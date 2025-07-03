# -*- coding: utf-8 -*-
"""
Décision lexicale – 10 essais d’entraînement
timeline : + 500 ms → blanc 500 ms → mots (≤2 s) → feedback → essai suivant
enregistrement : prime, cible, type, cond, réponse, RT, correcte, too_slow
Aucune dépendance externe (tout est fait avec Streamlit + JS « setTimeout »)
"""
import time, uuid, pandas as pd, streamlit as st

st.set_page_config(page_title="Décision lexicale", page_icon="🔠")

# ───────────────────────────── PARAMÈTRES ────────────────────────────────────
TIME_LIMIT_MS = 2000       # délai maximum pour répondre (2 000 ms)
FIX_DUR       = 0.5        # « + » 500 ms
BLANK_DUR     = 0.5        # blanc 500 ms
REFRESH_MS    = 50         # période de rafraîchissement automatique (ms)

# ───────────────────────────── STIMULI ───────────────────────────────────────
stimuli = pd.DataFrame([
    # prime      cible        type            cond  cle (1=Mot,2=Non-mot)
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

# ───────────────────────────── ÉTAT PERSISTANT ───────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", 0)               # 0 = instructions, 1 = tâche, 2 = fin
    # machine d’états pour la tâche
    s.setdefault("trial",        0)       # index essai courant
    s.setdefault("phase",        "fix")   # fix / blank / stim / fb
    s.setdefault("phase_start",  time.perf_counter())
    s.setdefault("stim_start",   0.0)     # horodatage apparition mots
    s.setdefault("fb_msg",       "")
    s.setdefault("fb_dur",       0.0)
    s.setdefault("results",      [])      # liste des essais
init_state()

# ───────────────────────────── AUTORELOAD JS (aucune lib externe) ────────────
def auto_refresh(interval_ms=50):
    """
    Injecte un petit script JS qui recharge la page après `interval_ms`.
    À appeler seulement pendant les phases où le temps compte.
    """
    st.markdown(
        f"""<script>
               setTimeout(function(){{window.location.reload();}},
                          {interval_ms});
            </script>""",
        unsafe_allow_html=True
    )

# ───────────────────────────── OUTILS ────────────────────────────────────────
def reset_phase(new_phase):
    st.session_state.phase       = new_phase
    st.session_state.phase_start = time.perf_counter()

def log_trial(**kw):
    st.session_state.results.append(kw)

# ───────────────────────────── PAGE 0 : INSTRUCTIONS ─────────────────────────
def page_instructions():
    st.title("Décision lexicale – entraînement")
    st.markdown("""
Séquence d’un essai :

1. « + » 500 ms  
2. Blanc 500 ms  
3. Deux mots : décidez si **le second est un mot français**  
   • bouton **Mot** (*A*)  
   • bouton **Non-mot** (*L*)  
4. 2 s maximum pour répondre  
5. *correct!* 500 ms **ou** *wrong response, or too slow!* 1 500 ms  
6. Nouvel essai

Cliquez sur le bouton pour démarrer (10 essais).
""")
    if st.button("Commencer ➡️"):
        st.session_state.page = 1
        # remise à zéro des marqueurs
        st.session_state.trial = 0
        reset_phase("fix")
        st.experimental_rerun()

# ───────────────────────────── PAGE 1 : TÂCHE ────────────────────────────────
def page_task():
    i = st.session_state.trial
    if i >= len(stimuli):                # tous les essais faits → page fin
        st.session_state.page = 2
        st.experimental_rerun()
        return

    # rafraîchissement automatique tant qu’on est dans la tâche
    auto_refresh(REFRESH_MS)

    prime, cible, typ, cond, cle_corr = stimuli.iloc[i]
    phase   = st.session_state.phase
    elapsed = time.perf_counter() - st.session_state.phase_start

    # ───────────── 1. FIXATION « + » ─────────────
    if phase == "fix":
        st.markdown("<h1 style='text-align:center'>+</h1>",
                    unsafe_allow_html=True)
        if elapsed >= FIX_DUR:
            reset_phase("blank")

    # ───────────── 2. BLANC ──────────────────────
    elif phase == "blank":
        st.empty()
        if elapsed >= BLANK_DUR:
            reset_phase("stim")
            st.session_state.stim_start = time.perf_counter()

    # ───────────── 3. STIMULI (≤ 2 s) ────────────
    elif phase == "stim":
        # affichage des deux mots
        st.markdown(
            f"<div style='text-align:center;font-size:42px;line-height:1.2'>"
            f"{prime}<br>{cible}</div>",
            unsafe_allow_html=True
        )

        # boutons de réponse
        col_mot, col_non = st.columns(2)
        clicked = None
        with col_mot:
            if st.button("Mot ✔️", key=f"mot_{i}"):
                clicked = 1
        with col_non:
            if st.button("Non-mot ❌", key=f"non_{i}"):
                clicked = 2

        rt = int((time.perf_counter() - st.session_state.stim_start) * 1000)

        # 3-A) clic dans le temps
        if clicked is not None and rt <= TIME_LIMIT_MS:
            correct = clicked == cle_corr
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=clicked,
                      rt=rt, too_slow=False, correcte=correct)
            st.session_state.fb_msg = "correct!" if correct else "wrong response, or too slow!"
            st.session_state.fb_dur = 0.5 if correct else 1.5
            reset_phase("fb")

        # 3-B) délai dépassé
        elif rt > TIME_LIMIT_MS:
            log_trial(prime=prime, cible=cible, type=typ, cond=cond,
                      cle_correcte=cle_corr, reponse=None,
                      rt=rt, too_slow=True, correcte=False)
            st.session_state.fb_msg = "wrong response, or too slow!"
            st.session_state.fb_dur = 1.5
            reset_phase("fb")

    # ───────────── 4. FEEDBACK ───────────────────
    elif phase == "fb":
        st.markdown(f"<h2 style='text-align:center'>{st.session_state.fb_msg}</h2>",
                    unsafe_allow_html=True)
        if elapsed >= st.session_state.fb_dur:
            st.session_state.trial += 1      # prochain essai
            reset_phase("fix")

# ───────────────────────────── PAGE 2 : FIN + CSV ────────────────────────────
def page_end():
    st.title("Fin de l’entraînement – merci !")

    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df)

    csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 Télécharger le CSV",
                       data=csv,
                       file_name=f"{uuid.uuid4()}_lexicale.csv",
                       mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────────────────────────── ROUTAGE ───────────────────────────────────────
if st.session_state.page == 0:
    page_instructions()
elif st.session_state.page == 1:
    page_task()
else:
    page_end()
