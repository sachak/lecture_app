#!/usr/bin/env python3
# =============================================================
# build_stimuli_tirage.py
#  – Sélection de 80 mots (4 feuilles × 4 groupes × 5 mots)
#  – Contraintes réglables sur old20 / pld20 / lettres / phons / freq*
#  – Fonction get_stimuli() à importer dans Streamlit
#  – Exécutable seul pour produire un classeur .xlsx
# =============================================================
from __future__ import annotations
from pathlib import Path
import random, sys, time
import pandas as pd

# =============================================================
# 1) CONTRAINTES RÉGLABLES
# -------------------------------------------------------------
MEAN_FACTOR_OLDPLD = 0.40          # éloignement mini (en σ) des moyennes LOW/HIGH
MEAN_DELTA = {                     # tolérance moyenne (en σ) autour de m
    "letters": 0.70,               # nblettres
    "phons"  : 0.70,               # nbphons
}
SD_MULTIPLIER = {                  # facteur multiplicatif autorisé sur σ
    "letters": 2.00,
    "phons"  : 2.00,
    "old20"  : 0.25,
    "pld20"  : 0.25,
    "freq"   : 10.00,              # toutes les colonnes freq*
}
# =============================================================

# -------- Fichiers -------------------------------------------------------
XLSX     = Path("Lexique.xlsx")         # classeur source
OUTFILE  = "Stimuli_perSheet.xlsx"      # généré quand on exécute ce script
# -------------------------------------------------------------------------

N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng = random.Random()          # option : rng.seed(123)

NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

# -------------------------------------------------------------------------
# OUTILS
# -------------------------------------------------------------------------
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(" ",  "", regex=False)
         .str.replace("\xa0","", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

# -------------------------------------------------------------------------
# CHARGEMENT DES 4 FEUILLES
# -------------------------------------------------------------------------
if not XLSX.exists():
    sys.exit(f"❌  Fichier introuvable : {XLSX.resolve()}")

xls = pd.ExcelFile(XLSX)
sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
if len(sheet_names) != 4:
    sys.exit("❌  Il faut exactement 4 feuilles nommées Feuil1 … Feuil4.")

FEUILLES: dict[str, dict] = {}          # {feuille: {"df":…, "stats":…, "freq_cols":…}}
all_freq_cols: set[str] = set()

for sh in sheet_names:
    df = xls.parse(sh)
    df.columns = df.columns.str.strip().str.lower()

    freq_cols_sheet = [c for c in df.columns if c.startswith("freq")]
    all_freq_cols.update(freq_cols_sheet)

    need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols_sheet
    if any(c not in df.columns for c in need):
        sys.exit(f"❌  Colonnes manquantes dans {sh}")

    for col in NUM_BASE + freq_cols_sheet:
        df[col] = to_float(df[col])

    df["ortho"] = df["ortho"].astype(str).str.upper()
    df = df.dropna(subset=need).reset_index(drop=True)

    # stats feuille
    st = {f"m_{c}": df[c].mean()  for c in ("old20", "pld20", "nblettres", "nbphons")}
    st |= {f"sd_{c}": df[c].std(ddof=0) for c in
           ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols_sheet)}

    FEUILLES[sh] = {"df": df, "stats": st, "freq_cols": freq_cols_sheet}

NUM = NUM_BASE + sorted(all_freq_cols)

# -------------------------------------------------------------------------
# MASQUES LOW / HIGH
# -------------------------------------------------------------------------
def masks(df: pd.DataFrame, st: dict) -> dict[str, pd.Series]:
    return {
        "LOW_OLD" : df.old20 <  st["m_old20"] - st["sd_old20"],
        "HIGH_OLD": df.old20 >  st["m_old20"] + st["sd_old20"],
        "LOW_PLD" : df.pld20 <  st["m_pld20"] - st["sd_pld20"],
        "HIGH_PLD": df.pld20 >  st["m_pld20"] + st["sd_pld20"],
    }

def cat_code(tag: str) -> int:
    return -1 if "LOW" in tag else 1

# -------------------------------------------------------------------------
# CONTRÔLES
# -------------------------------------------------------------------------
def sd_ok(sub: pd.DataFrame, st: dict, fq_cols: list[str]) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st["sd_nblettres"] * SD_MULTIPLIER["letters"] and
        sub.nbphons.std(ddof=0)   <= st["sd_nbphons"]   * SD_MULTIPLIER["phons"]   and
        sub.old20.std(ddof=0)     <= st["sd_old20"]     * SD_MULTIPLIER["old20"]   and
        sub.pld20.std(ddof=0)     <= st["sd_pld20"]     * SD_MULTIPLIER["pld20"]   and
        all(sub[c].std(ddof=0) <= st[f"sd_{c}"] * SD_MULTIPLIER["freq"] for c in fq_cols)
    )

def mean_lp_ok(sub: pd.DataFrame, st: dict) -> bool:
    """Moyennes lettres / phons proches de la moyenne feuille (±delta*σ)."""
    return (
        abs(sub.nblettres.mean() - st["m_nblettres"]) <= MEAN_DELTA["letters"] * st["sd_nblettres"] and
        abs(sub.nbphons.mean()   - st["m_nbphons"])   <= MEAN_DELTA["phons"]   * st["sd_nbphons"]
    )

# -------------------------------------------------------------------------
# TIRAGE 5 MOTS DANS UNE FEUILLE / TAG
# -------------------------------------------------------------------------
def pick_five(tag: str, feuille: str, used: set[str]) -> pd.DataFrame | None:
    df   = FEUILLES[feuille]["df"]
    st   = FEUILLES[feuille]["stats"]
    fqs  = FEUILLES[feuille]["freq_cols"]

    pool = df.loc[masks(df, st)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        # -- moyenne old20 / pld20 extrême ?
        if tag == "LOW_OLD"  and samp.old20.mean() >= st["m_old20"] - MEAN_FACTOR_OLDPLD*st["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st["m_old20"] + MEAN_FACTOR_OLDPLD*st["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st["m_pld20"] - MEAN_FACTOR_OLDPLD*st["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st["m_pld20"] + MEAN_FACTOR_OLDPLD*st["sd_pld20"]:  continue

        # -- moyenne lettres / phons OK ?
        if not mean_lp_ok(samp, st):
            continue

        # -- dispersion OK ?
        if sd_ok(samp, st, fqs):
            samp["source"]  = feuille
            samp["group"]   = tag
            samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
            return samp
    return None

# -------------------------------------------------------------------------
# CONSTRUCTION DES 80 MOTS
# -------------------------------------------------------------------------
def build_sheet() -> pd.DataFrame:
    """Renvoie un DataFrame (80 lignes) répondant à toutes les contraintes."""
    for _ in range(MAX_TRY_FULL):
        taken  = {sh: set() for sh in FEUILLES}
        groups = []
        ok = True

        for tag in TAGS:
            parts = []
            for sh in FEUILLES:
                sub = pick_five(tag, sh, taken[sh])
                if sub is None:
                    ok = False
                    break
                parts.append(sub)
                taken[sh].update(sub.ortho)
            if not ok:
                break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))  # mélange interne

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM + ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    raise RuntimeError("⚠️  Impossible de générer la feuille : relâche les contraintes.")

# -------------------------------------------------------------------------
#  FONCTION PUBLIQUE À IMPORTER DANS STREAMLIT
# -------------------------------------------------------------------------
def get_stimuli() -> list[str]:
    """
    Retourne la liste de 80 mots (ordre déjà mélangé) à afficher dans
    l'expérience.  Lève RuntimeError si les contraintes sont impossibles.
    """
    return build_sheet().ortho.tolist()

# -------------------------------------------------------------------------
#  SI LANÇÉ DIRECTEMENT : écrit le classeur Excel + stats
# -------------------------------------------------------------------------
def _stats_by_block_total(df: pd.DataFrame) -> pd.DataFrame:
    keep_num = [c for c in df.columns if c not in ("ortho","source","group","old_cat","pld_cat")]
    rows=[]
    for blk in ("4_5","6_7","8_9","10_11"):
        sub=df[df.nblettres.apply(lambda n: "4_5" if n in (4,5)
                                  else "6_7" if n in (6,7)
                                  else "8_9" if n in (8,9)
                                  else "10_11")==blk]
        d={"letters_block":blk,"n":len(sub)}
        for c in keep_num:
            d[f"{c}_mean"]=sub[c].mean()
            d[f"{c}_sd"]=sub[c].std(ddof=0)
        rows.append(d)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    tic = time.perf_counter()
    df80 = build_sheet()
    stats_blk = _stats_by_block_total(df80)

    with pd.ExcelWriter(OUTFILE, engine="openpyxl") as wr:
        df80.to_excel(wr, sheet_name="tirage", index=False)
        stats_blk.to_excel(wr, sheet_name="Stats_ByLetters", index=False)

    print(f"\n✓  {OUTFILE} généré en {time.perf_counter()-tic:.1f} s")