#!/usr/bin/env python3
"""
Génération des 80 mots (tirage contraint) – script autonome.
En sortie : tirage.json (UTF-8, orient='records').
"""

from __future__ import annotations
import random, sys
from pathlib import Path
import pandas as pd

# ─── paramètres identiques à l’app ──────────────────────────────────────
XLSX            = Path(__file__).with_name("Lexique.xlsx")
OUT             = Path(__file__).with_name("tirage.json")

MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER      = {"letters": 2.0, "phons": 2.0,
                      "old20": 0.25, "pld20": 0.25, "freq": 1.8}
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]

# ─── utilitaires ─────────────────────────────────────────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace({" ":"", "\xa0":""}, regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:          # -1 (LOW) / +1 (HIGH)
    return -1 if "LOW" in tag else 1

# ─── chargement Excel ────────────────────────────────────────────────────
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        sys.exit(f"{XLSX.name} introuvable.")
    xls = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4:
        sys.exit("Il faut 4 feuilles Feuil1 … Feuil4.")
    feuilles, all_freq = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns=df.columns.str.strip().str.lower()
        fcols=[c for c in df.columns if c.startswith("freq")]
        all_freq.update(fcols)
        need=["ortho","old20","pld20","nblettres","nbphons"]+fcols
        if any(c not in df.columns for c in need):
            sys.exit(f"Colonnes manquantes dans {sh}")
        for col in NUM_BASE+fcols: df[col]=to_float(df[col])
        df["ortho"]=df["ortho"].astype(str).str.upper()
        df=df.dropna(subset=need).reset_index(drop=True)
        stats={f"m_{c}":df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats|={f"sd_{c}":df[c].std(ddof=0) for c in
                ("old20","pld20","nblettres","nbphons")+tuple(fcols)}
        feuilles[sh]={"df":df,"stats":stats,"freq_cols":fcols}
    feuilles["all_freq_cols"]=sorted(all_freq)
    return feuilles

# ─── contraintes de tirage ───────────────────────────────────────────────
def masks(df:pd.DataFrame,s):            # s = stats
    return {"LOW_OLD":df.old20<s["m_old20"]-s["sd_old20"],
            "HIGH_OLD":df.old20>s["m_old20"]+s["sd_old20"],
            "LOW_PLD":df.pld20<s["m_pld20"]-s["sd_pld20"],
            "HIGH_PLD":df.pld20>s["m_pld20"]+s["sd_pld20"]}

def sd_ok(sub:pd.DataFrame,s,fqs):
    return (sub.nblettres.std(ddof=0)<=s["sd_nblettres"]*SD_MULTIPLIER["letters"] and
            sub.nbphons .std(ddof=0)<=s["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
            sub.old20   .std(ddof=0)<=s["sd_old20"]    *SD_MULTIPLIER["old20"]   and
            sub.pld20   .std(ddof=0)<=s["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
            all(sub[c].std(ddof=0)<=s[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fqs))

def mean_lp_ok(sub:pd.DataFrame,s):
    return (abs(sub.nblettres.mean()-s["m_nblettres"])<=MEAN_DELTA["letters"]*s["sd_nblettres"] and
            abs(sub.nbphons.mean() -s["m_nbphons"])   <=MEAN_DELTA["phons"]  *s["sd_nbphons"])

def pick_five(tag,feuille,used,F):
    df,s,fqs = F[feuille]["df"],F[feuille]["stats"],F[feuille]["freq_cols"]
    pool=df.loc[masks(df,s)[tag] & ~df.ortho.isin(used)]
    if len(pool)<N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp=pool.sample(N_PER_FEUIL_TAG,random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD" and samp.old20.mean()>=s["m_old20"]-MEAN_FACTOR_OLDPLD*s["sd_old20"]: continue
        if tag=="HIGH_OLD"and samp.old20.mean()<=s["m_old20"]+MEAN_FACTOR_OLDPLD*s["sd_old20"]: continue
        if tag=="LOW_PLD" and samp.pld20.mean()>=s["m_pld20"]-MEAN_FACTOR_OLDPLD*s["sd_pld20"]: continue
        if tag=="HIGH_PLD"and samp.pld20.mean()<=s["m_pld20"]+MEAN_FACTOR_OLDPLD*s["sd_pld20"]: continue
        if not mean_lp_ok(samp,s):continue
        if sd_ok(samp,s,fqs):
            samp["source"]=feuille; samp["group"]=tag
            samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
            return samp
    return None

def build_sheet() -> pd.DataFrame:
    F=load_sheets(); freqs=F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            part=[]
            for sh in taken:
                sub=pick_five(tag,sh,taken[sh],F)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(part,ignore_index=True)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            order=["ortho"]+NUM_BASE+freqs+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Tirage impossible (contraintes trop strictes).")

# ─── main ────────────────────────────────────────────────────────────────
def main():
    df=build_sheet()
    df.to_json(OUT, orient="records", force_ascii=False)
    print("OK")

if __name__=="__main__":
    main()