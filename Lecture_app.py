# -*- coding: utf-8 -*-
"""
Décision lexicale : présence d’un pseudo-mot ?
Essais aléatoires (5 à 9) – aucun mot ni pseudo-mot n’est répété
"""
import time, random, uuid, pandas as pd, streamlit as st

# ───────────  LISTES  ────────────────────────────────────────────────────────
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]

# ───────────  PARAMÈTRES TEMPS (s / ms)  ─────────────────────────────────────
FIX   = .5            # « + » 500 ms
BLANK = .5            # blanc 500 ms
LIM   = 2000          # délai max 2 000 ms
TICK  = .05           # refresh interne 50 ms

# ───────────  GÉNÉRATION DES ESSAIS (aucune répétition)  ────────────────────
def build_trials():
    """
    1. Tire aléatoirement un nombre r d’essais « mot + mot » (0 à 4).
       * r ∈ {0,1,2,3,4}
    2. Calcule m = 9 – 2r  →  nombre d’essais « mot + pseudo » (0 à 9).
    3. Construit la liste d’essais sans jamais réutiliser un item.
    """
    r = random.randint(0, 4)           # nb de paires 100 % mots
    m = 9 - 2 * r                      # nb de paires mixtes
    random.shuffle(WORDS)
    random.shuffle(PSEUDOS)

    trials = []

    # --- paires mot+mot (cle = 1)
    for k in range(r):
        a, b = WORDS[2*k], WORDS[2*k+1]
        trials.append(dict(w1=a, w2=b, has_pseudo=False, cle=1))

    # --- paires mot+pseudo (cle = 2)
    for k in range(m):
        w  = WORDS[2*r + k]            # mot encore inutilisé
        p  = PSEUDOS[k]                # pseudo-mot (unique)
        if random.random() < .5:
            w1, w2 = w, p
        else:
            w1, w2 = p, w
        trials.append(dict(w1=w1, w2=w2, has_pseudo=True, cle=2))

    random.shuffle(trials)
    return pd.DataFrame(trials)

# construit une seule fois
if "stimuli" not in st.session_state:
    st.session_state.stimuli = build_trials()

# ───────────  ÉTAT STREAMLIT  ────────────────────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)           # 0 intro • 1 task • 2 fin
    s.setdefault("trial", 0)
    s.setdefault("phase", "fix")      # fix | blank | stim | fb
    s.setdefault("t_phase", time.perf_counter())
    s.setdefault("t_stim",  0.0)
    s.setdefault("fb_left", 0.0)
    s.setdefault("log",     [])
init_state()

stimuli = st.session_state.stimuli    # raccourci

# ───────────  OUTILS  ────────────────────────────────────────────────────────
def reset_phase(p):
    st.session_state.phase  = p
    st.session_state.t_phase = time.perf_counter()

def tick():
    time.sleep(TICK)
    st.rerun()

def log(**k):
    st.session_state.log.append(k)

# ───────────  PAGE 0 : INSTRUCTIONS  ─────────────────────────────────────────
def page_intro():
    st.set_page_config(page_title="Décision lexicale", page_icon="🔡")
    st.title("Décision lexicale – pseudo-mot présent ?")
    st.markdown(f"""
Vous allez voir {len(stimuli)} paires de chaînes, sans aucune répétition.

1. « + » 500 ms → Blanc 500 ms  
2. Deux chaînes :  
   • « Seulement des mots » si **les deux** sont de vrais mots français  
   • « Pseudo-mot présent » s’il y a **au moins** un pseudo-mot  
3. 2 s pour répondre (sinon « Trop lent »)  

Aucune indication de bonne / mauvaise réponse n’est donnée.
""")
    if st.button("Commencer ➡️"):
        st.session_state.page = 1
        st.session_state.trial = 0
        reset_phase("fix")
        st.rerun()

# ───────────  PAGE 1 : BOUCLE TÂCHE  ─────────────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):           # → FIN
        st.session_state.page = 2
        st.rerun()
        return

    row = stimuli.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle
    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.t_phase

    # 1. FIXATION
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            reset_phase("blank")
        tick()

    # 2. BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            reset_phase("stim")
            st.session_state.t_stim = time.perf_counter()
        tick()

    # 3. STIMULI
    elif phase == "stim":
        st.markdown(
            f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
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
        if resp is not None and rt <= LIM:
            log(w1=w1, w2=w2, resp=resp, rt=rt,
                correcte=(resp==cle_corr), too_slow=False)
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()

        # b) délai dépassé
        elif rt > LIM:
            log(w1=w1, w2=w2, resp=None, rt=rt,
                correcte=False, too_slow=True)
            st.session_state.fb_left = 1.5
            reset_phase("fb")
            st.rerun()

        tick()

    # 4. FEEDBACK « Trop lent »
    elif phase == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>",
                    unsafe_allow_html=True)
        if elapsed >= st.session_state.fb_left:
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()
        else:
            tick()

# ───────────  PAGE 2 : FIN + CSV  ───────────────────────────────────────────
def page_end():
    st.title("Fin – merci de votre participation !")
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df)
    st.download_button(
        "📥 Télécharger les données (CSV)",
        data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────────  ROUTAGE  ───────────────────────────────────────────────────────
if st.session_state.page == 0:
    page_intro()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
