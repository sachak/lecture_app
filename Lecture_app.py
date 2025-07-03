# -*- coding: utf-8 -*-
"""
Décision lexicale – 10 essais
(+) 500 ms → blanc 500 ms → 2 000 ms pour répondre → « Trop lent » si dépassement
Streamlit uniquement – compatible ≥1.33  (st.rerun)
"""
import time, uuid, pandas as pd, streamlit as st

# ───────── PARAMÈTRES ────────────────────────────────────────────────────────
TIME_LIMIT_MS = 2_000        # délai max pour répondre
FIX_DUR       = 0.5          # « + » 500 ms
BLANK_DUR     = 0.5          # blanc 500 ms
TICK_SEC      = 0.05         # pas de rafraîchissement (50 ms)

# ───────── STIMULI ───────────────────────────────────────────────────────────
stimuli = pd.DataFrame([
    # prime      cible        type            cond  cle  (1 = Mot, 2 = Non-mot)
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

# ───────── ÉTAT STREAMLIT ────────────────────────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)               # 0=instr, 1=tâche, 2=fin
    s.setdefault("trial", 0)              # index essai
    s.setdefault("phase", "fix")          # fix | blank | stim | fb
    s.setdefault("phase_start", time.perf_counter())
    s.setdefault("stim_start", 0.0)
    s.setdefault("results", [])
    s.setdefault("fb_msg", "")
    s.setdefault("fb_dur", 0.0)
init_state()

# ───────── OUTILS ────────────────────────────────────────────────────────────
def reset_phase(p):
    st.session_state.phase = p
    st.session_state.phase_start = time.perf_counter()

def tick(run=True):
    time.sleep(TICK_SEC)
    if run:
        st.rerun()

def log_trial(**kw):
    st.session_state.results.append(kw)

# ───────── PAGE 0 : INSTRUCTIONS ─────────────────────────────────────────────
def page_instructions():
    st.set_page_config(page_title="Décision lexicale", page_icon="🔠")
    st.title("Décision lexicale – entraînement")
    st.markdown("""
Cycle de chaque essai :

1. « + » 500 ms → 2. écran blanc 500 ms  
3. Deux mots : décidez si **le second est un mot français**  
 • bouton Mot (touche A) • bouton Non-mot (touche L)  
4. 2 s maximum pour répondre  
5. Si vous dépassez 2 s : *Trop lent* (1 500 ms) puis essai suivant.  

(10 essais au total, aucune indication de bonne/mauvaise réponse.)
""")
    if st.button("Commencer ➡️"):
        st.session_state.page = 1
        st.session_state.trial = 0
        reset_phase("fix")
        st.rerun()

# ───────── PAGE 1 : TÂCHE ────────────────────────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):                       # terminé
        st.session_state.page = 2
        st.rerun()
        return

    prime, cible, typ, cond, cle_corr = stimuli.iloc[i]
    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.phase_start

    # 1. FIXATION
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>",
                    unsafe_allow_html=True)
        if elapsed >= FIX_DUR:
            reset_phase("blank")
        tick()

    # 2. BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK_DUR:
            reset_phase("stim")
            st.session_state.stim_start = time.perf_counter()
        tick()

    # 3. STIMULI (décision)
    elif phase == "stim":
        st.markdown(
            f"<div style='text-align:center;font-size:42px;line-height:1.2'>"
            f"{prime}<br>{cible}</div>",
            unsafe_allow_html=True
        )
        col_mot, col_non = st.columns(2)
        clicked = None
        with col_mot:
            if st.button("Mot ✔️", key=f"mot_{i}"):
                clicked = 1
        with col_non:
            if st.button("Non-mot ❌", key=f"non_{i}"):
                clicked = 2

        rt = int((time.perf_counter() - st.session_state.stim_start) * 1000)

        # a) réponse dans les temps → essai suivant sans feedback
        if clicked is not None and rt <= TIME_LIMIT_MS:
            correct = clicked == cle_corr
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=clicked,
                      rt=rt, too_slow=False, correcte=correct)
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()

        # b) délai dépassé → feedback "Trop lent"
        elif rt > TIME_LIMIT_MS:
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=None,
                      rt=rt, too_slow=True, correcte=False)
            st.session_state.fb_msg = "Trop lent"
            st.session_state.fb_dur = 1.5
            reset_phase("fb")
            st.rerun()

        # c) attente continue
        tick()

    # 4. FEEDBACK « Trop lent »
    elif phase == "fb":
        st.markdown(
            f"<h2 style='text-align:center'>{st.session_state.fb_msg}</h2>",
            unsafe_allow_html=True
        )
        if elapsed >= st.session_state.fb_dur:
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()
        else:
            tick()

# ───────── PAGE 2 : FIN + CSV ────────────────────────────────────────────────
def page_end():
    st.title("Fin de l’entraînement – merci !")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df)
    csv_bytes = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Télécharger le CSV",
                       data=csv_bytes,
                       file_name=f"{uuid.uuid4()}_lexicale.csv",
                       mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE ───────────────────────────────────────────────────────────
if st.session_state.page == 0:
    page_instructions()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
