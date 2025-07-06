# app.py  ──────────────────────────────────────────────────────
# Évaluation Lecture / Écriture – Module 1
# Formulaire + Test vocabulaire + passage au module 2
# ──────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import uuid
import threading

# =============================================================
# Lancer la génération des 80 mots en tâche de fond
# =============================================================
def _prepare_stimuli():
    try:
        from get_stimuli import get_stimuli
        st.session_state["stimuli"] = get_stimuli()
        st.session_state["stimuli_ready"] = True
    except Exception as e:
        st.session_state["stimuli_error"] = str(e)

if "stimuli_ready" not in st.session_state:
    st.session_state.update(stimuli_ready=False, stimuli_error=None)
    threading.Thread(target=_prepare_stimuli, daemon=True).start()

# =============================================================
# Interface principale
# =============================================================
def main():
    st.set_page_config(page_title="Évaluation Lecture/Écriture – Module 1",
                       page_icon="📝", layout="centered")

    st.title("📝 Évaluation Lecture / Écriture – Module 1")
    st.write(
        "Bienvenue ! Remplissez d’abord vos **informations générales**, "
        "puis répondez au **Test 1**. "
        "Vous passerez ensuite au module suivant."
    )

    # ---------- 1. Informations générales ----------
    st.header("Informations générales")

    col1, col2 = st.columns([3, 1])
    with col1:
        participant_id = st.text_input(
            "Identifiant participant (facultatif : laissez vide pour qu’il soit généré)"
        )

    if participant_id.strip() == "":
        participant_id = str(uuid.uuid4())          # identifiant auto

    with col2:
        st.markdown("Identifiant utilisé :")
        st.code(participant_id, language="")

    age  = st.number_input("Âge (en années)", 16, 99, 25, 1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    etude = st.selectbox(
        "Niveau d’étude",
        ["Collège", "Lycée", "Baccalauréat", "Bac +2",
         "Licence / Master", "Doctorat", "Autre"],
    )

    st.markdown("---")

    # ---------- 2. Test 1 : vocabulaire ----------
    st.header("Test 1 – Vocabulaire (synonyme)")
    st.write("Choisissez le mot **le plus proche** du sens de : **impétueux**")

    options = ["Calme", "Fougueux", "Timide", "Lent"]
    reponse_vocab = st.radio("Votre réponse :", options, index=None)

    st.markdown("---")

    # ---------- 3. Sauvegarde locale des réponses ----------
    df = pd.DataFrame({
        "participant_id": [participant_id],
        "age":  [age],
        "sexe": [sexe],
        "etude": [etude],
        "test1_item": ["impétueux"],
        "test1_reponse": [reponse_vocab],
    })
    st.session_state["module1_df"] = df          # utile si tu veux le ré-utiliser

    # ---------- 4. Passage au module suivant ----------
    st.header("Module suivant")

    btn_disabled = (reponse_vocab is None)
    if st.button("➡️ Passer au Test 2", disabled=btn_disabled):
        try:
            # cas le plus simple : tu utilises le système multi-pages natif
            st.switch_page("pages/Module2.py")   # adapte le chemin si besoin
        except (RuntimeError, KeyError):
            # si tu n’es pas en multi-page, on met juste un flag
            st.session_state["go_next"] = True
            st.info("Module 2 : ouvrez la page suivante dans le menu latéral.")

    # ---------- 5. Infos sur la préparation des stimuli ----------
    if st.session_state.get("stimuli_ready"):
        st.success("Les 80 mots du module suivant sont déjà prêts ✅")
    elif st.session_state.get("stimuli_error"):
        st.error("Erreur pendant la préparation des 80 mots : "
                 + st.session_state["stimuli_error"])

# -------------------------------------------------------------
if __name__ == "__main__":
    main()
