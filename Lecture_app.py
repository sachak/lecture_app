# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JavaScript)
• La zone de saisie n’apparaît qu’après l’appui sur <Espace>
• Elle disparaît dès la validation (Entrée)
© 2024 – usage pédagogique
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─── Paramètres de l’expérience ────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ─── État Streamlit ────────────────────────────────────────────────────────
s = st.session_state
if "page" not in s:        # première exécution
    s.page   = "intro"     # intro | trial | end
    s.idx    = 0           # index du mot courant
    s.phase  = "js"        # js  | typing
    s.rt     = None
    s.results= []

# ─── HTML + JS : stimulus progressive-demasking ────────────────────────────
def demask_component(word: str, idx: int):
    mask = MASK_CHAR * len(word)
    html = f"""
<div id="stim" style="font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD="{word}";
const MASK="{mask}";
const CYCLE={CYCLE_MS};
const STEP={STEP_MS};
let start = performance.now();
let stop  = false;
let div   = document.getElementById("stim");

function flip(ts){{
    if(stop) return;
    const el   = ts - start;
    const i    = Math.floor(el / CYCLE);
    const d    = Math.min(STEP * (i+1), CYCLE);
    div.textContent = (el % CYCLE) < d ? WORD : MASK;
    requestAnimationFrame(flip);
}}
requestAnimationFrame(flip);

function endTrial(){{
   stop = true;
   div.textContent = "";
   div.style.display = "none";
   const rt = Math.round(performance.now() - start);

   /* on écrit le JSON dans le champ caché de la page Streamlit */
   const hidden = window.parent.document.getElementById("receiver_input");
   if(hidden){{
       hidden.value = JSON.stringify({{idx:{idx}, rt:rt}});
       hidden.dispatchEvent(new Event('input', {{ bubbles:true }}));
   }}
}}

/* écoute de la barre espace */
document.addEventListener('keydown', e=>{
    if(e.code==='Space' || e.key===' ') endTrial();
});
</script>
"""
    components.html(html, height=400, scrolling=False, key=f"stim_{idx}")

# ─── Champ caché + CSS pour qu’il soit invisible ───────────────────────────
def hidden_receiver():
    st.markdown(
        "<style>input#receiver_input{display:none;}</style>",
        unsafe_allow_html=True
    )
    st.text_input("", key="receiver_input", label_visibility="collapsed")

# ─── Page : introduction ───────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. Un mot se dévoilera peu à peu. "
        "Dès que vous l’avez reconnu, appuyez sur la **barre Espace** ; "
        "la zone de réponse apparaîtra alors. Tapez le mot et validez par "
        "**Entrée**."
    )
    if st.button("Démarrer"):
        s.page, s.phase = "trial", "js"
        st.rerun()

# ─── Page : un essai ───────────────────────────────────────────────────────
def page_trial():
    if s.idx >= len(STIMULI):          # expérience terminée
        s.page = "end"; st.rerun(); return

    word = STIMULI[s.idx]
    hidden_receiver()                  # champ caché (toujours présent)
    msg = s.get("receiver_input", "")

    # Phase 1 : animation JS
    if s.phase == "js":
        demask_component(word, s.idx)
        if msg.startswith("{"):        # JSON reçu depuis le JS
            data = json.loads(msg)
            s.rt      = data["rt"]
            s.phase   = "typing"       # on passe à la saisie
            s["receiver_input"] = ""   # reset champ caché
            st.rerun()

    # Phase 2 : zone de réponse visible
    elif s.phase == "typing":
        st.write(f"Temps de réaction : **{s.rt} ms**")
        answer = st.text_input("Tapez le mot reconnu :", key=f"typed_{s.idx}")
        if answer:                     # Entrée = validation
            s.results.append(dict(
                stimulus = word,
                response = answer.upper(),
                correct  = answer.upper() == word,
                rt_ms    = s.rt
            ))
            s.idx   += 1
            s.phase  = "js"            # nouveau mot → phase animation
            st.rerun()

# ─── Page : fin ────────────────────────────────────────────────────────────
def page_end():
    st.title("Expérience terminée – merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "📥 Télécharger les résultats (.csv)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv"
    )
    st.success("Vous pouvez fermer l’onglet.")

# ─── Routage principal ─────────────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
