# -*- coding: utf-8 -*-
"""
Évaluation Lecture / Écriture
  • Module 1 : QCM Vocabulaire
  • Module 2 : Décision lexicale (10 essais ; timeout 2000 ms)
"""
import time, uuid, pandas as pd, streamlit as st
from streamlit_autorefresh import st_autorefresh   # pip install streamlit-autorefresh

# ────────────────────────────── PARAMÈTRES GÉNÉRAUX ──────────────────────────
st.set_page_config(page_title="Évaluation Lecture/Écriture",
                   page_icon="📝", layout="centered")

TIME_LIMIT_MS   = 2_000     # délai maxi pour répondre (lexicale)
REFRESH_MS      = 100       # période d'auto-refresh pendant l'attente

# ────────────────────────────── ÉTAT PERSISTANT ──────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)

    # module QCM
    s.setdefault("infos", {})
    s.setdefault("rep_qcm", {})

    # module décision lexicale
    s.setdefault("trial",           0)        # index essai courant
    s.setdefault("in_trial",        False)    # True = phase stimuli en cours
    s.setdefault("trial_start",     0.0)      # horodatage apparition stimuli
    s.setdefault("lexi_results",    [])       # liste dict essais
    s.setdefault("feedback_msg",    "")       # message entre essais
init_state()

# ────────────────────────────── OUTILS ───────────────────────────────────────
def next_page():
    st.session_state.page += 1
    st.experimental_rerun()

def btn_suivant(ok=True, label="Suivant ➡️"):
    st.button(label, disabled=not ok, on_click=next_page,
              key=f"btn_{st.session_state.page}")

def record_result(prime, cible, typ, cond, cle_corr,
                  reponse, rt, too_slow):
    correcte = (reponse == cle_corr) and (not too_slow)
    st.session_state.lexi_results.append(dict(
        prime=prime, cible=cible, type=typ, cond=cond,
        cle_correcte=cle_corr, reponse=reponse,
        rt=rt, too_slow=too_slow, correcte=correcte
    ))
    # message feedback
    st.session_state.feedback_msg = (
        "correct!" if correcte else "wrong response, or too slow!"
    )

# ────────────────────────────── PAGE 0 : INFOS ───────────────────────────────
def page_infos():
    st.title("📝 Évaluation Lecture / Écriture")
    st.subheader("Informations générales")

    pid = st.text_input("Identifiant (laisser vide pour auto-génération)")
    pid = pid.strip() or str(uuid.uuid4())

    age  = st.number_input("Âge (années)", 16, 99, 25, 1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    niv  = st.selectbox("Niveau d’étude",
                        ["Collège", "Lycée", "Baccalauréat", "Bac +2",
                         "Licence / Master", "Doctorat", "Autre"])

    st.session_state.infos = dict(
        participant_id=pid, age=age, sexe=sexe, etude=niv
    )
    st.markdown("---")
    btn_suivant()

# ────────────────────────────── PAGE 1 : QCM 1 ───────────────────────────────
def page_qcm1():
    st.header("Test 1 – Vocabulaire")
    st.write("Synonyme le plus proche de **impétueux**")

    choix = st.radio("Votre réponse :", ["Calme", "Fougueux", "Timide", "Lent"],
                     index=None, key="q1")
    if choix:
        st.session_state.rep_qcm["impétueux"] = choix

    st.markdown("---")
    btn_suivant(choix is not None)

# ────────────────────────────── PAGE 2 : QCM 2 ───────────────────────────────
def page_qcm2():
    st.header("Test 2 – Vocabulaire")
    st.write("Synonyme le plus proche de **hirsute**")

    choix = st.radio("Votre réponse :",
                     ["Ébouriffé", "Lisse", "Propre", "Rasé"],
                     index=None, key="q2")
    if choix:
        st.session_state.rep_qcm["hirsute"] = choix

    st.markdown("---")
    btn_suivant(choix is not None, label="Commencer la décision lexicale ➡️")

# ────────────────────────── TABLE STIMULI DÉCISION LEXICALE ──────────────────
stimuli = pd.DataFrame([
    # prime      cible        type            cond  cle (1=Mot, 2=Non-mot)
    ["MEDECIN",  "INFIRMIER", "associés",      1,   1],
    ["MEDECIN",  "FLIPO",     "non-mot",       3,   2],
    ["ARBRE",    "MEDECIN",   "non-associés",  2,   1],
    ["MEDECIN",  "INFIRMIER", "non-associés",  2,   1],
    ["MEDECIN",  "FLIPO",     "non-mot",       3,   2],
    ["BEURRE",   "PAIN",      "associés",      1,   1],
    ["PAIN",     "MEDECIN",   "non-associés",  2,   1],
    ["SOAM",     "GANT",      "non-mot",       3,   2],
    ["NART",     "TRIEF",     "non-mot",       3,   2],
    ["PLAME",    "VIN",       "non-mot",       3,   2],
], columns=["prime", "cible", "type", "cond", "cle"])

# ───────────────────── PAGE 3 : INSTRUCTIONS LEXICALE ────────────────────────
def page_lexi_instructions():
    st.header("Module 2 – Décision lexicale (entraînement 10 essais)")
    st.write("""
Étapes d’un essai :
1. « + » 500 ms  
2. Écran blanc 500 ms  
3. Deux mots s’affichent (le **second** est la cible)  

Vous disposez de **2 s** pour décider si la cible est un **mot français** :
• **A** (ou bouton « Mot ») pour *Mot*  
• **L** (ou bouton « Non-mot ») pour *Non-mot*  

Si vous êtes trop lent, la mention *wrong response, or too slow!* apparaît.
""")
    btn_suivant()

# ───────────────────── PAGE 4 : ESSAI LEXICALE ───────────────────────────────
def page_lexi_trial():
    i = st.session_state.trial
    if i >= len(stimuli):
        next_page()           # fin des 10 essais
        return

    # ——————————————————— initialisation essai ———————————————————
    if not st.session_state.in_trial:
        st.session_state.in_trial    = True
        st.session_state.trial_start = 0.0      # pour plus tard

        # PHASE 1 : fixation + blanc (exécutée une seule fois)
        _, col_centre, _ = st.columns([1, 2, 1])
        with col_centre:
            st.markdown("<h1 style='text-align:center'>+</h1>",
                        unsafe_allow_html=True)
            time.sleep(0.5)
            st.empty()
            time.sleep(0.5)
        # (après ces 1 000 ms on continue avec l’affichage des mots)

    # ——————————————————— AFFICHAGE STIMULI + RÉPONSE ——————————————————
    prime, cible, typ, cond, cle_corr = stimuli.iloc[i]

    # auto-refresh toutes les REFRESH_MS pour surveiller le timeout
    st_autorefresh(interval=REFRESH_MS, key=f"auto_trial_{i}")

    # colonne centrale pour garder les mots centrés
    _, col_centre, _ = st.columns([1, 2, 1])
    with col_centre:
        st.markdown(
            f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
            f"{prime}<br>{cible}</div>",
            unsafe_allow_html=True
        )

    # horodatage début stimuli (si pas déjà mis)
    if st.session_state.trial_start == 0.0:
        st.session_state.trial_start = time.perf_counter()

    # boutons de réponse
    col_mot, col_non = st.columns(2)
    clicked = None
    with col_mot:
        if st.button("Mot ✔️", key=f"mot_{i}"):
            clicked = 1
    with col_non:
        if st.button("Non-mot ❌", key=f"non_{i}"):
            clicked = 2

    now = time.perf_counter()
    rt_ms = int((now - st.session_state.trial_start) * 1000)

    # ——————————————————— 1) CLIC avant 2 000 ms ————————————————————
    if clicked is not None and rt_ms <= TIME_LIMIT_MS:
        record_result(prime, cible, typ, cond, cle_corr,
                      reponse=clicked, rt=rt_ms, too_slow=False)
        st.session_state.in_trial = False
        st.session_state.trial   += 1
        st.session_state.page = 5          # feedback
        st.experimental_rerun()

    # ——————————————————— 2) TROP LENT (>2 000 ms) ————————————————————
    if rt_ms > TIME_LIMIT_MS:
        record_result(prime, cible, typ, cond, cle_corr,
                      reponse=None, rt=rt_ms, too_slow=True)
        st.session_state.in_trial = False
        st.session_state.trial   += 1
        st.session_state.page = 5          # feedback
        st.experimental_rerun()

# ───────────────────── PAGE 5 : FEEDBACK APRÈS ESSAI ─────────────────────────
def page_lexi_feedback_trial():
    msg = st.session_state.get("feedback_msg", "")
    st.markdown(f"<h2 style='text-align:center'>{msg}</h2>",
                unsafe_allow_html=True)

    # durée d'affichage : 500 ms si correct ; 1 500 ms sinon
    wait = 0.5 if msg == "correct!" else 1.5
    time.sleep(wait)
    next_page()              # retourne à page 4 (essai suivant)

# ───────────────────── PAGE 6 : FEEDBACK FINAL LEX ───────────────────────────
def page_lexi_feedback_final():
    st.header("Fin de l’entraînement – Décision lexicale")

    df = pd.DataFrame(st.session_state.lexi_results)
    good = df[df.correcte]

    def mean_rt(cond):
        sel = good[good.cond == cond].rt
        return int(sel.mean()) if not sel.empty else "—"

    st.write(f"Related words : {mean_rt(1)} ms")
    st.write(f"Unrelated words : {mean_rt(2)} ms")
    st.write(f"Nonsense word(s) : {mean_rt(3)} ms")

    st.markdown("---")
    btn_suivant(label="Terminer ✅")

# ───────────────────── PAGE 7 : EXPORT CSV & FIN ─────────────────────────────
def page_fin():
    st.header("🎉 Merci pour votre participation !")

    # ---------- CSV QCM
    ligne = {**st.session_state.infos, **st.session_state.rep_qcm}
    df_qcm = pd.DataFrame([ligne])
    csv_qcm = df_qcm.to_csv(index=False, header=False, sep=';',
                            encoding='utf-8-sig').encode('utf-8-sig')
    st.subheader("Réponses QCM")
    st.dataframe(df_qcm)
    st.download_button("📥 Télécharger QCM (CSV)",
                       data=csv_qcm,
                       file_name=f"{ligne['participant_id']}_module1.csv",
                       mime="text/csv")

    # ---------- CSV Décision lexicale
    df_lexi = pd.DataFrame(st.session_state.lexi_results)
    if not df_lexi.empty:
        df_lexi.insert(0, "participant_id", ligne["participant_id"])
        csv_lexi = df_lexi.to_csv(index=False, sep=';',
                                 encoding='utf-8-sig').encode('utf-8-sig')
        st.subheader("Réponses Décision lexicale")
        st.dataframe(df_lexi)
        st.download_button("📥 Télécharger Lexicale (CSV)",
                           data=csv_lexi,
                           file_name=f"{ligne['participant_id']}_lexicale.csv",
                           mime="text/csv")
    st.success("Fichiers prêts – vous pouvez fermer l’onglet.")

# ───────────────────── ROUTAGE ───────────────────────────────────────────────
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
