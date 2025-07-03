# -*- coding: utf-8 -*-
"""
Évaluation Lecture / Écriture
  • Module 1 : Vocabulaire (QCM)
  • Module 2 : Décision lexicale (10 essais, délai 2 s)
"""
import time, uuid, pandas as pd, streamlit as st

# ────────────────────────── CONFIGURATION ────────────────────────────────────
st.set_page_config(page_title="Évaluation Lecture/Écriture",
                   page_icon="📝", layout="centered")

TIME_LIMIT_MS = 2_000              # délai maximum pour répondre (2 000 ms)

# ────────────────────────── ÉTAT PERSISTANT ──────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page",           0)
    s.setdefault("infos",          {})
    s.setdefault("rep",            {})      # réponses QCM

    # Décision lexicale
    s.setdefault("trial",          0)       # index d’essai courant
    s.setdefault("start_time",     0.)      # horodatage début essai
    s.setdefault("lexi_results",   [])      # liste des essais
    s.setdefault("feedback_msg",   "")      # message après chaque essai
init_state()

# ────────────────────────── OUTILS ───────────────────────────────────────────
def next_page():
    st.session_state.page += 1
    st.experimental_rerun()

def btn_suivant(ok=True, label="Suivant ➡️"):
    st.button(label, disabled=not ok, on_click=next_page,
              key=f"btn_{st.session_state.page}")

# ────────────────────────── PAGE 0 : INFOS ───────────────────────────────────
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

# ────────────────────────── PAGE 1 : QCM 1 ───────────────────────────────────
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

# ────────────────────────── PAGE 2 : QCM 2 ───────────────────────────────────
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

# ────────────────────────── STIMULI DÉCISION LEXICALE ────────────────────────
stimuli = pd.DataFrame([
    #  prime      cible        type            cond  cle (1=mot,2=non-mot)
    ["MEDECIN",   "INFIRMIER", "associés",      1,   1],
    ["MEDECIN",   "FLIPO",     "non-mot",       3,   2],
    ["ARBRE",     "MEDECIN",   "non-associés",  2,   1],
    ["MEDECIN",   "INFIRMIER", "non-associés",  2,   1],
    ["MEDECIN",   "FLIPO",     "non-mot",       3,   2],
    ["BEURRE",    "PAIN",      "associés",      1,   1],
    ["PAIN",      "MEDECIN",   "non-associés",  2,   1],
    ["SOAM",      "GANT",      "non-mot",       3,   2],
    ["NART",      "TRIEF",     "non-mot",       3,   2],
    ["PLAME",     "VIN",       "non-mot",       3,   2],
], columns=["prime", "cible", "type", "cond", "cle"])

# ────────────────────────── PAGE 3 : INSTRUCTIONS LEX ────────────────────────
def page_lexi_instructions():
    st.header("Module 2 – Décision lexicale")
    st.write("""
Sur chaque essai :
1. Un point de fixation « + » apparaît brièvement  
2. Deux mots s’affichent (le second est la **cible**)  
3. Décidez le plus vite possible si **le second est un mot français**  

• Cliquez sur **“Mot”** si c’en est un  
• Cliquez sur **“Non-mot”** sinon  

Vous disposez de **2 secondes** ; au-delà la réponse sera comptée
comme « trop lente ».
""")
    btn_suivant()

# ────────────────────────── PAGE 4 : ESSAI LEX ───────────────────────────────
def page_lexi_trial():
    i = st.session_state.trial
    if i >= len(stimuli):                 # tous les essais terminés
        next_page()
        return

    prime, cible, typ, cond, cle = stimuli.iloc[i]

    # 1. Colonne centrale pour les stimuli
    _, col_centre, _ = st.columns([1, 2, 1])
    with col_centre:
        ph = st.empty()

    # 2. Point de fixation (500 ms)
    ph.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
    time.sleep(0.5)

    # 3. Blanc (500 ms)
    ph.empty()
    time.sleep(0.5)

    # 4. Affichage des deux mots
    ph.markdown(
        f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
        f"{prime}<br>{cible}</div>",
        unsafe_allow_html=True
    )
    st.session_state.start_time = time.perf_counter()

    # 5. Boutons de réponse
    col_mot, col_non = st.columns(2)
    reponse = None
    with col_mot:
        if st.button("Mot ✔️", key=f"mot_{i}"):
            reponse = 1
    with col_non:
        if st.button("Non-mot ❌", key=f"non_{i}"):
            reponse = 2

    # 6. Si clic -> évaluation
    if reponse is not None:
        rt = int((time.perf_counter() - st.session_state.start_time) * 1000)
        too_slow = rt > TIME_LIMIT_MS
        correcte = (reponse == cle) and (not too_slow)

        # enregistrement
        st.session_state.lexi_results.append(
            dict(prime=prime, cible=cible, type=typ, cond=cond,
                 cle_correcte=cle, reponse=reponse,
                 rt=rt, too_slow=too_slow, correcte=correcte)
        )

        # message feedback
        st.session_state.feedback_msg = (
            "Bonne réponse !" if correcte else
            "Réponse incorrecte ou trop lente !"
        )

        # passage à la page feedback
        st.session_state.trial += 1
        st.session_state.page  = 5          # page feedback
        st.experimental_rerun()

# ────────────────────────── PAGE 5 : FEEDBACK ESSAI ──────────────────────────
def page_lexi_feedback_trial():
    msg = st.session_state.get("feedback_msg", "")
    st.markdown(f"<h2 style='text-align:center'>{msg}</h2>",
                unsafe_allow_html=True)
    btn_suivant(label="Continuer")

# ────────────────────────── PAGE 6 : FEEDBACK FINAL LEX ──────────────────────
def page_lexi_feedback_final():
    st.header("Fin de l’entraînement – Décision lexicale")

    df = pd.DataFrame(st.session_state.lexi_results)
    good = df[df.correcte]                 # seules les réponses correctes

    def moyenne(cond):
        sel = good[good.cond == cond].rt
        return int(sel.mean()) if not sel.empty else None

    assoc     = moyenne(1)
    nonassoc  = moyenne(2)
    nonmot    = moyenne(3)

    st.write(f"• Mots **associés** : {assoc or '—'} ms")
    st.write(f"• Mots **non-associés** : {nonassoc or '—'} ms")
    st.write(f"• **Pseudo-mots** : {nonmot or '—'} ms")

    st.markdown("---")
    btn_suivant(label="Terminer ✅")

# ────────────────────────── PAGE 7 : SYNTHÈSE & EXPORT ───────────────────────
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

# ────────────────────────── ROUTAGE ──────────────────────────────────────────
PAGES = {
    0: page_infos,
    1: page_qcm1,
    2: page_qcm2,
    3: page_lexi_instructions,
    4: page_lexi_trial,
    5: page_lexi_feedback_trial,
    6: page_lexi_feedback_final,
    7: page_fin,
}
PAGES.get(st.session_state.page, page_infos)()
