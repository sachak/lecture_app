# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JavaScript)
– La zone de saisie n’apparaît qu’après <Espace>
– Elle disparaît dès la validation (Entrée)
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─── PARAMÈTRES ────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ─── ÉTAT SESSION ──────────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page, s.idx, s.wait_js, s.typing, s.rt, s.results = "intro", 0, False, False, None, []

# ─── COMPOSANT RÉCEPTEUR (caché) ──────────────────────────
def receiver():
    # CSS pour masquer complètement le champ caché
    st.markdown(
        """<style>#receiver_input{display:none !important;}</style>""",
        unsafe_allow_html=True
    )
    components.html(
        """
<script>
window.addEventListener("message", evt => {
  if (evt.data && evt.data.source === "demask") {
      const hidden = window.parent.document.getElementById("receiver_input");
      if (hidden) {
          hidden.value = JSON.stringify(evt.data);
          hidden.dispatchEvent(new Event('input', {bubbles:true}));
      }
  }
});
</script>
""", height=0)
    # Champ texte réellement caché
    st.text_input("", key="receiver_input", label_visibility="collapsed", disabled=True)

# ─── COMPOSANT STIMULUS (JS) ──────────────────────────────
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

let start  = performance.now();
let div    = document.getElementById("stim");
let stop   = false;
let rafID  = null;

/* Boucle frame-lockée */
function flip(ts) {{
    if (stop) return;
    const e   = ts - start;
    const idx = Math.floor(e / CYCLE_MS);
    const d   = Math.min(STEP_MS * (idx + 1), CYCLE_MS);
    const show= (e % CYCLE_MS) < d;
    div.textContent = show ? WORD : MASK;
    rafID = requestAnimationFrame(flip);
}}
rafID = requestAnimationFrame(flip);

/* Appui barre Espace */
window.addEventListener("keydown", e => {{
    if ((e.key === ' ' || e.code === 'Space') && !stop) {{
        stop = true;
        cancelAnimationFrame(rafID);
        div.textContent = "";
        div.style.display = "none";
        const rt = Math.round(performance.now() - start);
        window.parent.postMessage({{
            source:"demask", word:WORD, rt:rt
        }},"*");
    }}
}});
</script>
"""
    components.html(html, height=400, scrolling=False)

# ─── PAGES ────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. Le mot se dévoile progressivement ; "
        "appuyez sur la **barre Espace** dès que vous l’avez reconnu, "
        "puis tapez-le et validez par **Entrée**."
    )
    if st.button("Démarrer"):
        s.page, s.wait_js = "trial", True
        st.rerun()

def page_trial():
    if s.idx >= len(STIMULI):
        s.page = "end"; st.rerun(); return

    word = STIMULI[s.idx]

    # 1. Phase JavaScript
    if s.wait_js:
        receiver()
        demask(word)
        msg = s.get("receiver_input","")
        if msg and msg.strip().startswith("{"):
            data = json.loads(msg)
            s.rt = data["rt"]
            s.wait_js, s.typing = False, True
            s["receiver_input"] = ""          # reset
            st.rerun()

    # 2. Phase de saisie (visible seulement ici)
    elif s.typing:
        st.write(f"Temps de réaction : **{s.rt} ms**")
        typed = st.text_input("Tapez le mot reconnu puis Entrée :",
                              key=f"typed_{s.idx}")
        if typed:                             # validation par Entrée
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = (typed.upper() == word),
                rt_ms    = s.rt
            ))
            s.idx += 1
            s.wait_js, s.typing = True, False
            st.rerun()

def page_end():
    st.title("Expérience terminée – merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Télécharger les résultats (.csv)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ─── ROUTAGE ──────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
