# -*- coding: utf-8 -*-
"""
EXPÉRIMENTATION STREAMLIT  (≥ 1.33 – aucune dépendance externe)

Partie 1 : Détection de pseudo-mot
  • 5 à 9 essais chronométrés (2 s max)
  • jamais pseudo + pseudo, aucun item réutilisé
  • score = 1 si bonne réponse ≤ 2 000 ms, sinon 0

Partie 2 : Vocabulaire – fréquence subjective
  • 7 mots, ordre aléatoire, affichés jusqu’au clic (1…7)
  • rappel complet de l’échelle (1 = « jamais » … 7 = « plusieurs fois/j »)

Deux CSV téléchargeables à la fin : _lexicale.csv et _vocab.csv
"""
import time, random, uuid, pandas as pd, streamlit as st

# ═════════════════════════════════════════════════════════════════════════════
#  LISTES DE MOTS
# ═════════════════════════════════════════════════════════════════════════════
PSEUDOS = [
    "appendance", "arrancerai", "assoubiers", "caratillés", "cavartenne",
    "caporenèse", "batistrale", "bâfrentade", "banonneuse"
]
WORDS = [
    "appartenez", "appartenir", "appartiens", "bolivienne", "bolognaise",
    "bombardais", "cascadeurs", "cascadeuse", "cascatelle"
]
VOCAB_WORDS = ["merise", "roseau", "viaduc", "anode", "appeau", "miroir", "cornac"]

# ═════════════════════════════════════════════════════════════════════════════
#  PARAMÈTRES TEMPORELS
# ═════════════════════════════════════════════════════════════════════════════
FIX, BLANK      = .5, .5               # 500 ms chacun
LIM_MS          = 2_000                # délai max partie 1
ISI_VOC         = 1.5                  # blanc 1 500 ms partie 2
TICK            = .05                  # pas de « boucle » 50 ms

# ═════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATION DES ESSAIS – PARTIE 1
# ═════════════════════════════════════════════════════════════════════════════
def build_trials():
    """
    r paires mot+mot   (r tiré aléatoirement 0–4)
    m = 9-2r paires mot+pseudo
    Jamais pseudo+pseudo - aucun item réutilisé.
    """
    r = random.randint(0, 4)
    m = 9 - 2 * r
    random.shuffle(WORDS)
    random.shuffle(PSEUDOS)
    trials = []

    # paires mot + mot  (cle correcte = 1)
    for k in range(r):
        a, b = WORDS[2*k], WORDS[2*k+1]
        trials.append(dict(w1=a, w2=b, cle=1))

    # paires mot + pseudo (cle correcte = 2)
    for k in range(m):
        w, p = WORDS[2*r + k], PSEUDOS[k]
        w1, w2 = (w, p) if random.random() < .5 else (p, w)
        trials.append(dict(w1=w1, w2=w2, cle=2))

    random.shuffle(trials)
    return pd.DataFrame(trials)         # colonnes : w1 w2 cle

# ═════════════════════════════════════════════════════════════════════════════
#  INITIALISATION DES ÉTATS STREAMLIT
# ═════════════════════════════════════════════════════════════════════════════
def init_state():
    s = st.session_state
    # routage global
    s.setdefault("page", 0)             # 0 intro 1 / 1 tâche 1 / 2 intro 2 /
                                        # 3 tâche 2 / 4 fin
    # ---------- PARTIE 1
    if "stim_lex" not in s:
        s.stim_lex = build_trials()
    s.setdefault("lex_trial", 0)
    s.setdefault("lex_phase", "fix")    # fix blank stim fb
    s.setdefault("lex_t0", time.perf_counter())
    s.setdefault("lex_t_stim", 0.0)
    s.setdefault("lex_fb_left", 0.0)
    s.setdefault("lex_log", [])         # liste de dict

    # ---------- PARTIE 2
    if "stim_vocab" not in s:
        w = VOCAB_WORDS.copy(); random.shuffle(w)
        s.stim_vocab = w
    s.setdefault("voc_trial", 0)
    s.setdefault("voc_phase", "fix")    # fix blank word isi
    s.setdefault("voc_t0", time.perf_counter())
    s.setdefault("voc_t_word", 0.0)
    s.setdefault("voc_log", [])

init_state()

# ═════════════════════════════════════════════════════════════════════════════
#  OUTIL DE « TICK » (rafraîchit la page après une petite pause)
# ═════════════════════════════════════════════════════════════════════════════
def tick():
    time.sleep(TICK)
    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PARTIE 1 – INTRO
# ═════════════════════════════════════════════════════════════════════════════
def page_intro_lex():
    st.set_page_config(page_title="Expérimentation", page_icon="🔡")
    st.title("Partie 1 – Détection de pseudo-mot")
    st.markdown(f"""
Vous allez voir **{len(st.session_state.stim_lex)}** paires de chaînes
(sans répétition).

• **Seulement des mots**  →  si les deux sont de vrais mots français  
• **Pseudo-mot présent**  →  s’il y a au moins un pseudo-mot  

Vous disposez de **2 s** pour répondre ; au-delà, le message *Trop lent*
s’affiche brièvement.
""")
    if st.button("Commencer la partie 1 ➡️"):
        st.session_state.page = 1
        st.session_state.lex_trial = 0
        st.session_state.lex_phase = "fix"
        st.session_state.lex_t0    = time.perf_counter()
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PARTIE 1 – BOUCLE TÂCHE
# ═════════════════════════════════════════════════════════════════════════════
def page_task_lex():
    i  = st.session_state.lex_trial
    df = st.session_state.stim_lex
    if i >= len(df):                         # partie terminée
        st.session_state.page = 2
        st.rerun(); return

    row = df.iloc[i]
    w1, w2, cle_corr = row.w1, row.w2, row.cle
    phase   = st.session_state.lex_phase
    elapsed = time.perf_counter() - st.session_state.lex_t0

    # ------ 1. FIX ------
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.lex_phase = "blank"
            st.session_state.lex_t0    = time.perf_counter()
        tick()

    # ------ 2. BLANK ------
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.lex_phase   = "stim"
            st.session_state.lex_t_stim  = time.perf_counter()
            st.session_state.lex_t0      = time.perf_counter()
        tick()

    # ------ 3. STIM ------
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

        rt = int((time.perf_counter() - st.session_state.lex_t_stim)*1000)

        # a) réponse dans les temps
        if resp is not None and rt <= LIM_MS:
            score = 1 if resp == cle_corr else 0
            st.session_state.lex_log.append(
                dict(trial=i+1, w1=w1, w2=w2, resp=resp,
                     rt=rt, score=score, too_slow=0))
            st.session_state.lex_trial += 1
            st.session_state.lex_phase = "fix"
            st.session_state.lex_t0    = time.perf_counter()
            st.rerun()

        # b) délai dépassé
        elif rt > LIM_MS:
            st.session_state.lex_log.append(
                dict(trial=i+1, w1=w1, w2=w2, resp=None,
                     rt=rt, score=0, too_slow=1))
            st.session_state.lex_fb_left = 1.5
            st.session_state.lex_phase   = "fb"
            st.session_state.lex_t0      = time.perf_counter()
            st.rerun()

        tick()

    # ------ 4. FEEDBACK « Trop lent » ------
    elif phase == "fb":
        st.markdown("<h2 style='text-align:center'>Trop lent</h2>", unsafe_allow_html=True)
        if elapsed >= st.session_state.lex_fb_left:
            st.session_state.lex_trial += 1
            st.session_state.lex_phase  = "fix"
            st.session_state.lex_t0     = time.perf_counter()
            st.rerun()
        else:
            tick()

# ═════════════════════════════════════════════════════════════════════════════
#  PARTIE 2 – INTRO
# ═════════════════════════════════════════════════════════════════════════════
def page_intro_vocab():
    st.title("Partie 2 – Vocabulaire : fréquence d’exposition à l’écrit")
    st.write("Après un « + » (500 ms) et un blanc (500 ms), un mot apparaît.")
    st.write("Choisissez sur l’échelle suivante :")
    st.markdown("""
| Bouton | Signification |
|:---:|---|
| **1** | vous ne le rencontrez **jamais** |
| **2** | environ **une fois par an** |
| **3** | **une fois par mois** |
| **4** | **une fois par semaine** |
| **5** | **tous les deux jours** |
| **6** | **une fois par jour** |
| **7** | **plusieurs fois par jour** |
""")
    st.write("Le mot reste affiché jusqu’à votre clic. Il y a 7 mots au total.")
    if st.button("Commencer la partie 2 ➡️"):
        st.session_state.page      = 3
        st.session_state.voc_trial = 0
        st.session_state.voc_phase = "fix"
        st.session_state.voc_t0    = time.perf_counter()
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PARTIE 2 – BOUCLE TÂCHE
# ═════════════════════════════════════════════════════════════════════════════
def page_task_vocab():
    j  = st.session_state.voc_trial
    lst= st.session_state.stim_vocab
    if j >= len(lst):                         # terminé
        st.session_state.page = 4
        st.rerun(); return

    word  = lst[j]
    phase = st.session_state.voc_phase
    elapsed = time.perf_counter() - st.session_state.voc_t0

    # -- FIX
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>", unsafe_allow_html=True)
        if elapsed >= FIX:
            st.session_state.voc_phase = "blank"
            st.session_state.voc_t0    = time.perf_counter()
        tick()

    # -- BLANC
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK:
            st.session_state.voc_phase = "word"
            st.session_state.voc_t_word= time.perf_counter()
            st.session_state.voc_t0    = time.perf_counter()
        tick()

    # -- WORD + ÉCHELLE 1-7
    elif phase == "word":
        st.markdown(f"<div style='text-align:center;font-family:Times New Roman;"
                    f"font-size:42px;'>{word}</div>", unsafe_allow_html=True)

        cols = st.columns(7)
        resp = None
        for idx in range(7):
            with cols[idx]:
                if st.button(str(idx+1), key=f"rate_{j}_{idx}"):
                    resp = idx + 1
        if resp is not None:
            rt = int((time.perf_counter() - st.session_state.voc_t_word)*1000)
            st.session_state.voc_log.append(
                dict(order=j+1, word=word, rating=resp, rt=rt))
            st.session_state.voc_phase = "isi"
            st.session_state.voc_t0    = time.perf_counter()
            st.rerun()
        else:
            tick()

    # -- ISI 1 500 ms
    elif phase == "isi":
        st.empty()
        if elapsed >= ISI_VOC:
            st.session_state.voc_trial += 1
            st.session_state.voc_phase  = "fix"
            st.session_state.voc_t0     = time.perf_counter()
            st.rerun()
        else:
            tick()

# ═════════════════════════════════════════════════════════════════════════════
#  FIN – EXPORT CSV
# ═════════════════════════════════════════════════════════════════════════════
def page_fin():
    st.title("Fin – merci pour votre participation !")

    df_lex = pd.DataFrame(st.session_state.lex_log)
    st.subheader("Partie 1 : pseudo-mots")
    st.dataframe(df_lex)
    st.download_button("📥 Télécharger partie 1 (CSV)",
        data=df_lex.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_lexicale.csv", mime="text/csv")

    df_voc = pd.DataFrame(st.session_state.voc_log)
    st.subheader("Partie 2 : vocabulaire")
    st.dataframe(df_voc)
    st.download_button("📥 Télécharger partie 2 (CSV)",
        data=df_voc.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
        file_name=f"{uuid.uuid4()}_vocab.csv", mime="text/csv")

    st.success("Fichiers prêts – vous pouvez fermer l’onglet.")

# ═════════════════════════════════════════════════════════════════════════════
#  ROUTAGE GLOBAL
# ═════════════════════════════════════════════════════════════════════════════
pg = st.session_state.page
if   pg == 0: page_intro_lex()
elif pg == 1: page_task_lex()
elif pg == 2: page_intro_vocab()
elif pg == 3: page_task_vocab()
else        : page_fin()
