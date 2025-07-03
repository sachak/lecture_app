# -*- coding: utf-8 -*-
"""
Évaluation Lecture / Écriture
  • Module 1 : Vocabulaire (QCM)
  • Module 2 : Décision lexicale (10 essais + feedback)
"""
import time, uuid, pandas as pd, streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Évaluation Lecture/Écriture",
                   page_icon="📝", layout="centered")

# ──────────────────────────────────────────────────────────────────────────────
# ÉTATS PERSISTANTS
# ──────────────────────────────────────────────────────────────────────────────
def init_state():
    d = st.session_state
    d.setdefault("page",         0)   # numéro de page
    d.setdefault("infos",        {})  # infos démographiques
    d.setdefault("rep",          {})  # réponses QCM

    # Décision lexicale
    d.setdefault("trial",        0)   # index d’essai courant
    d.setdefault("start_time",   0.)  # chrono
    d.setdefault("lexi_results", [])  # liste des essais
init_state()

# ──────────────────────────────────────────────────────────────────────────────
# OUTILS
# ──────────────────────────────────────────────────────────────────────────────
def next_page():
    st.session_state.page += 1
    st.experimental_rerun()

def btn_suivant(ok=True, label="Suivant ➡️"):
    st.button(label, disabled=not ok, on_click=next_page,
              key=f"btn_{st.session_state.page}")

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 0 : INFOS PARTICIPANT
# ──────────────────────────────────────────────────────────────────────────────
def page_infos():
    st.title("📝 Évaluation Lecture / Écriture")
    st.subheader("Informations générales")

    pid = st.text_input("Identifiant (laisser vide pour auto-génération)")
    pid = pid.strip() or str(uuid.uuid4())

    age  = st.number_input("Âge (années)", 16, 99, 25, 1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    niv  = st.selectbox(
        "Niveau d’étude",
        ["Collège", "Lycée", "Baccalauréat", "Bac +2",
         "Licence / Master", "Doctorat", "Autre"]
    )

    st.session_state.infos = dict(
        participant_id=pid, age=age, sexe=sexe, etude=niv
    )

    st.markdown("---")
    btn_suivant()

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 1 : QCM 1
# ──────────────────────────────────────────────────────────────────────────────
def page_qcm1():
    st.header("Test 1 – Vocabulaire")
    st.write("Synonyme le plus proche de **impétueux**")

    choix = st.radio(
        "Votre réponse :",
        ["Calme", "Fougueux", "Timide", "Lent"],
        index=None, key="q1"
    )
    if choix:
        st.session_state.rep["impétueux"] = choix

    st.markdown("---")
    btn_suivant(choix is not None)

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 2 : QCM 2
# ──────────────────────────────────────────────────────────────────────────────
def page_qcm2():
    st.header("Test 2 – Vocabulaire")
    st.write("Synonyme le plus proche de **hirsute**")

    choix = st.radio(
        "Votre réponse :",
        ["Ébouriffé", "Lisse", "Propre", "Rasé"],
        index=None, key="q2"
    )
    if choix:
        st.session_state.rep["hirsute"] = choix

    st.markdown("---")
    btn_suivant(choix is not None, label="Commencer la décision lexicale ➡️")

# ──────────────────────────────────────────────────────────────────────────────
# STIMULI DÉCISION LEXICALE
# ──────────────────────────────────────────────────────────────────────────────
stimuli = pd.DataFrame([
    # prime,  cible,       type,            cond, cle (1=mot,2=non-mot)
    ["MEDECIN", "INFIRMIER", "associés",      1,   1],
    ["MEDECIN", "FLIPO",     "non-mot",       3,   2],
    ["ARBRE",   "MEDECIN",   "non-associés",  2,   1],
    ["MEDECIN", "INFIRMIER", "non-associés",  2,   1],
    ["MEDECIN", "FLIPO",     "non-mot",       3,   2],
    ["BEURRE",  "PAIN",      "associés",      1,   1],
    ["PAIN",    "MEDECIN",   "non-associés",  2,   1],
    ["SOAM",    "GANT",      "non-mot",       3,   2],
    ["NART",    "TRIEF",     "non-mot",       3,   2],
    ["PLAME",   "VIN",       "non-mot",       3,   2],
], columns=["prime", "cible", "type", "cond", "cle"])

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 3 : INSTRUCTIONS DÉCISION LEXICALE
# ──────────────────────────────────────────────────────────────────────────────
def page_lexi_instructions():
    st.header("Module 2 – Décision lexicale")
    st.write("""
Sur chaque essai :
1. Un point de fixation « + » apparaît brièvement  
2. Deux mots s’affichent (le second est la **cible**)  
3. Décidez le plus vite possible si **le second est un mot français**  

• Cliquez sur **“Mot”** si c’est un mot  
• Cliquez sur **“Non-mot”** si ce n’en est pas un  

Vous allez commencer par 10 essais d’entraînement.
""")
    btn_suivant()

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 4 : ESSAIS DÉCISION LEXICALE (centre corrigé)
# ──────────────────────────────────────────────────────────────────────────────
def page_lexi_trial():
    i = st.session_state.trial
    if i >= len(stimuli):
        next_page()
        return

    prime, cible, typ, cond, cle = stimuli.iloc[i]

    # 1. Ligne 3 colonnes : centre réservé aux stimuli
    _, col_centre, _ = st.columns([1, 2, 1])
    with col_centre:
        ph = st.empty()      # placeholder uniquement dans la colonne centrale

    # 2. Point de fixation (500 ms)
    ph.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
    time.sleep(0.5)

    # 3. Blanc (500 ms)
    ph.empty()
    time.sleep(0.5)

    # 4. Affichage des mots (centrés)
    ph.markdown(
        f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
        f"{prime}<br>{cible}</div>",
        unsafe_allow_html=True
    )

    # Chronomètre
    st.session_state.start_time = time.perf_counter()

    # 5. Ligne suivante : 2 colonnes pour les boutons
    col_mot, col_non = st.columns(2)
    reponse = None
    with col_mot:
        if st.button("Mot ✔️", key=f"mot_{i}"):
            reponse = 1
    with col_non:
        if st.button("Non-mot ❌", key=f"non_{i}"):
            reponse = 2

    # 6. Enregistrement et passage à l’essai suivant
    if reponse is not None:
        rt = int((time.perf_counter() - st.session_state.start_time) * 1000)
        correct = reponse == cle
        st.session_state.lexi_results.append(
            dict(prime=prime, cible=cible, type=typ, cond=cond,
                 cle_correcte=cle, reponse=reponse,
                 correcte=correct, rt=rt)
        )
        st.session_state.trial += 1
        st.experimental_rerun()

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 5 : FEEDBACK DÉCISION LEXICALE
# ──────────────────────────────────────────────────────────────────────────────
def page_lexi_feedback():
    st.header("Fin de l’entraînement – Décision lexicale")

    df = pd.DataFrame(st.session_state.lexi_results)
    good = df[df.correcte]          # seulement les bonnes réponses

    def moyenne(cond):
        sel = good[good.cond == cond].rt
        return int(sel.mean()) if not sel.empty else None

    assoc = moyenne(1)
    non_assoc = moyenne(2)
    non_mot = moyenne(3)

    st.write(f"• Mots **associés** : {assoc or '—'} ms")
    st.write(f"• Mots **non-associés** : {non_assoc or '—'} ms")
    st.write(f"• **Pseudo-mots** : {non_mot or '—'} ms")

    st.markdown("---")
    btn_suivant(label="Terminer ✅")

# ──────────────────────────────────────────────────────────────────────────────
# PAGE 6 : SYNTHÈSE & EXPORT CSV
# ──────────────────────────────────────────────────────────────────────────────
def page_fin():
    st.header("🎉 Merci pour votre participation !")

    # ---------- QCM
    ligne = {**st.session_state.infos, **st.session_state.rep}
    df_qcm = pd.DataFrame([ligne])
    csv_qcm = df_qcm.to_csv(index=False, header=False, sep=';',
                            encoding='utf-8-sig').encode('utf-8-sig')

    st.subheader("Vos réponses – QCM")
    st.dataframe(df_qcm)
    st.download_button("📥 Télécharger (CSV – QCM)",
                       data=csv_qcm,
                       file_name=f"{ligne['participant_id']}_module1.csv",
                       mime="text/csv")

    # ---------- Décision lexicale
    if st.session_state.lexi_results:
        df_lexi = pd.DataFrame(st.session_state.lexi_results)
        df_lexi.insert(0, "participant_id", ligne["participant_id"])
        csv_lexi = df_lexi.to_csv(index=False, sep=';',
                                 encoding='utf-8-sig').encode('utf-8-sig')

        st.subheader("Vos réponses – Décision lexicale")
        st.dataframe(df_lexi)
        st.download_button("📥 Télécharger (CSV – Lexicale)",
                           data=csv_lexi,
                           file_name=f"{ligne['participant_id']}_lexicale.csv",
                           mime="text/csv")

    st.success("Fichiers prêts – vous pouvez fermer l’onglet.")

# ──────────────────────────────────────────────────────────────────────────────
# ROUTAGE DES PAGES
# ──────────────────────────────────────────────────────────────────────────────
PAGES = {
    0: page_infos,
    1: page_qcm1,
    2: page_qcm2,
    3: page_lexi_instructions,
    4: page_lexi_trial,
    5: page_lexi_feedback,
    6: page_fin,
}
PAGES.get(st.session_state.page, page_infos)()
