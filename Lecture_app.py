# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – version « tirage en arrière-plan »
Exécution : streamlit run exp3_async.py
"""
from __future__ import annotations

# ───────────────────────────── IMPORTS ────────────────────────────────────── #
import json, random, threading
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components
from streamlit.runtime.scriptrunner import add_script_run_ctx

# ───────────────────────── 0. CONFIG STREAMLIT ───────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
    #MainMenu, header, footer {visibility: hidden;}
    .css-1d391kg {display: none;}          /* ancien spinner Streamlit */
</style>""", unsafe_allow_html=True)

# =============================================================================
# 1. PARAMÈTRES + OUTILS  (identiques à votre script)
# =============================================================================
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA   = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER = {
    "letters": 2.00, "phons": 2.00, "old20": 0.25,
    "pld20": 0.25,  "freq": 1.80,
}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]   # phase de familiarisation

# ----------------------------------------------------------------------------- 
# 1-b  Fonctions utilitaires  (inchangées)
# -----------------------------------------------------------------------------
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
# 2.  CHARGEMENT D’EXCEL (cache GLOBAL) + TIRAGE DES 80 MOTS
# =============================================================================
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    # (identique à votre fonction)
    # [...]

def masks(df: pd.DataFrame, st_: dict) -> dict[str, pd.Series]:         # [...]
    # (identique)

def sd_ok(sub: pd.DataFrame, st_: dict, fq_cols: list[str]) -> bool:     # [...]
    # (identique)

def mean_lp_ok(sub: pd.DataFrame, st_: dict) -> bool:                    # [...]
    # (identique)

def pick_five(tag: str, feuille: str, used: set[str], FEUILLES) -> pd.DataFrame | None:
    # (identique)

def build_sheet() -> pd.DataFrame:
    """Calcul ‘lourd’ : génère la liste de 80 mots (appelé dans un thread)."""
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
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source", "group",
                                                            "old_cat", "pld_cat"]
            return df[order]

    raise RuntimeError("Impossible de générer la liste (contraintes trop strictes)")

# =============================================================================
# 3.  THREAD DÉDIÉ AU TIRAGE
# =============================================================================
def launch_background_tirage():
    """
    Lance build_sheet() dans un thread et enregistre le résultat
    dans st.session_state quand c’est prêt.
    """
    def _worker():
        try:
            df = build_sheet()
        except Exception as exc:      # en cas d’erreur on la stocke
            st.session_state.tirage_error = str(exc)
            st.session_state.tirage_ready = True
            return

        words = df["ortho"].tolist()
        random.shuffle(words)

        # Les écritures suivantes SONT thread-safe car on a ajouté le contexte :
        st.session_state.tirage_df   = df
        st.session_state.stimuli     = words
        st.session_state.tirage_ready = True

        # forcer un rafraîchissement de l’IHM
        st.experimental_rerun()

    t = threading.Thread(target=_worker, daemon=True)
    add_script_run_ctx(t)            # indispensable pour accéder à session_state
    t.start()
    st.session_state.tirage_thread = t


# Drapeaux d’état (créés une seule fois)
if "tirage_ready"   not in st.session_state: st.session_state.tirage_ready = False
if "tirage_error"   not in st.session_state: st.session_state.tirage_error = ""
if "tirage_thread"  not in st.session_state: launch_background_tirage()

# =============================================================================
# 4.  HTML/JS pour la familiarisation et le test  (identique à votre fonction)
# =============================================================================
def experiment_html(words: list[str], with_download=True,
                    cycle_ms=350, start_ms=14, step_ms=14) -> str:
    # (fonction inchangée)
    # [...]

# =============================================================================
# 5.  NAVIGATION
# =============================================================================
if "page" not in st.session_state:
    st.session_state.page = "intro"

# ──────────────────── PAGE INTRO ──────────────────────────────────────────── #
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** "
                "puis le test principal.")

    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        st.rerun()

# ──────────────────── PAGE FAMILIARISATION ───────────────────────────────── #
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **Espace** dès que vous voyez apparaître le mot, "
                "puis tapez ce que vous avez lu et validez avec **Entrée**.")

    # Feedback sur l’avancement du tirage
    placeholder = st.empty()
    if st.session_state.tirage_ready:
        if st.session_state.tirage_error:
            placeholder.error(f"Erreur lors du tirage : {st.session_state.tirage_error}")
        else:
            placeholder.success("Stimuli du test prêts !")
    else:
        placeholder.info("Préparation des stimuli du test en arrière-plan…")

    components.v1.html(experiment_html(PRACTICE_WORDS, with_download=False),
                       height=650, scrolling=False)

    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"
        st.rerun()

# ──────────────────── PAGE TEST PRINCIPAL ────────────────────────────────── #
else:   # page == "exp"
    st.header("Test principal (80 mots)")

    if not st.session_state.tirage_ready:
        # Le tirage n’est pas encore terminé → on attend gentiment.
        st.warning("Les stimuli sont encore en cours de génération… Merci de patienter.")
        st.stop()

    if st.session_state.tirage_error:
        st.error(f"Impossible de poursuivre : {st.session_state.tirage_error}")
        st.stop()

    tirage_df = st.session_state.tirage_df
    STIMULI   = st.session_state.stimuli

    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())

    components.v1.html(experiment_html(STIMULI, with_download=True),
                       height=650, scrolling=False)
