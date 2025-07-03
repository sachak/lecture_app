# -*- coding: utf-8 -*-
"""
Mini-expérience « Décision lexicale » (10 essais)
timeline : + 500 ms → blanc 500 ms → mots (≤2 s) → feedback → essai suivant
enregistre : prime, cible, type, cond, réponse, RT, correcte, too_slow
"""
import time, uuid, pandas as pd, streamlit as st
from streamlit_autorefresh import st_autorefresh   # ← pour le timeout

st.set_page_config(page_title="Décision lexicale", page_icon="🔠")

# ─────────────────────────── PARAMÈTRES ──────────────────────────────────────
TIME_LIMIT   = 2000                # délai maxi pour répondre (ms)
FIX_DUR      = 0.5                 # durée « + » (s)
BLANK_DUR    = 0.5                 # durée blanc (s)
REFRESH_MS   = 50                  # intervalle auto-refresh (ms)

# ─────────────────────────── STIMULI ─────────────────────────────────────────
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

# ─────────────────────────── ÉTAT GLOBAL ─────────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page",         0)          # 0 = instructions, 1 = tâche, 2 = fin
    # Tâche
    s.setdefault("trial",        0)          # index essai
    s.setdefault("phase",        "fix")      # fix → blank → stim → fb
    s.setdefault("phase_start",  time.perf_counter())
    s.setdefault("rt_start",     0.0)        # horodatage apparition stimuli
    s.setdefault("fb_msg",       "")         # texte feedback
    s.setdefault("fb_dur",       0.0)        # durée du feedback
    s.setdefault("results",      [])         # log complet
init_state()

# ─────────────────────────── OUTILS ──────────────────────────────────────────
def reset_phase(new_phase):
    st.session_state.phase       = new_phase
    st.session_state.phase_start = time.perf_counter()

def log_trial(**kw):
    st.session_state.results.append(kw)

# ─────────────────────────── PAGE 0 : INSTRUCTIONS ───────────────────────────
def page_instructions():
    st.title("Décision lexicale – entraînement 10 essais")
    st.markdown("""
Sur chaque essai :

1. Un « + » pendant 500 ms  
2. Un écran blanc 500 ms  
3. Deux mots – décidez si **le second est un mot français**  
   • touche « A » ou bouton **Mot**  
   • touche « L » ou bouton **Non-mot**  
4. 2 s maximum pour répondre  
5. *correct!* 500 ms **ou** *wrong response, or too slow!* 1500 ms  
6. Nouvel essai

Répondez le plus vite et le plus justement possible.
""")
    if st.button("Commencer ➡️"):
        st.session_state.page = 1
        reset_phase("fix")
        st.experimental_rerun()

# ─────────────────────────── PAGE 1 : TÂCHE ──────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):                       # fini → page récap
        st.session_state.page = 2
        st.experimental_rerun()
        return

    # petit « tick » toutes REFRESH_MS pour gérer les délais
    st_autorefresh(interval=REFRESH_MS, key="refresh")

    prime, cible, typ, cond, cle_corr = stimuli.iloc[i]
    phase = st.session_state.phase
    now   = time.perf_counter()
    elapsed = now - st.session_state.phase_start

    # ───────────────  PHASE 1 : FIXATION  (+)  ────────────────
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>",
                    unsafe_allow_html=True)
        if elapsed >= FIX_DUR:
            reset_phase("blank")

    # ───────────────  PHASE 2 : BLANC  ────────────────────────
    elif phase == "blank":
        st.empty()                            # écran vide
        if elapsed >= BLANK_DUR:
            reset_phase("stim")
            st.session_state.rt_start = time.perf_counter()

    # ───────────────  PHASE 3 : STIMULI  ──────────────────────
    elif phase == "stim":
        # Affichage deux lignes centrées
        st.markdown(
            f"<div style='text-align:center;font-size:42px;line-height:1.2'>"
            f"{prime}<br>{cible}</div>",
            unsafe_allow_html=True
        )

        # boutons / touches
        col_mot, col_non = st.columns(2)
        clicked = None
        with col_mot:
            if st.button("Mot ✔️", key=f"mot_{i}"):
                clicked = 1
        with col_non:
            if st.button("Non-mot ❌", key=f"non_{i}"):
                clicked = 2

        rt = int((time.perf_counter() - st.session_state.rt_start) * 1000)

        # 1) CLIC pendant la fenêtre de 2 s
        if clicked is not None and rt <= TIME_LIMIT:
            correct = clicked == cle_corr
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=clicked,
                      rt=rt, too_slow=False, correcte=correct)
            st.session_state.fb_msg = "correct!" if correct else "wrong response, or too slow!"
            st.session_state.fb_dur = 0.5 if correct else 1.5
            reset_phase("fb")

        # 2) Aucune réponse et délai dépassé
        elif rt > TIME_LIMIT:
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=None,
                      rt=rt, too_slow=True, correcte=False)
            st.session_state.fb_msg = "wrong response, or too slow!"
            st.session_state.fb_dur = 1.5
            reset_phase("fb")

    # ───────────────  PHASE 4 : FEEDBACK  ─────────────────────
    elif phase == "fb":
        st.markdown(f"<h2 style='text-align:center'>{st.session_state.fb_msg}</h2>",
                    unsafe_allow_html=True)
        if elapsed >= st.session_state.fb_dur:
            st.session_state.trial += 1
            reset_phase("fix")               # essai suivant

# ─────────────────────────── PAGE 2 : RÉCAP & CSV ────────────────────────────
def page_end():
    st.title("Fin de l’entraînement")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df)

    csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Télécharger le CSV", data=csv,
                       file_name=f"{uuid.uuid4()}_lexicale.csv",
                       mime="text/csv")
    st.success("Merci ! Vous pouvez fermer l’onglet.")

# ─────────────────────────── ROUTAGE ─────────────────────────────────────────
if st.session_state.page == 0:
    page_instructions()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
