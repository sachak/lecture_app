# -*- coding: utf-8 -*-
"""
Décision lexicale : détecter la présence d’un pseudo-mot
18 essais : 9 « pseudo-mot présent », 9 « aucun pseudo-mot »
Aucune dépendance externe – Streamlit ≥ 1.33
"""
import time, uuid, random, pandas as pd, streamlit as st

# ───────── LISTES DE MOTS ────────────────────────────────────────────────────
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]

# ───────── PARAMÈTRES TEMPORELS (s / ms) ─────────────────────────────────────
TIME_LIMIT_MS = 2000
FIX_DUR       = 0.5
BLANK_DUR     = 0.5
TICK_SEC      = 0.05            # rafraîchissement interne (50 ms)

# ───────── GÉNÉRATION DES 18 ESSAIS ──────────────────────────────────────────
def build_trials():
    trials = []

    # 1) 9 essais avec pseudo-mot
    for pseudo in PSEUDOS:
        word = random.choice(WORDS)
        if random.random() < .5:
            w1, w2 = pseudo, word
        else:
            w1, w2 = word, pseudo
        trials.append(dict(w1=w1, w2=w2, has_pseudo=True, cle=2))

    # 2) 9 essais « aucun pseudo-mot »
    for _ in range(9):
        w1, w2 = random.sample(WORDS, 2)
        trials.append(dict(w1=w1, w2=w2, has_pseudo=False, cle=1))

    random.shuffle(trials)
    return pd.DataFrame(trials)

# construit une fois au premier run
if "stimuli" not in st.session_state:
    st.session_state.stimuli = build_trials()

# ───────── INITIALISATION ÉTAT STREAMLIT ─────────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)             # 0=instr  1=tâche  2=fin
    s.setdefault("trial", 0)
    s.setdefault("phase", "fix")        # fix | blank | stim | fb
    s.setdefault("phase_start", time.perf_counter())
    s.setdefault("stim_start", 0.0)
    s.setdefault("results", [])
    s.setdefault("fb_timer", 0.0)       # pour « Trop lent »
init_state()

stimuli = st.session_state.stimuli     # raccourci

# ───────── OUTILS GÉNÉRIQUES ────────────────────────────────────────────────
def reset_phase(p):
    st.session_state.phase = p
    st.session_state.phase_start = time.perf_counter()

def tick(rerun=True):
    time.sleep(TICK_SEC)
    if rerun:
        st.rerun()

def log_trial(**kw):
    st.session_state.results.append(kw)

# ───────── PAGE 0 : INSTRUCTIONS ─────────────────────────────────────────────
def page_instructions():
    st.set_page_config(page_title="Décision lexicale", page_icon="🔡")
    st.title("Décision lexicale")
    st.markdown("""
Sur chaque essai :

1. « + » 500 ms → 2. écran blanc 500 ms  
3. Deux mots : indiquez s’il existe **au moins un pseudo-mot**  
   • bouton « Seulement des mots » (touche A)  
   • bouton « Pseudo-mot présent » (touche L)  
4. 2 s pour répondre  
5. Si vous êtes trop lent, l’avertissement *Trop lent* s’affiche 1 500 ms.  

Aucune information sur l’exactitude n’est donnée.  
Appuyez sur le bouton pour commencer (18 essais).
""")
    if st.button("Commencer ➡️"):
        st.session_state.page = 1
        st.session_state.trial = 0
        reset_phase("fix")
        st.rerun()

# ───────── PAGE 1 : BOUCLE TÂCHE ─────────────────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):             # tous les essais terminés
        st.session_state.page = 2
        st.rerun()
        return

    row = stimuli.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle

    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.phase_start

    # 1) FIXATION
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>",
                    unsafe_allow_html=True)
        if elapsed >= FIX_DUR:
            reset_phase("blank")
        tick()

    # 2) BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK_DUR:
            reset_phase("stim")
            st.session_state.stim_start = time.perf_counter()
        tick()

    # 3) STIMULI
    elif phase == "stim":
        st.markdown(
            f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
            f"{w1}<br>{w2}</div>", unsafe_allow_html=True
        )

        col_ok, col_pseudo = st.columns(2)
        clicked = None
        with col_ok:
            if st.button("Seulement des mots ✔️", key=f"ok_{i}"):
                clicked = 1
        with col_pseudo:
            if st.button("Pseudo-mot présent ❌", key=f"pseudo_{i}"):
                clicked = 2

        rt = int((time.perf_counter() - st.session_state.stim_start) * 1000)

        # a) réponse dans le temps
        if clicked is not None and rt <= TIME_LIMIT_MS:
            correct = clicked == cle_corr
            log_trial(w1=w1, w2=w2, has_pseudo=row.has_pseudo,
                      reponse=clicked, rt=rt,
                      correcte=correct, too_slow=False)
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()

        # b) délai dépassé
        elif rt > TIME_LIMIT_MS:
            log_trial(w1=w1, w2=w2, has_pseudo=row.has_pseudo,
                      reponse=None, rt=rt,
                      correcte=False, too_slow=True)
            st.session_state.fb_timer = 1.5
            reset_phase("fb")
            st.rerun()

        # c) attente continue
        tick()

    # 4) FEEDBACK « Trop lent »
    elif phase == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>",
                    unsafe_allow_html=True)
        if elapsed >= st.session_state.fb_timer:
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()
        else:
            tick()

# ───────── PAGE 2 : FIN + CSV ────────────────────────────────────────────────
def page_end():
    st.title("Fin – merci pour votre participation !")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df)
    name = f"{uuid.uuid4()}_lexicale.csv"
    st.download_button("📥 Télécharger le CSV",
                       data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
                       file_name=name, mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE ───────────────────────────────────────────────────────────
if st.session_state.page == 0:
    page_instructions()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
