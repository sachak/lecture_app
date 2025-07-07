# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3
• Familiarisation : 2 mots fixes (PAIN, EAU)
• Test            : 4 × 20 mots (5 par feuille × 4 feuilles, tirage contraint)

Fichier requis : Lexique.xlsx (Feuil1…Feuil4)
Sortie         : results.csv  (séparateur “;”, décimale “.”)

Exécution : streamlit run exp3.py
"""

from __future__ import annotations

# ───────────────────────────── IMPORTS ────────────────────────────────────── #
import json, random
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ───────────────────────── 0. CONFIG STREAMLIT ───────────────────────────── #
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

# ─────────────── PARAMÈTRES DU TIRAGE ─────────────── #
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER = {
    "letters": 2.00,
    "phons": 2.00,
    "old20": 0.25,
    "pld20": 0.25,
    "freq": 1.80,
}
XLSX = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG = 1_000
MAX_TRY_FULL = 1_000
rng = random.Random()
NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# ─────────────── OUTILS ─────────────── #
def to_float(s: pd.Series) -> pd.Series:
    """Convertit proprement une série à virgules en float (gère espaces, insécables, virgules)."""
    return pd.to_numeric(
        s.astype(str)
        .str.replace(" ", "")
        .str.replace(",", ".")
        .str.replace(" ", ""),
        errors="coerce",
    )


def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne le DataFrame mélangé (seed pseudo‐aléatoire)."""
    return df.sample(frac=1, random_state=rng.randint(0, 999_999)).reset_index(drop=True)


def cat_code(tag: str) -> int:
    """Encode +1 / –1 pour les tags HIGH / LOW, 0 sinon."""
    return -1 if "LOW" in tag else 1


# ─────────────── CHARGEMENT EXCEL + TIRAGE ─────────────── #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets():
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable.")
        st.stop()

    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4.")
        st.stop()

    feuilles, all_freq_cols = {}, set()

    for sh in sheet_names:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()

        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}")
            st.stop()

        # Conversion numérique
        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])

        # Ortho en MAJUSCULES
        df["ortho"] = df["ortho"].astype(str).str.upper()

        # On élimine les lignes incomplètes
        df = df.dropna(subset=need).reset_index(drop=True)

        # Moyennes et écarts types
        stats = {f"m_{c}": df[c].mean() for c in NUM_BASE}
        # CORRECTION ICI → on concatène deux listes, plus d’erreur TypeError
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in NUM_BASE + freq_cols}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles


def masks(df: pd.DataFrame, st_: dict[str, float]) -> dict[str, pd.Series]:
    return {
        "LOW_OLD": df.old20 < st_["m_old20"] - st_["sd_old20"],
        "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
        "LOW_PLD": df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
        "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"],
    }


def sd_ok(sub: pd.DataFrame, st_: dict[str, float], fq: list[str]) -> bool:
    """Vérifie que la dispersion des variables reste dans les bornes fixées."""
    return all(
        [
            sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULTIPLIER["letters"],
            sub.nbphons.std(ddof=0) <= st_["sd_nbphons"] * SD_MULTIPLIER["phons"],
            sub.old20.std(ddof=0) <= st_["sd_old20"] * SD_MULTIPLIER["old20"],
            sub.pld20.std(ddof=0) <= st_["sd_pld20"] * SD_MULTIPLIER["pld20"],
            all(
                sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULTIPLIER["freq"] for c in fq
            ),
        ]
    )


def mean_lp_ok(sub: pd.DataFrame, st_: dict[str, float]) -> bool:
    """Vérifie l’équilibre moyen longueur/nb phonèmes."""
    return all(
        [
            abs(sub.nblettres.mean() - st_["m_nblettres"])
            <= MEAN_DELTA["letters"] * st_["sd_nblettres"],
            abs(sub.nbphons.mean() - st_["m_nbphons"])
            <= MEAN_DELTA["phons"] * st_["sd_nbphons"],
        ]
    )


def pick_five(tag: str, feuille: str, used: set[str], FEUILLES):
    """Tirage de 5 mots correspondant au tag dans la feuille donnée."""
    df = FEUILLES[feuille]["df"]
    st_ = FEUILLES[feuille]["stats"]
    fq = FEUILLES[feuille]["freq_cols"]

    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 999_999)).copy()

        # Garantit qu’en moyenne on reste bien LOW ou HIGH
        if tag == "LOW_OLD" and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD * st_["sd_old20"]:
            continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD * st_["sd_old20"]:
            continue
        if tag == "LOW_PLD" and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:
            continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:
            continue

        if not mean_lp_ok(samp, st_):
            continue
        if sd_ok(samp, st_, fq):
            samp["source"], samp["group"] = feuille, tag
            samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
            return samp

    return None


def build_sheet() -> pd.DataFrame:
    FEUILLES = load_sheets()
    fq_cols = FEUILLES["all_freq_cols"]

    for _ in range(MAX_TRY_FULL):
        taken: dict[str, set[str]] = {
            sh: set() for sh in FEUILLES if sh != "all_freq_cols"
        }
        groups, ok = [], True

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
            order = ["ortho"] + NUM_BASE + fq_cols + ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    st.error("Impossible de générer la liste (contraintes trop strictes).")
    st.stop()


# ─────────────── HTML STIMULI ─────────────── #
def experiment_html(
    words: list[str],
    with_download: bool = True,
    cycle_ms: int = 350,
    start_ms: int = 14,
    step_ms: int = 14,
) -> str:
    """Fabrique le micro-script HTML/JS qui gère l’expérience côté navigateur."""
    download_js = ""
    if with_download:
        download_js = """
        const csv = ["word;rt_ms;response", ...results.map(r => `${r.word};${r.rt_ms};${r.response}`)].join("\\n");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"}));
        a.download = "results.csv";
        a.textContent = "Télécharger les résultats";
        a.style.fontSize = "32px";
        a.style.marginTop = "30px";
        document.body.appendChild(a);
        """
    return f"""<html><head><meta charset="utf-8"/><style>
    html,body {{height:100%;margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Courier New',monospace;}}
    #scr {{font-size:60px;user-select:none;}} #ans {{display:none;font-size:48px;width:60%;text-align:center;}}
    </style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
    <script>
    window.addEventListener("load",()=>document.body.focus());
    const WORDS={json.dumps(words)},CYCLE={cycle_ms},START={start_ms},STEP={step_ms};
    let trial=0,results=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
    function nextTrial() {{
        if(trial>=WORDS.length){{scr.textContent="Merci !";{download_js}return;}}
        const w=WORDS[trial],mask="#".repeat(w.length);let showDur=START,hideDur=CYCLE-showDur,t0=performance.now(),active=true;
        (function loop(){{if(!active)return;scr.textContent=w;
            tShow=setTimeout(()=>{{if(!active)return;scr.textContent=mask;
                tHide=setTimeout(()=>{{if(active){{showDur+=STEP;hideDur=Math.max(0,CYCLE-showDur);loop();}}}},hideDur);
            }},showDur);
        }})();
        function onSpace(e){{if(e.code==="Space"&&active){{active=false;clearTimeout(tShow);clearTimeout(tHide);
            const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",onSpace);
            scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
            function onEnter(ev){{if(ev.key==="Enter"){{ev.preventDefault();results.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
                ans.removeEventListener("keydown",onEnter);ans.style.display="none";trial+=1;nextTrial();}}}}ans.addEventListener("keydown",onEnter);}}}}
        window.addEventListener("keydown",onSpace);
    }}nextTrial();
    </script></body></html>"""


# ─────────────── PRÉPARATION TIRAGE (ARRIÈRE-PLAN) ─────────────── #
if "tirage_df" not in st.session_state:
    with st.spinner("Préparation du tirage des 80 mots…"):
        df = build_sheet()
        st.session_state.tirage_df = df
        mots = df["ortho"].tolist()
        random.shuffle(mots)
        st.session_state.stimuli = mots

tirage_df: pd.DataFrame = st.session_state.tirage_df
STIMULI: list[str] = st.session_state.stimuli

# ─────────────── NAVIGATION ─────────────── #
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown(
        "Cette expérience comporte d’abord **une courte familiarisation** puis le test principal."
    )
    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        st.rerun()

elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown(
        "Appuyez sur **Espace** dès que vous voyez apparaître le mot, puis tapez ce que vous avez lu."
    )
    components.v1.html(
        experiment_html(PRACTICE_WORDS, with_download=False),
        height=650,
        scrolling=False,
    )
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"
        st.rerun()

else:
    st.header("Test principal (80 mots)")
    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())
    components.v1.html(
        experiment_html(STIMULI, with_download=True), height=650, scrolling=False
    )
