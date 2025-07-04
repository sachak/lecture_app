# -*- coding: utf-8 -*-
"""
EXPÉRIMENTATION STREAMLIT ― VERSION « PLEIN-ÉCRAN »

Partie 1 : Détection de pseudo-mot    (5-9 essais, 2 s maxi)  
Partie 2 : Vocabulaire – fréquence    (7 mots, échelle 1-7)

• L’interface Streamlit (menu, barre d’en-tête, footer, sidebar) est masquée.  
• Le navigateur passe en plein-écran dès le clic sur « Commencer la partie 1 ».  
• Deux fichiers CSV (UTF-8-SIG) sont proposés à la fin.
"""
import time, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components     # ← pour le JavaScript plein-écran

# ───────── Configuration globale & habillage ─────────────────────────────────
st.set_page_config(page_title="Expérience", page_icon="🔡", layout="wide")

# Masquage complet de l’UI Streamlit
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header    {visibility: hidden;}
    footer    {visibility: hidden;}
    div[data-testid="stSidebar"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

def go_fullscreen() -> None:
    """Demande au navigateur de passer en mode plein-écran."""
    components.html(
        """
        <script>
        var doc = window.parent.document.documentElement;
        if      (doc.requestFullscreen)       {doc.requestFullscreen();}
        else if (doc.mozRequestFullScreen)    {doc.mozRequestFullScreen();}
        else if (doc.webkitRequestFullscreen) {doc.webkitRequestFullscreen();}
        else if (doc.msRequestFullscreen)     {doc.msRequestFullscreen();}
        </script>
        """,
        height=0, width=0
    )

# ───────── Données expérimentales ───────────────────────────────────────────
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]
VOCAB_WORDS = ["merise", "roseau", "viaduc", "anode", "appeau", "miroir", "cornac"]

LABELS_1_7 = {
    1: "Jamais",
    2: "1×/an",
    3: "1×/mois",
    4: "1×/semaine",
    5: "Tous les 2 j",
    6: "1×/jour",
    7: "Plusieurs ×/jour",
}

# ───────── Paramètres temps (s / ms) ─────────────────────────────────────────
FIX, BLANK = .5, .5       # croix + écran blanc
LIM_MS     = 2000         # limite de réponse (pseudo-mots) en ms
ISI_VOC    = 1.5          # inter-stimulus vocabulaire
TICK       = .05          # rafraîchissement « quasi temps réel »

# ───────── Construction des essais (partie 1) ───────────────────────────────
def build_trials() -> pd.DataFrame:
    r = random.randint(0, 4)           # paires mot+mot
    m = 9 - 2 * r                      # paires mot+pseudo
    random.shuffle(WORDS)
    random.shuffle(PSEUDOS)
    trials = []

    for k in range(r):                 # mot + mot
        a, b = WORDS[2*k], WORDS[2*k+1]
        trials.append(dict(w1=a, w2=b, cle=1))
    for k in range(m):                 # mot + pseudo
        w, p = WORDS[2*r + k], PSEUDOS[k]
        w1, w2 = (w, p) if random.random() < .5 else (p, w)
        trials.append(dict(w1=w1, w2=w2, cle=2))

    random.shuffle(trials)
    return pd.DataFrame(trials)

# ───────── Initialisation de l’état Streamlit ───────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)

    # Partie 1
    if "stim_lex" not in s:
        s.stim_lex = build_trials()
    s.setdefault("lex_trial", 0)
    s.setdefault("lex_phase", "fix")
    s.setdefault("lex_t0", time.perf_counter())
    s.setdefault("lex_t_stim", 0.0)
    s.setdefault("lex_fb_left", 0.0)
    s.setdefault("lex_log", [])

    # Partie 2
    if "stim_vocab" not in s:
        tmp = VOCAB_WORDS.copy(); random.shuffle(tmp)
        s.stim_vocab = tmp
    s.setdefault("voc_trial", 0)
    s.setdefault("voc_phase", "fix")
    s.setdefault("voc_t0", time.perf_counter())
    s.setdefault("voc_t_word", 0.0)
    s.setdefault("voc_log", [])

init_state()

# ───────── Petit « tick » pour la boucle pseudo temps réel ──────────────────
def tick():
    time.sleep(TICK)
    st.rerun()

# ═══════════════════════════  PARTIE 1 – INTRO  ═════════════════════════════
def page_intro_lex():
    st.title("Partie 1 – Détection de pseudo-mot")
    st.markdown(f"""
Vous allez voir **{len(st.session_state.stim_lex)}** paires :

• **Seulement des mots** : 2 vrais mots français  
• **Pseudo-mot présent** : ≥ 1 pseudo-mot  

Vous avez 2 s pour répondre ; sinon « Trop lent ».
""")
    if st.button("Commencer la partie 1 ➡️"):
        go_fullscreen()                       # ← on bascule en plein-écran
        st.session_state.page = 1
        st.session_state.lex_trial = 0
        st.session_state.lex_phase = "fix"
        st.session_state.lex_t0    = time.perf_counter()
        st.rerun()

# ═══════════════════════════  PARTIE 1 – TÂCHE  ═════════════════════════════
def page_task_lex():
    i  = st.session_state.lex_trial
    df = st.session_state.stim_lex
    if i >= len(df):
        st.session_state.page = 2; st.rerun(); return

    row     = df.iloc[i]
    w1, w2  = row.w1, row.w2
    cle     = row.cle
    ph      = st.session_state.lex_phase
    t0      = st.session_state.lex_t0
    elapsed = time.perf_counter() - t0

    if ph == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.lex_phase, st.session_state.lex_t0 = "blank", time.perf_counter()
        tick()

    elif ph == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.lex_phase, st.session_state.lex_t0 = "stim", time.perf_counter()
            st.session_state.lex_t_stim = time.perf_counter()
        tick()

    elif ph == "stim":
        st.markdown(
            f"<div style='text-align:center;font-size:40px;line-height:1.2'>"
            f"{w1}<br>{w2}</div>",
            unsafe_allow_html=True
        )

        col_ok, col_ps = st.columns(2)
        resp = None
        with col_ok:
            if st.button("Seulement des mots ✔️", key=f"ok_{i}"):
                resp = 1
        with col_ps:
            if st.button("Pseudo-mot présent ❌", key=f"ps_{i}"):
                resp = 2

        rt = int((time.perf_counter() - st.session_state.lex_t_stim) * 1000)

        if resp is not None and rt <= LIM_MS:
            score = 1 if resp == cle else 0
            st.session_state.lex_log.append(
                dict(trial=i+1, w1=w1, w2=w2, resp=resp,
                     rt=rt, score=score, too_slow=0)
            )
            st.session_state.lex_trial += 1
            st.session_state.lex_phase, st.session_state.lex_t0 = "fix", time.perf_counter()
            st.rerun()

        elif rt > LIM_MS:
            st.session_state.lex_log.append(
                dict(trial=i+1, w1=w1, w2=w2, resp=None,
                     rt=rt, score=0, too_slow=1)
            )
            st.session_state.lex_fb_left = 1.5
            st.session_state.lex_phase, st.session_state.lex_t0 = "fb", time.perf_counter()
            st.rerun()

        tick()

    elif ph == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>", unsafe_allow_html=True)
        if elapsed >= st.session_state.lex_fb_left:
            st.session_state.lex_trial += 1
            st.session_state.lex_phase, st.session_state.lex_t0 = "fix", time.perf_counter()
            st.rerun()
        else:
            tick()

# ═══════════════════════════  PARTIE 2 – INTRO  ═════════════════════════════
def page_intro_vocab():
    st.title("Partie 2 – Vocabulaire : fréquence d’exposition à l’écrit")
    st.write("Choisissez pour chaque mot la fréquence à laquelle "
             "vous le rencontrez **à l’écrit** :")
    st.markdown("""
| Bouton | Signification |
|:---:|---|
| **1** | Jamais |
| **2** | 1 fois / an |
| **3** | 1 fois / mois |
| **4** | 1 fois / semaine |
| **5** | Tous les 2 jours |
| **6** | 1 fois / jour |
| **7** | Plusieurs fois / jour |
""")
    if st.button("Commencer la partie 2 ➡️"):
        st.session_state.page      = 3
        st.session_state.voc_trial = 0
        st.session_state.voc_phase = "fix"
        st.session_state.voc_t0    = time.perf_counter()
        st.rerun()

# ═══════════════════════════  PARTIE 2 – TÂCHE  ═════════════════════════════
def page_task_vocab():
    j   = st.session_state.voc_trial
    lst = st.session_state.stim_vocab
    if j >= len(lst):
        st.session_state.page = 4; st.rerun(); return

    word    = lst[j]
    phase   = st.session_state.voc_phase
    elapsed = time.perf_counter() - st.session_state.voc_t0

    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.voc_phase, st.session_state.voc_t0 = "blank", time.perf_counter()
        tick()

    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.voc_phase   = "word"
            st.session_state.voc_t_word  = time.perf_counter()
            st.session_state.voc_t0      = time.perf_counter()
        tick()

    elif phase == "word":
        st.markdown(
            f"<div style='text-align:center;font-family:Times New Roman;"
            f"font-size:42px;'>{word}</div>",
            unsafe_allow_html=True
        )

        cols = st.columns(7)
        resp = None
        for idx in range(7):
            num = idx + 1
            with cols[idx]:
                if st.button(str(num), key=f"rate_{j}_{num}"):
                    resp = num
                st.markdown(
                    f"<div style='font-size:12px;text-align:center'>"
                    f"{LABELS_1_7[num]}</div>",
                    unsafe_allow_html=True
                )

        if resp is not None:
            rt = int((time.perf_counter() - st.session_state.voc_t_word) * 1000)
            st.session_state.voc_log.append(
                dict(order=j+1, word=word, rating=resp, rt=rt)
            )
            st.session_state.voc_phase, st.session_state.voc_t0 = "isi", time.perf_counter()
            st.rerun()
        else:
            tick()

    elif phase == "isi":
        st.empty()
        if elapsed >= ISI_VOC:
            st.session_state.voc_trial += 1
            st.session_state.voc_phase, st.session_state.voc_t0 = "fix", time.perf_counter()
            st.rerun()
        else:
            tick()

# ═══════════════════════════  FIN & EXPORT  ════════════════════════════════
def page_fin():
    st.title("Merci pour votre participation !")

    df1 = pd.DataFrame(st.session_state.lex_log)
    st.subheader("Partie 1 – Pseudo-mots")
    st.dataframe(df1)
    st.download_button(
        "📥 Télécharger partie 1 (CSV)",
        data=df1.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv",
        mime="text/csv"
    )

    df2 = pd.DataFrame(st.session_state.voc_log)
    st.subheader("Partie 2 – Vocabulaire")
    st.dataframe(df2)
    st.download_button(
        "📥 Télécharger partie 2 (CSV)",
        data=df2.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_vocab.csv",
        mime="text/csv"
    )

    st.success("Fichiers prêts – vous pouvez fermer l’onglet.")

# ───────── Routage global ────────────────────────────────────────────────────
pg = st.session_state.page
if   pg == 0: page_intro_lex()
elif pg == 1: page_task_lex()
elif pg == 2: page_intro_vocab()
elif pg == 3: page_task_vocab()
else:          page_fin()
