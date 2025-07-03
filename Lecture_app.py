# -*- coding: utf-8 -*-
"""
Décision lexicale : pseudo-mot présent ?   (9 essais, 18 mots uniques)
+ 500 ms  → blanc 500 ms → paire (≤ 2 s) → trop lent ? (1 500 ms) → essai suivant
Aucune indication correct / incorrect.
CSV final téléchargeable.
"""
import time, random, uuid, pandas as pd, streamlit as st

# ───────── LISTES ────────────────────────────────────────────────────────────
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]

# ───────── PARAMÈTRES TEMPS ─────────────────────────────────────────────────
FIX_DUR  = .5          # « + »      500 ms
BLANK_DUR= .5          # blanc      500 ms
TIMEOUT  = 2000        # limite     2 000 ms
TICK     = .05         # rafraîch.   50 ms

# ───────── CONSTRUCTION DES 9 ESSAIS (0 répétition) ─────────────────────────
def build_trials():
    """Retourne un DataFrame de 9 essais sans répétition d’aucun mot."""
    random.shuffle(PSEUDOS)
    random.shuffle(WORDS)
    trials = []
    for pseudo, word in zip(PSEUDOS, WORDS):
        # Orientation aléatoire : pseudo-mot 1er OU 2ᵉ
        if random.random() < .5:
            w1, w2 = pseudo, word
        else:
            w1, w2 = word, pseudo
        trials.append(dict(w1=w1, w2=w2, has_pseudo=True, cle=2))
    # Mélange final des essais
    random.shuffle(trials)
    return pd.DataFrame(trials)

if "stimuli" not in st.session_state:
    st.session_state.stimuli = build_trials()

# ───────── INITIALISATION ÉTAT ──────────────────────────────────────────────
def init():
    s = st.session_state
    s.setdefault("page", 0)            # 0 = instr / 1 = tâche / 2 = fin
    s.setdefault("trial", 0)
    s.setdefault("phase", "fix")       # fix | blank | stim | fb
    s.setdefault("phase_t0", time.perf_counter())
    s.setdefault("stim_t0",  0.0)
    s.setdefault("fb_left",  0.0)
    s.setdefault("logs",     [])
init()

stimuli = st.session_state.stimuli     # raccourci

# ───────── OUTILS ───────────────────────────────────────────────────────────
def reset_phase(p):
    st.session_state.phase   = p
    st.session_state.phase_t0= time.perf_counter()

def tick():
    time.sleep(TICK)
    st.rerun()

def log(**kwargs):
    st.session_state.logs.append(kwargs)

# ───────── PAGE 0 : INSTRUCTIONS ─────────────────────────────────────────────
def page_intro():
    st.set_page_config(page_title="Décision lexicale", page_icon="🔤")
    st.title("Décision lexicale – pseudo-mot présent ?")
    st.markdown("""
1. « + » 500 ms → 2. écran blanc 500 ms  
3. Deux chaînes s’affichent :  
   • cliquez **Seulement des mots** si les deux sont de vrais mots français  
   • cliquez **Pseudo-mot présent** s’il y en a au moins un faux  
4. Vous disposez de **2 s**.  
5. Si vous n’avez pas répondu à temps, « Trop lent » apparaît 1 500 ms.  

Chaque chaîne n’apparaît qu’une seule fois.  
""")
    if st.button("Commencer ➡️"):
        st.session_state.page  = 1
        st.session_state.trial = 0
        reset_phase("fix")
        st.rerun()

# ───────── PAGE 1 : BOUCLE TÂCHE ─────────────────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):          # terminé
        st.session_state.page = 2
        st.rerun()
        return

    row = stimuli.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle
    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.phase_t0

    # 1. FIX
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX_DUR:
            reset_phase("blank")
        tick()

    # 2. BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK_DUR:
            reset_phase("stim")
            st.session_state.stim_t0 = time.perf_counter()
        tick()

    # 3. STIM
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

        rt = int((time.perf_counter() - st.session_state.stim_t0)*1000)

        # a) réponse en temps
        if resp is not None and rt <= TIMEOUT:
            log(w1=w1, w2=w2, resp=resp, rt=rt,
                correcte=(resp==cle_corr), too_slow=False)
            st.session_state.trial += 1
            reset_phase("fix")
            st.rerun()

        # b) délai dépassé
        elif rt > TIMEOUT:
            log(w1=w1, w2=w2, resp=None, rt=rt,
                correcte=False, too_slow=True)
            st.session_state.fb_left = 1.5
            reset_phase("fb")
            st.rerun()

        # c) sinon on continue
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

# ───────── PAGE 2 : FIN + CSV ───────────────────────────────────────────────
def page_end():
    st.title("Fin – merci !")
    df = pd.DataFrame(st.session_state.logs)
    st.dataframe(df)
    st.download_button(
        "📥 Télécharger le CSV",
        data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv",
        mime="text/csv"
    )
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE ──────────────────────────────────────────────────────────
if st.session_state.page == 0:
    page_intro()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
