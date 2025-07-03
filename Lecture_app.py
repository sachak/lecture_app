# -*- coding: utf-8 -*-
"""
Application Streamlit : Évaluation Lecture / Écriture – Module 1
• Page 0 : informations générales
• Page 1 : QCM 1
• Page 2 : QCM 2
• Page 3 : récapitulatif + export CSV
"""

import uuid
import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# CONFIGURATION GÉNÉRALE
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Évaluation Lecture/Écriture – Module 1",
    page_icon="📝",
    layout="centered",
)

# ------------------------------------------------------------------
# INITIALISATION DE L'ÉTAT (session_state)
# ------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 0            # page courante
if "infos" not in st.session_state:
    st.session_state.infos = {}          # données personnelles
if "reponses" not in st.session_state:
    st.session_state.reponses = {}       # réponses aux QCM

# ------------------------------------------------------------------
# FONCTIONS UTILITAIRES
# ------------------------------------------------------------------
def next_page() -> None:
    """Passe à la page suivante et force le refresh."""
    st.session_state.page += 1
    st.experimental_rerun()


def bouton_suivant(actif: bool, label: str = "Suivant ➡️") -> None:
    st.button(label, on_click=next_page, disabled=not actif, key=f"btn_{st.session_state.page}")

# ------------------------------------------------------------------
# PAGE 0 : INFORMATIONS GÉNÉRALES
# ------------------------------------------------------------------
def page_infos() -> None:
    st.title("📝 Évaluation Lecture / Écriture – Module 1")
    st.subheader("Informations générales")

    identifiant = st.text_input(
        "Identifiant participant (laissez vide pour génération automatique)"
    )
    if identifiant.strip() == "":
        identifiant = str(uuid.uuid4())

    age = st.number_input("Âge (en années)", 16, 99, 25, 1)
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

    st.session_state.infos = {
        "participant_id": identifiant,
        "age": age,
        "sexe": sexe,
        "etude": etude,
    }

    st.markdown("---")
    bouton_suivant(actif=True)

# ------------------------------------------------------------------
# PAGE 1 : QCM 1
# ------------------------------------------------------------------
def page_qcm1() -> None:
    st.header("Test 1 – Vocabulaire")
    st.write("Choisissez le synonyme le plus proche de **impétueux**")

    choix = st.radio(
        "Votre réponse :",
        ["Calme", "Fougueux", "Timide", "Lent"],
        index=None,
        key="qcm1",
    )

    if choix is not None:
        st.session_state.reponses["impétueux"] = choix

    st.markdown("---")
    bouton_suivant(actif=choix is not None)

# ------------------------------------------------------------------
# PAGE 2 : QCM 2
# ------------------------------------------------------------------
def page_qcm2() -> None:
    st.header("Test 2 – Vocabulaire")
    st.write("Choisissez le synonyme le plus proche de **hirsute**")

    choix = st.radio(
        "Votre réponse :",
        ["Ébouriffé", "Lisse", "Propre", "Rasé"],
        index=None,
        key="qcm2",
    )

    if choix is not None:
        st.session_state.reponses["hirsute"] = choix

    st.markdown("---")
    bouton_suivant(actif=choix is not None, label="Terminer ✅")

# ------------------------------------------------------------------
# PAGE 3 : SYNTHÈSE + EXPORT
# ------------------------------------------------------------------
def page_synthese() -> None:
    st.header("🎉 Merci pour votre participation !")

    # Assemblage des données
    data = {**st.session_state.infos, **st.session_state.reponses}
    df = pd.DataFrame([data])
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    st.subheader("Récapitulatif")
    st.dataframe(df)

    st.download_button(
        "📥 Télécharger mes réponses (CSV)",
        data=csv_bytes,
        file_name=f"{st.session_state.infos['participant_id']}_module1.csv",
        mime="text/csv",
    )

    st.success("Vous pouvez maintenant fermer l’onglet.")

# ------------------------------------------------------------------
# ROUTAGE DES PAGES
# ------------------------------------------------------------------
PAGES = {
    0: page_infos,
    1: page_qcm1,
    2: page_qcm2,
    3: page_synthese,
}

# Exécution de la page demandée
PAGES.get(st.session_state.page, page_infos)()
