# -*- coding: utf-8 -*-
# =============================================================
# lecture_app.py – version 100 % Streamlit (zéro page blanche)
# =============================================================
import random, threading, time, uuid, io, pandas as pd, streamlit as st
from get_stimuli import get_stimuli          # ta fonction de tirage

# ---------- paramètres stimulus ---------------------------------------
MASK_TIME = 0.35     # s d’affichage masque ####
WORD_TIME = 0.02     # s avant de mettre le mot
INC_SOAA  = 0.014    # +14 ms après chaque essai
TRAIN     = ["MER", "SAC", "LOT"]

# ---------- sélection des 80 mots en tâche de fond --------------------
def _select():
    try:
        st.session_state.stimuli = get_stimuli()
        st.session_state.ready   = True
    except Exception as e:
        st.session_state.error   = str(e)
    finally:
        st.experimental_rerun()

if "ready" not in st.session_state:
    st.session_state.update(dict(
        ready=False, error=None, page="intro",
        idx=0, soa=MASK_TIME+WORD_TIME, data=[]
    ))
    threading.Thread(target=_select, daemon=True).start()

# ---------- fonction d’une épreuve ------------------------------------
def run_trial(word):
    placeholder = st.empty()
    placeholder.markdown(f"<h1 style='text-align:center'>"
                         + "#"*len(word) + "</h1>", True)
    time.sleep(WORD_TIME)
    placeholder.markdown(f"<h1 style='text-align:center'>{word}</h1>", True)
    t0 = time.perf_counter()
    resp = st.text_input("Retapez le mot :", key=str(uuid.uuid4()))
    if resp:
        rt = int((time.perf_counter() - t0)*1000)
        st.session_state.data.append(dict(word=word, rt_ms=rt,
                                          response=resp.strip()))
        st.session_state.soa += INC_SOAA
        st.session_state.idx += 1
        st.experimental_rerun()

# ======================================================================
#  NAVIGATION
# ======================================================================
pg = st.session_state.page

if pg == "intro":
    st.title("Expérience 3 — instructions")
    st.write("Appuyez sur **Espace** quand le mot apparaît, "
             "retapez-le puis validez avec **Entrée**. "
             "Commençons par 3 essais d’entraînement.")
    if st.button("Commencer"): st.session_state.page="train"; st.experimental_rerun()

elif pg == "train":
    i = st.session_state.idx
    if i >= len(TRAIN):
        st.session_state.page, st.session_state.idx = "wait", 0
        st.experimental_rerun()
    else:
        st.subheader(f"Entraînement {i+1}/3")
        run_trial(TRAIN[i])

elif pg == "wait":
    if st.session_state.ready:
        st.session_state.page="exp"; st.experimental_rerun()
    elif st.session_state.error:
        st.error("Erreur tirage : "+st.session_state.error)
    else:
        st.info("Préparation des 80 mots…"); st.progress(None); time.sleep(2); st.experimental_rerun()

elif pg == "exp":
    i = st.session_state.idx
    W = st.session_state.stimuli
    if i >= len(W):
        st.success("Terminé !")
        df = pd.DataFrame(st.session_state.data)
        st.download_button("Télécharger résultats CSV",
                           df.to_csv(index=False).encode(),
                           file_name=f"{uuid.uuid4()}_exp3.csv",
                           mime="text/csv")
    else:
        st.subheader(f"Mot {i+1}/80")
        run_trial(W[i])
