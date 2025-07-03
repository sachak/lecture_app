# -*- coding: utf-8 -*-
import uuid
import pandas as pd
import streamlit as st

# -------- CONFIG GÉNÉRALE ----------------------------------------------------
st.set_page_config(page_title="Évaluation Lecture/Écriture – Module 1",
                   page_icon="📝", layout="centered")

# -------- INIT SESSION_STATE -------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 0
if "infos" not in st.session_state:
    st.session_state.infos = {}
if "rep" not in st.session_state:
    st.session_state.rep = {}

# -------- OUTILS -------------------------------------------------------------
def next_page():
    st.session_state.page += 1
    st.experimental_rerun()

def btn_suivant(ok: bool, label="Suivant ➡️"):
    st.button(label, disabled=not ok, on_click=next_page,
              key=f"btn_{st.session_state.page}")

# -------- PAGE 0  : INFOS ----------------------------------------------------
def page_infos():
    st.title("📝 Évaluation Lecture / Écriture – Module 1")
    st.subheader("Informations générales")

    pid = st.text_input("Identifiant (laisser vide pour auto-génération)")
    if not pid.strip():
        pid = str(uuid.uuid4())

    age  = st.number_input("Âge (années)", 16, 99, 25, 1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    niv  = st.selectbox("Niveau d’étude",
                        ["Collège", "Lycée", "Baccalauréat", "Bac +2",
                         "Licence / Master", "Doctorat", "Autre"])
    st.session_state.infos = dict(participant_id=pid, age=age, sexe=sexe, etude=niv)

    st.markdown("---")
    btn_suivant(True)

# -------- PAGE 1  : QCM 1 ----------------------------------------------------
def page_qcm1():
    st.header("Test 1 – Vocabulaire")
    st.write("Synonyme le plus proche de **impétueux**")
    choix = st.radio("Votre réponse :",
                     ["Calme", "Fougueux", "Timide", "Lent"],
                     index=None, key="q1")
    if choix:
        st.session_state.rep["impétueux"] = choix
    st.markdown("---")
    btn_suivant(choix is not None)

# -------- PAGE 2  : QCM 2 ----------------------------------------------------
def page_qcm2():
    st.header("Test 2 – Vocabulaire")
    st.write("Synonyme le plus proche de **hirsute**")
    choix = st.radio("Votre réponse :",
                     ["Ébouriffé", "Lisse", "Propre", "Rasé"],
                     index=None, key="q2")
    if choix:
        st.session_state.rep["hirsute"] = choix
    st.markdown("---")
    btn_suivant(choix is not None, label="Terminer ✅")

# -------- PAGE 3  : SYNTHÈSE + CSV (1 ligne) ---------------------------------
def page_fin():
    st.header("🎉 Merci pour votre participation !")

    # données sur une seule ligne (pas d’en-tête)
    ligne = {**st.session_state.infos, **st.session_state.rep}
    df = pd.DataFrame([ligne])
    csv_text = df.to_csv(index=False, header=False, sep=';',
                         encoding='utf-8-sig')

    st.subheader("Récapitulatif")
    st.dataframe(df)

    st.download_button("📥 Télécharger (CSV 1 ligne)",
                       data=csv_text,
                       file_name=f"{ligne['participant_id']}_module1.csv",
                       mime="text/csv")
    st.success("Fichier prêt – vous pouvez fermer l’onglet.")

# -------- ROUTAGE ------------------------------------------------------------
PAGES = {0: page_infos, 1: page_qcm1, 2: page_qcm2, 3: page_fin}
PAGES.get(st.session_state.page, page_infos)()
