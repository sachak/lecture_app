# -*- coding: utf-8 -*-
# =============================================================
# Lecture_app_streamlit.py  –  version 100 % Streamlit
# =============================================================
import json, random, threading, time, uuid, io
import pandas as pd
import streamlit as st
from get_stimuli import get_stimuli          # ← ta fonction de tirage

# -------------------------------------------------------------
#  PARAMÈTRES
# -------------------------------------------------------------
MASK_TIME   = 0.35     # durée d’affichage du masque  (s)
WORD_TIME   = 0.02     # délai avant de remplacer par le mot (s)
CYCLE_INC   = 0.014    # augmentation du SOA après chaque essai
TRAIN_WORDS = ["MER", "SAC", "LOT"]   # 3 essais fixés

# -------------------------------------------------------------
#  SÉLECTION DES 80 MOTS EN TÂCHE DE FOND
# -------------------------------------------------------------
def launch_selection():
    try:
        st.session_state.stimuli = get_stimuli()
        st.session_state.ready   = True
    except Exception as e:
        st.session_state.error   = str(e)
    finally:
        st.experimental_rerun()          # force refresh

if "ready" not in st.session_state:
    st.session_state.update(dict(
        ready=False, error=None, page="intro",
        idx=0,       # index dans la liste courante (train ou réelle)
        soa=MASK_TIME+WORD_TIME,   # Stimulus Onset Asynchrony courant
        data=[],     # réponses
    ))
    threading.Thread(target=launch_selection, daemon=True).start()

# -------------------------------------------------------------
#  OUTILS
# -------------------------------------------------------------
def show_mask(mask_placeholder, word_placeholder, word, soa):
    """Affiche d’abord ##### puis le mot, puis retourne l’heure t0"""
    mask_placeholder.write("#" * len(word))
    time.sleep(WORD_TIME)
    word_placeholder.write(word)
    return time.perf_counter()

def add_response(word, rt_ms, resp):
    st.session_state.data.append(dict(word=word, rt_ms=rt_ms, response=resp))

# -------------------------------------------------------------
#  PAGE INTRO
# -------------------------------------------------------------
if st.session_state.page == "intro":
    st.title("Expérience 3 — instructions")
    st.write("Appuyez sur **Espace** dès que le mot apparaît ; retapez-le puis "
             "validez avec **Entrée**. Nous commençons par 3 essais.")
    if st.button("Démarrer"):
        st.session_state.page = "train"
        st.experimental_rerun()

# -------------------------------------------------------------
#  ENTRAÎNEMENT (3 mots)
# -------------------------------------------------------------
elif st.session_state.page == "train":
    i = st.session_state.idx
    if i >= len(TRAIN_WORDS):
        st.session_state.page = "wait"
        st.experimental_rerun()
    else:
        word = TRAIN_WORDS[i]
        st.subheader(f"Essai entraînement {i+1}/3")
        mask_ph   = st.empty()
        word_ph   = st.empty()
        input_ph  = st.empty()

        t0 = show_mask(mask_ph, word_ph, word, st.session_state.soa)
        resp = input_ph.text_input("Retapez le mot :", key=f"train_{i}")
        if resp:
            rt = (time.perf_counter() - t0) * 1000
            add_response(word, int(rt), resp.strip())
            st.session_state.idx += 1
            st.session_state.soa += CYCLE_INC
            st.experimental_rerun()

# -------------------------------------------------------------
#  ATTENTE SI MOTS PAS PRÊTS
# -------------------------------------------------------------
elif st.session_state.page == "wait":
    if st.session_state.ready:
        st.session_state.page = "exp"
        st.session_state.idx  = 0
        st.experimental_rerun()
    elif st.session_state.error:
        st.error("Erreur tirage : " + st.session_state.error)
    else:
        st.info("Préparation des 80 mots… merci de patienter.")
        st.progress(None)

# -------------------------------------------------------------
#  EXPÉRIENCE RÉELLE 80 mots
# -------------------------------------------------------------
elif st.session_state.page == "exp":
    i = st.session_state.idx
    words = st.session_state.stimuli

    if i >= len(words):            # FIN
        st.success("C'est terminé ! Merci.")
        df = pd.DataFrame(st.session_state.data)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger les résultats", csv,
                           file_name=f"{uuid.uuid4()}_exp3.csv",
                           mime="text/csv")
    else:
        word = words[i]
        st.subheader(f"Mot {i+1} / 80")
        mask_ph = st.empty()
        word_ph = st.empty()
        input_ph = st.empty()

        t0 = show_mask(mask_ph, word_ph, word, st.session_state.soa)
        resp = input_ph.text_input("Retapez le mot :", key=f"exp_{i}")
        if resp:
            rt = (time.perf_counter() - t0) * 1000
            add_response(word, int(rt), resp.strip())
            st.session_state.idx += 1
            st.session_state.soa += CYCLE_INC
            st.experimental_rerun()
