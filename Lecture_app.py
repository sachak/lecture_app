# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test 80 mots ; écrans 60 / 120 Hz)
Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import inspect, json, random, re
from pathlib import Path
from string import Template
from typing import Dict, List
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


#────────────────────────── utilitaire « rerun » ────────────────────────────
def do_rerun():
    st.session_state["_rerun_flag_"] = True
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


#────────────────────────── config Streamlit ────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


#────────────────────────── constantes globales ─────────────────────────────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = {"letters": .68, "phons": .68}
SD_MULT            = {"letters": 2, "phons": 2,
                      "old20": .28, "pld20": .28, "freq": 1.9}

XLSX            = Path(__file__).with_name("Lexique.xlsx")
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG = 5                  # 5×4×4 = 80 mots
MAX_TRY_TAG     = MAX_TRY_FULL = 1_000
rng             = random.Random()

NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]

# dictionnaire d’alias « nom renvoyé par Lexique.xlsx → nom standard »
ALIAS = {
    # nbre lettres
    r"nb.?lettres?"  : "nblettres",
    r"nb.?lettre"    : "nblettres",
    # nbre phonèmes
    r"nb.?phons?"    : "nbphons",
    r"nb.?phon(?:emes?)?" : "nbphons",
    # OLD20
    r"old.?20"       : "old20",
    # PLD20
    r"pld.?20"       : "pld20",
}

#────────────────────────── outils génériques ───────────────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[ ,\xa0]", "", regex=True)
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:          # -1 LOW ; +1 HIGH ; 0 autre
    return -1 if "LOW"  in tag else (1 if "HIGH" in tag else 0)

#────────────────────────── 3. Lecture des feuilles ─────────────────────────
@st.cache_data(show_spinner=False)
def load_sheets() -> Dict[str, Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls  = pd.ExcelFile(XLSX)
    shs  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(shs) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq = {}, set()

    for sh in shs:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()

        # — renommage via dictionnaire d’alias ————————————————
        ren = {}
        for col in df.columns:
            for pat, std in ALIAS.items():
                if re.fullmatch(pat, col):
                    ren[col] = std
                    break
        df = df.rename(columns=ren)

        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.warning(f"Feuille « {sh} » ignorée : colonnes manquantes.")
            continue                # on zappe plutôt que planter

        for c in NUM_BASE + freq_cols:
            df[c] = to_float(df[c])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()        for c in NUM_BASE}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in NUM_BASE + freq_cols}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    if len(feuilles) < 4:
        st.error("Au moins une feuille invalide ; merci d’harmoniser les en-têtes."); st.stop()

    feuilles["all_freq_cols"] = sorted(all_freq)
    return feuilles

#────────────────────────── 4. Tirage des 80 mots ───────────────────────────
def masks(df, st_) -> Dict[str, pd.Series]:
    return {"LOW_OLD":  df.old20 < st_["m_old20"],
            "HIGH_OLD": df.old20 > st_["m_old20"],
            "LOW_PLD":  df.pld20 < st_["m_pld20"],
            "HIGH_PLD": df.pld20 > st_["m_pld20"]}

def sd_ok(sub, st_, fq) -> bool:
    if any(c not in sub.columns for c in ("nblettres", "nbphons", "old20", "pld20")):
        return False
    ok_num = all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT[c]
                 for c in ("nblettres", "nbphons", "old20", "pld20"))
    ok_fqs = all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq)
    return ok_num and ok_fqs

def mean_lp_ok(s, st_) -> bool:
    return (abs(s.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(s.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="HIGH_OLD" and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="LOW_PLD"  and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag=="HIGH_PLD" and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp,st_) or not sd_ok(samp,st_,fq): continue
        samp["source"],samp["group"]=feuille,tag
        samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F=load_sheets(); all_freq=F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            bloc=[]
            for sh in taken:
                sub=pick_five(tag,sh,taken[sh],F)
                if sub is None: ok=False; break
                bloc.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            order=["ortho"]+NUM_BASE+all_freq+["source","group","old_cat","pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste ; vérifiez Lexique.xlsx."); st.stop()

#────────────────────────── 5. HTML/JS de la tâche  (identique) ─────────────
# … (inchangé, voir le code précédent : HTML_TPL, experiment_html) …
# Pour raison de place, ces blocs sont identiques à la version précédente.
#────────────────────────── 6. Navigation et pages Streamlit ────────────────
# … idem version précédente …
