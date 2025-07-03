# -*- coding: utf-8 -*-
"""
EXPÉRIMENTATION STREAMLIT
Partie 1 : Détection de pseudo-mot (5-9 essais, 2 s maxi)
Partie 2 : Vocabulaire – fréquence subjective (7 essais, sans limite de temps)
chronologie P2 : + 500 ms → blanc 500 ms → mot (affiché jusqu’à réponse)
                 → blanc 1500 ms → essai suivant
"""
import time, random, uuid, pandas as pd, streamlit as st

# ────────── LISTES DE STIMULI ────────────────────────────────────────────────
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]

VOCAB_WORDS = [
    "merise", "roseau", "viaduc", "anode", "appeau", "miroir", "cornac"
]

# ────────── PARAMÈTRES TEMPORELS ─────────────────────────────────────────────
FIX      = .5        # « + »   500 ms
BLANK    = .5        # blanc   500 ms
LIM_MS   = 2000      # délai max pour la partie 1
ISI_VOC  = 1.5       # inter-stimulus de la partie 2
TICK     = .05       # rafraîchissement boucle (50 ms)

# ────────── CONSTRUCTION DES ESSAIS PARTIE 1 ────────────────────────────────
def build_trials():
    """
    r paires mot+mot (r tiré 0-4)
    m = 9-2r paires mot+pseudo  (jamais pseudo+pseudo)
    aucun item réutilisé
    """
    r = random.randint(0, 4)
    m = 9 - 2 * r
    random.shuffle(WORDS)
    random.shuffle(PSEUDOS)
    trials = []

    # mot + mot  (clé correcte = 1)
    for k in range(r):
        a, b = WORDS[2*k], WORDS[2*k+1]
        trials.append(dict(w1=a, w2=b, cle=1))

    # mot + pseudo (clé correcte = 2)
    for k in range(m):
        w  = WORDS[2*r + k]
        p  = PSEUDOS[k]
        w1, w2 = (w, p) if random.random() < .5 else (p, w)
        trials.append(dict(w1=w1, w2=w2, cle=2))

    random.shuffle(trials)
    return pd.DataFrame(trials)

# ────────── INITIALISATION ÉTAT GLOBAL ───────────────────────────────────────
def init_state():
    s = st.session_state
    # routage général
    s.setdefault("page", 0)            # 0 intro 1 tâche 1  |  2 intro 2  |
                                       # 3 tâche 2 | 4 fin
    # PARTIE 1
    if "stim_lex" not in s:
        s.stim_lex = build_trials()
    s.setdefault("lex_trial", 0)
    s.setdefault("lex_phase", "fix")   # fix blank stim fb
    s.setdefault("lex_t0", time.perf_counter())
    s.setdefault("lex_t_stim", 0.0)
    s.setdefault("lex_fb_left", 0.0)
    s.setdefault("lex_log", [])

    # PARTIE 2
    if "stim_vocab" not in s:
        tmp = VOCAB_WORDS.copy()
        random.shuffle(tmp)
        s.stim_vocab = tmp             # simple liste mélangée
    s.setdefault("voc_trial", 0)
    s.setdefault("voc_phase", "fix")   # fix blank word isi
    s.setdefault("voc_t0", time.perf_counter())
    s.setdefault("voc_t_word", 0.0)
    s.setdefault("voc_log", [])

init_state()

# ────────── OUTILS GÉNÉRIQUES ───────────────────────────────────────────────
def tick():
    time.sleep(TICK)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#                           PARTIE 1  –  pseudo-mots
# ─────────────────────────────────────────────────────────────────────────────
def page_intro_lex():
    st.title("Partie 1 – Détection de pseudo-mot")
    st.markdown(f"""
Vous allez voir {len(st.session_state.stim_lex)} paires de chaînes (aucune
répétition) :

• « Seulement des mots » si **les deux** sont de vrais mots français  
• « Pseudo-mot présent » s’il y en a au moins un faux  

Vous disposez de 2 s. Au-delà : message *Trop lent* (1 500 ms).
""")
    if st.button("Commencer la partie 1 ➡️"):
        st.session_state.page = 1
        st.session_state.lex_trial = 0
        st.session_state.lex_phase = "fix"
        st.session_state.lex_t0 = time.perf_counter()
        st.rerun()

def page_task_lex():
    i = st.session_state.lex_trial
    stim_df = st.session_state.stim_lex
    if i >= len(stim_df):                       # partie terminée
        st.session_state.page = 2
        st.rerun()
        return

    row = stim_df.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle
    phase   = st.session_state.lex_phase
    elapsed = time.perf_counter() - st.session_state.lex_t0

    # ------ phase FIX ------
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.lex_phase = "blank"
            st.session_state.lex_t0 = time.perf_counter()
        tick()

    # ------ phase BLANK ------
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.lex_phase = "stim"
            st.session_state.lex_t_stim = time.perf_counter()
            st.session_state.lex_t0 = time.perf_counter()
        tick()

    # ------ phase STIM ------
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

        rt = int((time.perf_counter() - st.session_state.lex_t_stim)*1000)

        # réponse dans le temps
        if resp is not None and rt <= LIM_MS:
            score = 1 if resp == cle_corr else 0
            st.session_state.lex_log.append(
                dict(pair=i+1, w1=w1, w2=w2, resp=resp,
                     rt=rt, score=score, too_slow=0))
            st.session_state.lex_trial += 1
            st.session_state.lex_phase = "fix"
            st.session_state.lex_t0 = time.perf_counter()
            st.rerun()

        # délai dépassé
        elif rt > LIM_MS:
            st.session_state.lex_log.append(
                dict(pair=i+1, w1=w1, w2=w2, resp=None,
                     rt=rt, score=0, too_slow=1))
            st.session_state.lex_fb_left = 1.5
            st.session_state.lex_phase = "fb"
            st.session_state.lex_t0 = time.perf_counter()
            st.rerun()

        tick()

    # ------ phase FEEDBACK « Trop lent » ------
    elif phase == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>",
                    unsafe_allow_html=True)
        if elapsed >= st.session_state.lex_fb_left:
            st.session_state.lex_trial += 1
            st.session_state.lex_phase = "fix"
            st.session_state.lex_t0 = time.perf_counter()
            st.rerun()
        else:
            tick()

# ─────────────────────────────────────────────────────────────────────────────
#                           PARTIE 2  –  Vocabulaire
# ─────────────────────────────────────────────────────────────────────────────
def page_intro_vocab():
    st.title("Partie 2 – Vocabulaire")
    st.markdown("""
Pour chaque mot affiché :

1. « + » 500 ms → blanc 500 ms  
2. Le **mot** apparaît (Times New Roman 42, minuscules)  
3. Indiquez à quelle fréquence vous le rencontrez à l’écrit :  
   1 = jamais … 7 = plusieurs fois par jour  

Les mots restent affichés jusqu’à votre réponse.  
Appuyez sur un des 7 boutons (ou touches 1-7 si votre navigateur les prend en charge).
""")
    if st.button("Commencer la partie 2 ➡️"):
        st.session_state.page = 3
        st.session_state.voc_trial = 0
        st.session_state.voc_phase = "fix"
        st.session_state.voc_t0 = time.perf_counter()
        st.rerun()

def page_task_vocab():
    j = st.session_state.voc_trial
    words = st.session_state.stim_vocab
    if j >= len(words):                          # partie terminée
        st.session_state.page = 4
        st.rerun()
        return

    word = words[j]
    phase   = st.session_state.voc_phase
    elapsed = time.perf_counter() - st.session_state.voc_t0

    # -- FIX
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.voc_phase = "blank"
            st.session_state.voc_t0 = time.perf_counter()
        tick()

    # -- BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.voc_phase = "word"
            st.session_state.voc_t_word = time.perf_counter()
            st.session_state.voc_t0 = time.perf_counter()
        tick()

    # -- WORD (échelle 1-7)
    elif phase == "word":
        st.markdown(
            f"<div style='text-align:center;font-family:Times New Roman;"
            f"font-size:42px;line-height:1.2'>{word}</div>",
            unsafe_allow_html=True)

        col = st.columns(7)
        resp = None
        for idx in range(7):
            with col[idx]:
                if st.button(str(idx+1), key=f"rate_{j}_{idx}"):
                    resp = idx + 1

        if resp is not None:
            rt = int((time.perf_counter() - st.session_state.voc_t_word)*1000)
            st.session_state.voc_log.append(
                dict(order=j+1, word=word, rating=resp, rt=rt))
            st.session_state.voc_phase = "isi"
            st.session_state.voc_t0 = time.perf_counter()
            st.rerun()
        else:
            tick()

    # -- ISI (blanc 1 500 ms)
    elif phase == "isi":
        st.empty()
        if elapsed >= ISI_VOC:
            st.session_state.voc_trial += 1
            st.session_state.voc_phase = "fix"
            st.session_state.voc_t0 = time.perf_counter()
            st.rerun()
        else:
            tick()

# ─────────────────────────────────────────────────────────────────────────────
#                               PAGE 4  FIN
# ─────────────────────────────────────────────────────────────────────────────
def page_fin():
    st.title("Merci pour votre participation !")

    # CSV pseudo-mots
    df_lex = pd.DataFrame(st.session_state.lex_log)
    st.subheader("Résultats partie 1")
    st.dataframe(df_lex)
    st.download_button(
        "📥 Télécharger partie 1 (CSV)",
        data=df_lex.to_csv(index=False, sep=';', encoding='utf-8-sig')
                     .encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv",
        mime="text/csv")

    # CSV vocabulaire
    df_vocab = pd.DataFrame(st.session_state.voc_log)
    st.subheader("Résultats partie 2")
    st.dataframe(df_vocab)
    st.download_button(
        "📥 Télécharger partie 2 (CSV)",
        data=df_vocab.to_csv(index=False, sep=';', encoding='utf-8-sig')
                      .encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_vocab.csv",
        mime="text/csv")

    st.success("Fichiers prêts – vous pouvez fermer l’onglet.")

# ───────────────────────── ROUTAGE GLOBAL ────────────────────────────────────
pg = st.session_state.page
if pg == 0:
    page_intro_lex()
elif pg == 1:
    page_task_lex()
elif pg == 2:
    page_intro_vocab()
elif pg == 3:
    page_task_vocab()
else:
    page_fin()
