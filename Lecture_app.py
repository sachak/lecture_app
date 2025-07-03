# -*- coding: utf-8 -*-
"""
Décision lexicale – pseudo-mot présent ?
Nombre d’essais aléatoire (5 à 9) – aucun item réutilisé
CSV : score = 1 (bonne + rapide) ; 0 (mauvaise OU trop lent)
"""
import time, random, uuid, pandas as pd, streamlit as st

# ------------------- LISTES DE STIMULI --------------------------------------
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]

# ------------------- PARAMÈTRES TEMPORELS -----------------------------------
FIX, BLANK = .5, .5          # « + » 500 ms ; blanc 500 ms
LIM_MS     = 2000            # délai maxi 2 s
TICK       = .05             # rafraîchissement interne 50 ms

# ------------------- GÉNÉRATION DES ESSAIS (aucune répétition) --------------
def build_trials():
    """
    r paires « mot+mot » (r tiré 0-4)
    m = 9-2r paires « mot+pseudo »
    jamais « pseudo+pseudo » ; aucun item réutilisé
    """
    r = random.randint(0, 4)          # 0…4
    m = 9 - 2 * r                     # 5…9-2r
    random.shuffle(WORDS)
    random.shuffle(PSEUDOS)

    trials = []

    # – mots + mots (score correct attendu = 1 → bouton « Seulement des mots »)
    for k in range(r):
        a, b = WORDS[2*k], WORDS[2*k+1]
        trials.append(dict(w1=a, w2=b, cle=1))   # cle = bonne réponse

    # – mot + pseudo (score correct attendu = 1 → bouton « Pseudo-mot présent »)
    for k in range(m):
        w  = WORDS[2*r + k]
        p  = PSEUDOS[k]
        w1, w2 = (w, p) if random.random() < .5 else (p, w)
        trials.append(dict(w1=w1, w2=w2, cle=2))

    random.shuffle(trials)
    return pd.DataFrame(trials)

if "stimuli" not in st.session_state:
    st.session_state.stimuli = build_trials()

# ------------------- ÉTAT STREAMLIT -----------------------------------------
def init_state():
    s = st.session_state
    s.setdefault("page",   0)          # 0 intro | 1 tâche | 2 fin
    s.setdefault("trial",  0)
    s.setdefault("phase",  "fix")      # fix | blank | stim | fb
    s.setdefault("t0",     time.perf_counter())
    s.setdefault("t_stim", 0.0)
    s.setdefault("fb_left",0.0)
    s.setdefault("log",    [])
init_state()

stimuli = st.session_state.stimuli

# ------------------- OUTILS --------------------------------------------------
def reset(phase):               # change de phase
    st.session_state.phase = phase
    st.session_state.t0    = time.perf_counter()

def tick():                     # boucle temps réel
    time.sleep(TICK)
    st.rerun()

def add_log(**k):               # enregistre un essai
    st.session_state.log.append(k)

# ------------------- PAGE 0 : INTRO -----------------------------------------
def page_intro():
    st.set_page_config(page_title="Décision lexicale", page_icon="🔡")
    st.title("Décision lexicale – pseudo-mot présent ?")
    st.markdown(f"""
Vous allez voir {len(stimuli)} paires ; aucun mot n’est présenté deux fois.

Boutons :
• **Seulement des mots** → si les 2 chaînes sont de vrais mots français  
• **Pseudo-mot présent** → s’il y en a au moins un faux mot  

2 s pour répondre, sinon « Trop lent » apparaît brièvement.
""")
    if st.button("Commencer ➡️"):
        st.session_state.page, st.session_state.trial = 1, 0
        reset("fix")
        st.rerun()

# ------------------- PAGE 1 : TÂCHE -----------------------------------------
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):               # terminé
        st.session_state.page = 2
        st.rerun()
        return

    row = stimuli.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle
    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.t0

    # 1) FIXATION « + »
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            reset("blank")
        tick()

    # 2) BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            reset("stim")
            st.session_state.t_stim = time.perf_counter()
        tick()

    # 3) STIMULI
    elif phase == "stim":
        st.markdown(f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
                    f"{w1}<br>{w2}</div>", unsafe_allow_html=True)
        col_ok, col_pseudo = st.columns(2)
        resp = None
        with col_ok:
            if st.button("Seulement des mots ✔️", key=f"ok_{i}"):
                resp = 1
        with col_pseudo:
            if st.button("Pseudo-mot présent ❌", key=f"pseudo_{i}"):
                resp = 2

        rt = int((time.perf_counter() - st.session_state.t_stim)*1000)

        # a) réponse dans les temps
        if resp is not None and rt <= LIM_MS:
            score = 1 if resp == cle_corr else 0
            add_log(w1=w1, w2=w2, resp=resp, rt=rt, score=score, too_slow=0)
            st.session_state.trial += 1
            reset("fix")
            st.rerun()

        # b) délai dépassé -> score 0
        elif rt > LIM_MS:
            add_log(w1=w1, w2=w2, resp=None, rt=rt, score=0, too_slow=1)
            st.session_state.fb_left = 1.5
            reset("fb")
            st.rerun()

        tick()

    # 4) FEEDBACK « Trop lent »
    elif phase == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>", unsafe_allow_html=True)
        if elapsed >= st.session_state.fb_left:
            st.session_state.trial += 1
            reset("fix")
            st.rerun()
        else:
            tick()

# ------------------- PAGE 2 : FIN + CSV -------------------------------------
def page_end():
    st.title("Fin – merci !")
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df)
    st.download_button(
        "📥 Télécharger (CSV)",
        data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ------------------- ROUTAGE -------------------------------------------------
if st.session_state.page == 0:
    page_intro()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
