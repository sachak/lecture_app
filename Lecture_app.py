# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3
• Familiarisation : 2 mots (PAIN, EAU)
• Test principal  : 80 mots tirés au sort (4 × 20, contraintes OLD / PLD)

Le tirage est lancé en tâche de fond dès l’ouverture.
Fichier requis : Lexique.xlsx (Feuil1 … Feuil4)
Sortie         : results.csv (séparateur « ; », décimale « . »)
"""
from __future__ import annotations
import json, random, threading
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ───────────────────────── CONFIG STREAMLIT ─────────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility: hidden;}
.css-1d391kg {display: none;}          /* ancien spinner Streamlit */
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 1. PARAMÈTRES
# =============================================================================
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER      = {"letters": 2.00, "phons": 2.00,
                      "old20": 0.25, "pld20": 0.25, "freq": 1.80}

XLSX            = Path(__file__).with_name("Lexique.xlsx")
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG = 5
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]

# =============================================================================
# 2. OUTILS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(" ",  "", regex=False)
         .str.replace("\xa0","", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:
    return -1 if "LOW" in tag else 1

# =============================================================================
# 3.  CHARGEMENT DE L’EXCEL (cache global)
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

        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}")
            st.stop()

        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()  for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols)}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

# Feuilles chargées une fois
if "sheets" not in st.session_state:
    st.session_state.sheets = load_sheets()

# =============================================================================
# 4.  TIRAGE DES 80 MOTS  (aucun appel Streamlit)
# =============================================================================
def masks(df: pd.DataFrame, st_: dict) -> dict[str, pd.Series]:
    return {
        "LOW_OLD" : df.old20 <  st_["m_old20"] - st_["sd_old20"],
        "HIGH_OLD": df.old20 >  st_["m_old20"] + st_["sd_old20"],
        "LOW_PLD" : df.pld20 <  st_["m_pld20"] - st_["sd_pld20"],
        "HIGH_PLD": df.pld20 >  st_["m_pld20"] + st_["sd_pld20"],
    }

def sd_ok(sub: pd.DataFrame, st_: dict, fq_cols: list[str]) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULTIPLIER["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULTIPLIER["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULTIPLIER["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULTIPLIER["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULTIPLIER["freq"] for c in fq_cols)
    )

def mean_lp_ok(sub: pd.DataFrame, st_: dict) -> bool:
    return (
        abs(sub.nblettres.mean() - st_["m_nblettres"]) <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(sub.nbphons.mean()   - st_["m_nbphons"])   <= MEAN_DELTA["phons"]   * st_["sd_nbphons"]
    )

def pick_five(tag: str, feuille: str, used: set[str], FEUILLES) -> pd.DataFrame | None:
    df   = FEUILLES[feuille]["df"]
    st_  = FEUILLES[feuille]["stats"]
    fqs  = FEUILLES[feuille]["freq_cols"]
    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue

        if not mean_lp_ok(samp, st_):
            continue
        if sd_ok(samp, st_, fqs):
            samp["source"]  = feuille
            samp["group"]   = tag
            samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
            return samp
    return None

def build_sheet(FEUILLES) -> pd.DataFrame:
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
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source", "group",
                                                            "old_cat", "pld_cat"]
            return df[order]

    raise RuntimeError("Impossible de générer la liste (contraintes trop strictes).")

# =============================================================================
# 5. THREAD DE FOND : écrit directement dans session_state
# =============================================================================
def _async_build():
    try:
        sheets = st.session_state.sheets
        df = build_sheet(sheets)
        words = df["ortho"].tolist()
        random.shuffle(words)

        st.session_state.tirage_df    = df
        st.session_state.stimuli      = words
        st.session_state.tirage_ready = True
    except Exception as e:
        st.session_state.tirage_error = str(e)
        st.session_state.tirage_ready = False

if "tirage_ready" not in st.session_state:
    st.session_state.tirage_ready = False
    st.session_state.tirage_error = None
    threading.Thread(target=_async_build, daemon=True).start()

# =============================================================================
# 6.  GENERATION DU HTML
# =============================================================================
def experiment_html(words: list[str],
                    with_download: bool,
                    start_ms: int,
                    cycle_ms: int = 350,
                    step_ms : int = 14) -> str:

    end_msg = "Merci !" if with_download else "Fin de l’entraînement"

    download_js = ""
    if with_download:
        download_js = """
    const csv = ["word;rt_ms;response",
                 ...results.map(r => `${r.word};${r.rt_ms};${r.response}`)]
                .join("\\n");
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], {type: 'text/csv'}));
    a.download = 'results.csv';
    a.textContent = 'Télécharger les résultats';
    a.style.fontSize = '32px';
    a.style.marginTop = '30px';
    document.body.appendChild(a);
    """

    return f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace;}}
#scr{{font-size:60px;user-select:none;}}
#ans{{display:none;font-size:48px;width:60%;text-align:center;}}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load', ()=>document.body.focus());

const WORDS = {json.dumps(words)};
const CYCLE = {cycle_ms};
const START = {start_ms};
const STEP  = {step_ms};

let trial = 0;
let results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

function nextTrial() {{
    if (trial >= WORDS.length) {{ endExperiment(); return; }}

    const w   = WORDS[trial];
    const mask= '#'.repeat(w.length);

    let showDur = START;
    let hideDur = CYCLE - showDur;
    let tShow, tHide;
    const t0   = performance.now();
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
                    hideDur  = Math.max(0, CYCLE - showDur);
                    loop();
                }}
            }}, hideDur);
        }}, showDur);
    }})();

    function onSpace(e) {{
        if (e.code === 'Space' && active) {{
            active = false;
            clearTimeout(tShow);
            clearTimeout(tHide);

            const rt = Math.round(performance.now() - t0);
            window.removeEventListener('keydown', onSpace);

            scr.textContent = '';
            ans.style.display = 'block';
            ans.value = '';
            ans.focus();

            function onEnter(ev) {{
                if (ev.key === 'Enter') {{
                    ev.preventDefault();
                    results.push({{word: w, rt_ms: rt, response: ans.value.trim()}});
                    ans.removeEventListener('keydown', onEnter);
                    ans.style.display = 'none';
                    trial += 1;
                    nextTrial();
                }}
            }}
            ans.addEventListener('keydown', onEnter);
        }}
    }}
    window.addEventListener('keydown', onSpace);
}}

function endExperiment() {{
    scr.style.fontSize = '40px';
    scr.textContent = '{end_msg}';
    {download_js}
}}

nextTrial();
</script>
</body>
</html>
"""

# =============================================================================
# 7.  NAVIGATION
# =============================================================================
if "page" not in st.session_state:
    st.session_state.page = "intro"

# ---- INTRO ---------------------------------------------------------------- #
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** "
                "avec deux mots, puis le test principal (80 mots).")
    if st.session_state.tirage_error:
        st.error(st.session_state.tirage_error)

    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        st.rerun()

# ---- FAMILIARISATION ------------------------------------------------------ #
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **Espace** quand le mot apparaît, "
                "puis tapez ce que vous avez lu et validez avec **Entrée**.")
    components.v1.html(
        experiment_html(PRACTICE_WORDS, with_download=False, start_ms=250),
        height=650, scrolling=False
    )

    st.divider()
    if st.session_state.tirage_ready:
        if st.button("Passer au test principal"):
            st.session_state.page = "exp"
            st.rerun()
    else:
        st.button("Passer au test principal", disabled=True)
        st.markdown("""
        <div style="display:flex;align-items:center;margin-top:6px;">
          <div style="border:6px solid #f3f3f3;border-top:6px solid #3498db;
                      border-radius:50%;width:22px;height:22px;
                      animation:spin 1s linear infinite;"></div>
          <span style="margin-left:10px;">
            En attente du tirage au sort de 80 mots…
          </span>
        </div>
        <style>@keyframes spin{0%{transform:rotate(0deg);}
                               100%{transform:rotate(360deg);}}</style>
        """, unsafe_allow_html=True)

# ---- TEST PRINCIPAL ------------------------------------------------------- #
elif st.session_state.page == "exp":
    if not st.session_state.tirage_ready:
        st.warning("Les mots ne sont pas encore prêts. "
                   "Merci de patienter quelques instants…")
        st.stop()

    tirage_df = st.session_state.tirage_df
    stimuli   = st.session_state.stimuli

    st.header("Test principal (80 mots)")
    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())

    components.v1.html(
        experiment_html(stimuli, with_download=True, start_ms=14),
        height=650, scrolling=False
    )
