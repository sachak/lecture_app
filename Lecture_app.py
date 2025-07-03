# -*- coding: utf-8 -*-
# =============================================================
# Évaluation Lecture / Écriture – Module 1
# Infos générales + premier test vocabulaire + export CSV
# =============================================================

import streamlit as st
import pandas as pd
import uuid  # pour générer un identifiant unique si l’utilisateur n’en saisit pas

# -------------------------------------------------------------
#  FONCTION PRINCIPALE
# -------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Évaluation Lecture/Écriture – Module 1",
        page_icon="📝",
        layout="centered",
    )

    st.title("📝 Évaluation Lecture / Écriture – Module 1")
    st.write(
        "Bienvenue ! Remplissez d'abord vos **informations générales**, "
        "puis répondez au **Test 1**. "
        "Vous pourrez ensuite télécharger un **fichier CSV** contenant vos réponses."
    )

    # ---------- 1. Informations générales ----------
    st.header("Informations générales")

    col1, col2 = st.columns([3, 1])
    with col1:
        participant_id = st.text_input(
            "Identifiant participant (facultatif : laissez vide pour qu’il soit généré)"
        )

    # Génération d’un identifiant aléatoire si champ vide
    if participant_id.strip() == "":
        participant_id = str(uuid.uuid4())

    with col2:
        st.markdown("Identifiant utilisé :")
        st.code(participant_id)

    age = st.number_input("Âge (en années)", min_value=16, max_value=99, value=25, step=1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    etude = st.selectbox(
        "Niveau d’étude",
        [
            "Collège",
            "Lycée",
            "Baccalauréat",
            "Bac +2",
            "Licence / Master",
            "Doctorat",
            "Autre",
        ],
    )

    st.markdown("---")

    # ---------- 2. Test 1 : Vocabulaire ----------
    st.header("Test 1 – Vocabulaire (synonyme)")
    st.write("Choisissez le mot **le plus proche** du sens de : **impétueux**")

    options = ["Calme", "Fougueux", "Timide", "Lent"]
    reponse_vocab = st.radio("Votre réponse :", options, index=None)

    st.markdown("---")

    # ---------- 3. Construction du CSV ----------
    data = {
        "participant_id": [participant_id],
        "age": [age],
        "sexe": [sexe],
        "etude": [etude],
        "test1_item": ["impétueux"],
        "test1_reponse": [reponse_vocab],
    }
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # ---------- 4. Téléchargement ----------
    st.header("Téléchargement")

    st.download_button(
        label="📥 Télécharger mes réponses (CSV)",
        data=csv_bytes,
        file_name=f"{participant_id}_module1.csv",
        mime="text/csv",
        disabled=reponse_vocab is None,  # activé seulement après réponse
    )

    st.info(
        "Après téléchargement, vous pourrez fermer la page ou passer au module suivant."
    )


# -------------------------------------------------------------
#  POINT D’ENTRÉE
# -------------------------------------------------------------
if __name__ == "__main__":
    main()
