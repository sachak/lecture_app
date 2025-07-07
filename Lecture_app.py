# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – version « tirage » 4 × 20 mots (5 par feuille × 4 feuilles).

• Fichier attendu : Lexique.xlsx (4 feuilles Feuil1…Feuil4)
• Résultat        : experience.csv (séparateur “;”, décimale “.”)

Lancer :  streamlit run exp3.py
"""
from __future__ import annotations

# ─────────────────────────────── IMPORTS ───────────────────────────────────── #
import json, random, sys, time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from streamlit import components

# ───────────────────────── 0. CONFIG STREAMLIT ────────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .css-1d391kg {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# 1.  PARAMÈTRES DU TIRAGE (repris de build_stimuli_tirage.py)
# =============================================================================
MEAN_FACTOR_OLDPLD = 0.40

MEAN_DELTA = {"letters": 0.70, "phons": 0.70}

SD_MULTIPLIER = {
    "letters": 2.00,
    "phons"  : 2.00,
    "old20"  : 0.25,
    "pld20"  : 0.25,
    "freq"   : 10.00,
}

XLSX     = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng = random.Random()         # rng.seed(123)  # (optionnel)

NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

# =============================================================================
# 2.  OUTILS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(" ",  "", regex=False)
         .str.replace("\xa0","", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:
    return -1 if "LOW" in tag else 1

# =============================================================================
# 3.  LECTURE DU CLASSEUR + CONSTRUCTION DES 80 MOTS (fonctions @cache_data)
# =============================================================================
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable.")
        st.stop()

    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4.")
        st.stop()

    feuilles: dict[str, dict] = {}
    all_freq_cols: set[str] = set()

    for sh in sheet_names:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()

        freq_cols_sheet = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols_sheet)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols_sheet
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}")
            st.stop()

        for col in NUM_BASE + freq_cols_sheet:
            df[col] = to_float(df[col])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()  for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols_sheet)}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols_sheet}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles


def masks(df: pd.DataFrame, st: dict) -> dict[str, pd.Series]:
    return {
        "LOW_OLD" : df.old20 <  st["m_old20"] - st["sd_old20"],
        "HIGH_OLD": df.old20 >  st["m_old20"] + st["sd_old20"],
        "LOW_PLD" : df.pld20 <  st["m_pld20"] - st["sd_pld20"],
        "HIGH_PLD": df.pld20 >  st["m_pld20"] + st["sd_pld20"],
    }


def sd_ok(sub: pd.DataFrame, st: dict, fq_cols: list[str]) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st["sd_nblettres"] * SD_MULTIPLIER["letters"] and
        sub.nbphons.std(ddof=0)   <= st["sd_nbphons"]   * SD_MULTIPLIER["phons"]   and
        sub.old20.std(ddof=0)     <= st["sd_old20"]     * SD_MULTIPLIER["old20"]   and
        sub.pld20.std(ddof=0)     <= st["sd_pld20"]     * SD_MULTIPLIER["pld20"]   and
        all(sub[c].std(ddof=0) <= st[f"sd_{c}"] * SD_MULTIPLIER["freq"] for c in fq_cols)
    )


def mean_lp_ok(sub: pd.DataFrame, st: dict) -> bool:
    return (
        abs(sub.nblettres.mean() - st["m_nblettres"]) <= MEAN_DELTA["letters"] * st["sd_nblettres"] and
        abs(sub.nbphons.mean()   - st["m_nbphons"])   <= MEAN_DELTA["phons"]   * st["sd_nbphons"]
    )


def pick_five(tag: str, feuille: str, used: set[str], FEUILLES) -> pd.DataFrame | None:
    df   = FEUILLES[feuille]["df"]
    st   = FEUILLES[feuille]["stats"]
    fqs  = FEUILLES[feuille]["freq_cols"]
    pool = df.loc[masks(df, st)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        # distance OLD/PLD suffisante
        if tag == "LOW_OLD"  and samp.old20.mean() >= st["m_old20"] - MEAN_FACTOR_OLDPLD*st["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st["m_old20"] + MEAN_FACTOR_OLDPLD*st["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st["m_pld20"] - MEAN_FACTOR_OLDPLD*st["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st["m_pld20"] + MEAN_FACTOR_OLDPLD*st["sd_pld20"]:  continue

        if not mean_lp_ok(samp, st):
            continue
        if sd_ok(samp, st, fqs):
            samp["source"]  = feuille
            samp["group"]   = tag
            samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
            return samp
    return None


@st.cache_data(show_spinner="Tirage aléatoire des 80 mots…")
def build_sheet() -> pd.DataFrame:
    FEUILLES = load_sheets()
    all_freq_cols = FEUILLES["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken  = {sh: set() for sh in FEUILLES if sh != "all_freq_cols"}
        groups = []
        ok = True

        for tag in TAGS:
            parts = []
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], FEUILLES)
                if sub is None:
                    ok = False
                    break
                parts.append(sub)
                taken[sh].update(sub.ortho)
            if not ok:
                break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    st.error("Impossible de générer la liste (contraintes trop strictes).")
    st.stop()


# =============================================================================
# 4.  LISTE DES STIMULI PRÊTE POUR L’EXPÉRIMENTATION
# =============================================================================
tirage_df = build_sheet()
STIMULI   = tirage_df["ortho"].tolist()
random.shuffle(STIMULI)          # ordre expérimental aléatoire

# =============================================================================
# 5.  PARTIE VISUELLE : IDENTIQUE À L’ANCIEN SCRIPT
# =============================================================================
CYCLE_MS = 350
START_MS = 14
STEP_MS  = 14

if "page" not in st.session_state:
    st.session_state.page = "intro"

# ----------------------------- page intro ----------------------------------- #
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués (tirage contraint)")
    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.rerun()

# ----------------------------- expérience ----------------------------------- #
else:
    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body {{
    height: 100%;
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'Courier New', monospace;
}}
#scr {{
    font-size: 60px;
    user-select: none;
}}
#ans {{
    display: none;
    font-size: 48px;
    width: 60%;
    text-align: center;
}}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load", () => document.body.focus());

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS};
const START = {START_MS};
const STEP  = {STEP_MS};

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

function nextTrial() {{

    if (trial >= WORDS.length) {{
        endExperiment();
        return;
    }}

    const w = WORDS[trial];
    const mask = "#".repeat(w.length);

    let showDur = START;
    let hideDur = CYCLE - showDur;
    let tShow, tHide;
    const t0 = performance.now();
    let active = true;

    (function loop() {{
        if (!active) return;

        scr.textContent = w;
        tShow = setTimeout(() => {{
            if (!active) return;

            scr.textContent = mask;
            tHide = setTimeout(() => {{
                if (active) {{
                    showDur += STEP;
                    hideDur = Math.max(0, CYCLE - showDur);
                    loop();
                }}
            }}, hideDur);
        }}, showDur);
    }})();

    function onSpace(e) {{
        if (e.code === "Space" && active) {{
            active = false;
            clearTimeout(tShow);
            clearTimeout(tHide);

            const rt = Math.round(performance.now() - t0);
            window.removeEventListener("keydown", onSpace);

            scr.textContent = "";
            ans.style.display = "block";
            ans.value = "";
            ans.focus();

            function onEnter(ev) {{
                if (ev.key === "Enter") {{
                    ev.preventDefault();
                    results.push({{
                        word: w,
                        rt_ms: rt,
                        response: ans.value.trim()
                    }});
                    ans.removeEventListener("keydown", onEnter);
                    ans.style.display = "none";
                    trial += 1;
                    nextTrial();
                }}
            }}
            ans.addEventListener("keydown", onEnter);
        }}
    }}
    window.addEventListener("keydown", onSpace);
}}

function endExperiment() {{
    scr.style.fontSize = "40px";
    scr.textContent = "Merci !";

    const csv = [
        "word;rt_ms;response",
        ...results.map(r => `${{r.word}};${{r.rt_ms}};${{r.response}}`)
    ].join("\\n");

    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], {{type: "text/csv"}}));
    a.download = "results.csv";
    a.textContent = "Télécharger les résultats";
    a.style.fontSize = "32px";
    a.style.marginTop = "30px";
    document.body.appendChild(a);
}}

nextTrial();
</script>
</body>
</html>
"""
    components.v1.html(html, height=650, scrolling=False)
