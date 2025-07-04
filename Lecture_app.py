# -*- coding: utf-8 -*-
"""
Expérience 3 – Progressive-demasking (Streamlit + JS)
Le stimulus disparaît immédiatement après l’appui sur <Espace>.
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─── paramètres ──────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ─── état session ───────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page, s.idx, s.wait_js, s.typing, s.rt, s.results = "intro", 0, False, False, None, []

# ─── composant récepteur (message JS → Python) ──────────
def receiver():
    components.html(
        """
<script>
window.addEventListener("message", evt => {
  if (evt.data && evt.data.source === "demask") {
      const hidden = window.parent.document.getElementById("receiver_input");
      if (hidden) {
          hidden.value = JSON.stringify(evt.data);
          hidden.dispatchEvent(new Event('input', {bubbles: true}));
      }
  }
});
</script>
""", height=0)

# ─── composant stimulus (alternance + arrêt net) ────────
def demask(word: str):
    mask = MASK_CHAR * len(word)
    html = f"""
<div id="stim" style="font-size:64px;text-align:center;font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD     = "{word}";
const MASK     = "{mask}";
const CYCLE_MS = {CYCLE_MS};
const STEP_MS  = {STEP_MS};

let start  = performance.now();
let div    = document.getElementById("stim");
let stop   = false;
let rafID  = null;

/* ---- boucle frame-lockée ---- */
function flip(ts) {{
    if (stop) return;
    const elapsed  = ts - start;
    const idx      = Math.floor(elapsed / CYCLE_MS);
    const stimDur  = Math.min(STEP_MS * (idx + 1), CYCLE_MS);
    const pos      = elapsed % CYCLE_MS;
    const show     = pos < stimDur;
    div.textContent = show ? WORD : MASK;
    rafID = requestAnimationFrame(flip);
}}
rafID = requestAnimationFrame(flip);

/* ---- réponse utilisateur ---- */
window.addEventListener("keydown", e => {{
    if ((e.key === ' ' || e.code === 'Space') && !stop) {{
        stop = true;
        cancelAnimationFrame(rafID);     /* stoppe l’animation             */
        div.textContent = "";            /* vide le contenu                 */
        div.style.display = "none";      /* masque complètement l’élément   */
        const rt = Math.round(performance.now() - start);
        window.parent.postMessage({{
            source: "demask",
            word  : WORD,
            rt    : rt
        }}, "*");
    }}
}});
</script>
"""
    components.html(html, height=400, scrolling=False)

# ─── pages Streamlit ────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. Le mot se dévoile progressivement ; "
        "appuyez sur la **barre Espace** dès que vous l’avez reconnu, "
        "puis saisissez-le."
    )
    if st.button("Démarrer"):
        s.page, s.wait_js = "trial", True
        st.rerun()

def page_trial():
    if s.idx >= len(STIMULI):
        s.page = "end"; st.rerun(); return

    word = STIMULI[s.idx]

    # --- phase JS ---
    if s.wait_js:
        receiver()
        demask(word)
        msg = st.text_input("", key="receiver_input", label_visibility="collapsed")
        if msg:
            data = json.loads(msg)
            s.rt = data["rt"]
            s.wait_js, s.typing = False, True
            s["receiver_input"] = ""
            st.rerun()

    # --- phase saisie ---
    elif s.typing:
        st.write(f"Temps de réaction : **{s.rt} ms**")
        typed = st.text_input("Tapez le mot reconnu :", key=f"typed_{s.idx}")
        if typed:
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = typed.upper() == word,
                rt_ms    = s.rt))
            s.idx += 1
            s.wait_js, s.typing = True, False
            st.rerun()

def page_end():
    st.title("Expérience terminée – merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "📥 Télécharger les résultats (.csv)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ─── routage ────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
