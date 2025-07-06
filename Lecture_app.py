# -*- coding: utf-8 -*-
# =============================================================
# Lecture_app.py  –  version sans f-string dans le HTML
# =============================================================
import json, random, threading, time, pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from get_stimuli import get_stimuli            # ← ton module de tirage

# ---------- CONFIG ------------------------------------------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

# ---------- PETIT LEXIQUE (3 mots test) ---------------------------------
CSV_FILE = "Lexique383.csv"
@st.cache_data
def load_lexique():
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")
    df = df.rename(columns=lambda c: c.lower()).rename(columns={"ortho": "word"})
    df.word = df.word.str.upper()
    return df[["word"]].dropna()
LEX = load_lexique()

# ---------- LANCER LA SÉLECTION DES 80 MOTS -----------------------------
def _launch():
    try:
        st.session_state["stimuli"] = get_stimuli()
        st.session_state["ready"]   = True
    except Exception as e:
        st.session_state["error"]   = str(e)
    finally:
        try:
            st.experimental_rerun()
        except st.runtime.scriptrunner.StopException:
            pass

if "ready" not in st.session_state:
    st.session_state.update(dict(ready=False, error=None))
    threading.Thread(target=_launch, daemon=True).start()

# ---------- 3 mots d’entraînement ---------------------------------------
TRAIN = random.sample([w for w in LEX.word if len(w) == 3], 3)

# ---------- NAVIGATION ---------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "intro"
    st.session_state.idx  = 0

# ========================================================================
#  INTRO
# ========================================================================
if st.session_state.page == "intro":
    st.title("Expérience 3 — instructions")
    st.markdown("""
    Appuyez sur **Espace** dès que le mot apparaît, retapez-le, puis validez
    avec **Entrée**.  
    Nous commençons par **3 essais d’entraînement**.
    """)
    if st.button("Je suis prêt·e"):
        st.session_state.page = "train"
        st.experimental_rerun()

# ========================================================================
#  ENTRAÎNEMENT
# ========================================================================
elif st.session_state.page == "train":
    i = st.session_state.idx
    if i >= 3:
        st.session_state.page = "wait"
        st.experimental_rerun()
    else:
        st.subheader(f"Essai d’entraînement {i+1}/3")
        st.write("Mot cible :", TRAIN[i])
        if st.button("Valider (fictif)"):
            st.session_state.idx += 1
            st.experimental_rerun()

# ========================================================================
#  ATTENTE (80 mots pas encore prêts)
# ========================================================================
elif st.session_state.page == "wait":
    if st.session_state.get("ready"):
        st.session_state.page = "exp"
        st.experimental_rerun()
    elif st.session_state.get("error"):
        st.error("Erreur pendant la génération des stimuli : "
                 + st.session_state["error"])
    else:
        st.info("Préparation des 80 mots… merci de patienter.")
        st.progress(None)
        time.sleep(2)
        st.experimental_rerun()

# ========================================================================
#  EXPÉRIENCE (80 mots)
# ========================================================================
elif st.session_state.page == "exp":
    W      = json.dumps(st.session_state["stimuli"])  # 80 mots (JSON)
    CYCLE  = 350
    START  = 14
    STEP   = 14

    html_code = open("template.html", encoding="utf-8").read() \
                    .replace("__WORDS__",  W)         \
                    .replace("__CYCLE__", str(CYCLE)) \
                    .replace("__START__", str(START)) \
                    .replace("__STEP__",  str(STEP))

    components.html(html_code, height=650, scrolling=False)
