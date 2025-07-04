# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JavaScript)
– La zone de saisie n’apparaît qu’après Espace et disparaît après Entrée
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───────── PARAMÈTRES EXPÉRIMENTAUX ──────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───────── ÉTAT DE SESSION ───────────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page, s.idx, s.phase, s.rt, s.results = "intro", 0, "js", None, []

# ───────── CHAMP CACHÉ (réception JS → Python) ───────────────────────
def hidden_receiver():
    st.markdown("<style>#receiver_input{{display:none;}}</style>",
                unsafe_allow_html=True)
    st.text_input("", key="receiver_input", label_visibility="collapsed")

# ───────── COMPOSANT JS (demasking) ──────────────────────────────────
def demask_component(word: str, idx: int):
    mask = MASK_CHAR * len(word)

    html = f"""
<div id="stim" style="font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD  = "{word}";
const MASK  = "{mask}";
const CYCLE = {CYCLE_MS};
const STEP  = {STEP_MS};

let start = performance.now();
let div   = document.getElementById("stim");
let stop  = false;
let rafID = null;

/* --------- boucle frame-lockée --------- */
function flip(ts) {{
    if (stop) return;
    const elapsed = ts - start;
    const i       = Math.floor(elapsed / CYCLE);
    const dur     = Math.min(STEP * (i + 1), CYCLE);
    div.textContent = (elapsed % CYCLE) < dur ? WORD : MASK;
    rafID = requestAnimationFrame(flip);
}}
rafID = requestAnimationFrame(flip);

/* --------- fin d’essai --------- */
function endTrial() {{
    stop = true;
    cancelAnimationFrame(rafID);
    div.textContent = "";
    div.style.display = "none";
    const rt = Math.round(performance.now() - start);

    const hidden = window.parent.document.getElementById("receiver_input");
    if (hidden) {{
        hidden.value = JSON.stringify({{idx: {idx}, rt: rt}});
        hidden.dispatchEvent(new Event('input', {{bubbles:true}}));
    }}
}}

/* --------- écoute barre Espace --------- */
document.addEventListener('keydown', (e) => {{
    if (e.code === 'Space' || e.key === ' ') {{
        endTrial();
    }}
}});
</script>
"""
    components.html(html, height=400, scrolling=False, key=f"stim_{idx}")

# ───────── PAGE INTRO ────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. Un mot se dévoilera peu à peu. "
        "Dès que vous l’avez reconnu, appuyez sur la **barre Espace** ; "
        "la zone de réponse apparaîtra alors. Tapez le mot puis validez "
        "par **Entrée**."
    )
    if st.button("Démarrer"):
        s.page, s.phase = "trial", "js"
        st.rerun()

# ───────── PAGE TRIAL ────────────────────────────────────────────────
def page_trial():
    if s.idx >= len(STIMULI):
        s.page = "end"; st.rerun(); return

    word = STIMULI[s.idx]
    hidden_receiver()                 # champ invisible présent en permanence
    msg = s.get("receiver_input", "")

    # Phase 1 : présentation JS
    if s.phase == "js":
        demask_component(word, s.idx)
        if msg.startswith("{"):
            data = json.loads(msg)
            s.rt = data["rt"]
            s.phase            = "typing"
            s["receiver_input"] = ""   # reset
            st.rerun()

    # Phase 2 : zone de saisie
    elif s.phase == "typing":
        st.write(f"Temps de réaction : **{s.rt} ms**")
        typed = st.text_input("Tapez le mot reconnu :", key=f"inp_{s.idx}")
        if typed:
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = typed.upper() == word,
                rt_ms    = s.rt
            ))
            s.idx   += 1
            s.phase  = "js"
            st.rerun()

# ───────── PAGE FIN ─────────────────────────────────────────────────
def page_end():
    st.title("Expérience terminée – merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Télécharger les résultats (.csv)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE ───────────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
