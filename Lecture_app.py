# -*- coding: utf-8 -*-
"""
Expérience 3 – Progressive-demasking (Streamlit + JavaScript)
Le mot/masque disparaît dès que le participant appuie sur <Espace>.
© 2024 – usage pédagogique libre
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─── Paramètres généraux ─────────────────────────────────────────────
CYCLE_MS  = 350          # durée d’un cycle
STEP_MS   = 14           # +14 ms mot  / –14 ms masque
MASK_CHAR = "#"          # caractère du masque

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ─── Initialisation de session ───────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page     = "intro"
    s.index    = 0
    s.wait_js  = False
    s.typing   = False
    s.rt_ms    = None
    s.results  = []

# ─── Composant récepteur : récupère le message JS → Python ───────────
def receiver():
    components.html(
        """
<script>
window.addEventListener("message", (evt) => {
    if (evt.data && evt.data.source === "demask") {
        const hidden = window.parent.document.getElementById("receiver_input");
        if (hidden) {
            hidden.value = JSON.stringify(evt.data);
            hidden.dispatchEvent(new Event('input', {bubbles:true}));
        }
    }
});
</script>
""",
        height=0
    )

# ─── Composant stimulus : alternance mot/masque + disparition ───────
def demask(word: str):
    mask = MASK_CHAR * len(word)

    html = f"""
<div id="stim" style="font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD     = "{word}";
const MASK     = "{mask}";
const CYCLE_MS = {CYCLE_MS};
const STEP_MS  = {STEP_MS};

let start   = performance.now();
let divElem = document.getElementById("stim");
let stop    = false;

/* Boucle frame-lockée */
function flip(ts) {{
    if (stop) return;
    const elapsed  = ts - start;
    const cycleIdx = Math.floor(elapsed / CYCLE_MS);
    const stimDur  = Math.min(STEP_MS * (cycleIdx + 1), CYCLE_MS);
    const pos      = elapsed % CYCLE_MS;
    const showWord = pos < stimDur;
    divElem.textContent = showWord ? WORD : MASK;
    requestAnimationFrame(flip);
}}
requestAnimationFrame(flip);

/* Réponse avec la barre Espace */
window.addEventListener("keydown", (e) => {{
    if (e.code === "Space" && !stop) {{
        stop = true;
        divElem.textContent = "";                 /* efface mot + masque */
        const rt = performance.now() - start;
        window.parent.postMessage({{
            source: "demask",
            word  : WORD,
            rt    : Math.round(rt)
        }}, "*");
    }}
}});
</script>
"""
    components.html(html, height=400, scrolling=False)

# ─── Pages Streamlit ─────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. \n"
        "Le mot apparaît progressivement ; dès que vous l’avez reconnu, "
        "appuyez sur la **barre Espace** puis tapez le mot."
    )
    if st.button("Démarrer"):
        s.page = "trial"
        s.wait_js = True
        st.rerun()

def page_trial():
    if s.index >= len(STIMULI):
        s.page = "end"
        st.rerun()
        return

    word = STIMULI[s.index]

    # Phase 1 : affichage JS
    if s.wait_js:
        receiver()
        demask(word)
        js_msg = st.text_input("", key="receiver_input",
                               label_visibility="collapsed")
        if js_msg:
            data = json.loads(js_msg)
            s.rt_ms   = data["rt"]
            s.wait_js = False
            s.typing  = True
            s["receiver_input"] = ""          # reset
            st.rerun()

    # Phase 2 : saisie du mot
    elif s.typing:
        st.write(f"Temps de réaction : **{s.rt_ms} ms**")
        typed = st.text_input("Tapez le mot reconnu :", key=f"typed_{s.index}")
        if typed:
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = (typed.upper() == word),
                rt_ms    = s.rt_ms
            ))
            s.index  += 1
            s.wait_js = True
            s.typing  = False
            st.rerun()

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

# ─── Routage ─────────────────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
