# -*- coding: utf-8 -*-
# =============================================================
# Lecture_app.py  –  Module 1 + 3 essais fixes + tirage en tâche de fond
# =============================================================
import threading, time, uuid, pandas as pd, streamlit as st
from get_stimuli import get_stimuli          # prépare les 80 mots

# ------------------ préparation asynchrone des 80 mots ------------------
def _prepare():
    try:
        st.session_state.stimuli = get_stimuli()
        st.session_state.ready   = True
    except Exception as e:
        st.session_state.error   = str(e)
    finally:
        st.experimental_rerun()

if "ready" not in st.session_state:
    st.session_state.update(dict(ready=False, error=None))
    threading.Thread(target=_prepare, daemon=True).start()

# ------------------ essais d’entraînement (fixes) -----------------------
TRAIN_WORDS = ["MER", "SAC", "LOT"]

# ------------------ interface Module 1 ----------------------------------
def main():
    st.set_page_config(page_title="Évaluation Lecture/Écriture – Module 1",
                       page_icon="📝", layout="centered")

    if "page"  not in st.session_state: st.session_state.page  = "form"
    if "idx"   not in st.session_state: st.session_state.idx   = 0

    # ========== étape 1 : formulaire ====================================
    if st.session_state.page == "form":
        st.title("📝 Module 1 – formulaire + essais")
        pid = st.text_input("Identifiant participant (laisser vide ➡️ auto)")
        if pid.strip() == "": pid = str(uuid.uuid4())
        st.code(pid, language="")
        age  = st.number_input("Âge", 16, 99, 25, 1)
        sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
        etud = st.selectbox("Niveau d'étude",
                            ["Collège","Lycée","Bac","Bac+2",
                             "Licence/Master","Doctorat","Autre"])
        st.markdown("---")

        # ======= Test vocabulaire (impétueux) ============================
        st.header("Test 1 – vocabulaire")
        opt = ["Calme","Fougueux","Timide","Lent"]
        rep = st.radio("Synonyme de **impétueux** :", opt, index=None)

        if rep is not None:
            st.session_state.answers = pd.DataFrame({
                "participant_id":[pid], "age":[age], "sexe":[sexe],
                "etude":[etud], "test1_item":["impétueux"],
                "test1_reponse":[rep]
            })
            st.session_state.page = "train"
            st.experimental_rerun()

    # ========== étape 2 : entraînement (3 mots) =========================
    elif st.session_state.page == "train":
        i = st.session_state.idx
        if i >= 3:
            st.session_state.page = "wait"; st.experimental_rerun()
        else:
            st.subheader(f"Essai d’entraînement {i+1}/3")
            st.write("Mot :", TRAIN_WORDS[i])
            if st.button("Valider (fictif)"):
                st.session_state.idx += 1
                st.experimental_rerun()

    # ========== étape 3 : attente que les 80 mots soient prêts ==========
    elif st.session_state.page == "wait":
        if st.session_state.ready:
            st.success("80 mots prêts ! ➡️ Ouvrez le Module 2.")
        elif st.session_state.error:
            st.error("Erreur préparation stimuli :\n"+st.session_state.error)
        else:
            st.info("Préparation des 80 mots…"); st.progress(None); time.sleep(2); st.experimental_rerun()

# -----------------------------------------------------------------------
if __name__ == "__main__":
    main()
