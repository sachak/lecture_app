# -*- coding: utf-8 -*-
"""
Expérience 3 – Progressive-demasking (Streamlit + JS)
© 2024 – libre de droits pédagogiques
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───────── PARAMÈTRES ────────────────────────────────────────────────────
CYCLE_MS  = 350          # durée totale d’un cycle
STEP_MS   = 14           # +14 ms mot / –14 ms masque
MASK_CHAR = "#"          # caractère du masque

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───────── ÉTAT DE SESSION ───────────────────────────────────────────────
def init():
    s = st.session_state
    s.setdefault("page", "intro")
    s.setdefault("i", 0)              # index essai
    s.setdefault("waiting_js", False)
    s.setdefault("typing", False)
    s.setdefault("rt", None)
    s.setdefault("results", [])
init()

# ───────── RECEIVER : capte le message JS → Python ───────────────────────
def receiver_component():
    components.html(
        """
<script>
window.addEventListener("message", (evt)=>{
  if(evt.data && evt.data.source === "demask"){
      const hidden = window.parent.document.getElementById("receiver_input");
      if(hidden){
          hidden.value = JSON.stringify(evt.data);
          hidden.dispatchEvent(new Event('input',{bubbles:true}));
      }
  }
});
</script>
""",
        height=0,
    )

# ───────── STIMULUS PROGRESSIVE DEMASK (JS) ──────────────────────────────
def demask_component(word: str):
    mask = MASK_CHAR * len(word)
    html_code = f"""
<div id="stim"
     style="font-size:64px;text-align:center;font-family:monospace;margin-top:25vh;">
</div>

<script>
// ===== paramètres transmis par Python =====
const WORD     = "{word}";
const MASK     = "{mask}";
const CYCLE_MS = {CYCLE_MS};
const STEP_MS  = {STEP_MS};

// ===== initialisation =====
let startTime = performance.now();
const stimDiv = document.getElementById("stim");

// ===== boucle frame-lockée =====
function flip(ts) {{
    const elapsed  = ts - startTime;
    const idx      = Math.floor(elapsed / CYCLE_MS);
    const stimDur  = Math.min(STEP_MS * (idx + 1), CYCLE_MS);
    const pos      = elapsed % CYCLE_MS;
    const showWord = pos < stimDur;

    stimDiv.textContent = showWord ? WORD : MASK;
    requestAnimationFrame(flip);
}}
requestAnimationFrame(flip);

// ===== réponse (barre espace) =====
window.addEventListener("keydown", (e) => {{
    if(e.code === "Space") {{
        const rt = performance.now() - startTime;
        window.parent.postMessage(
            {{ source:"demask", word:WORD, rt:Math.round(rt) }}, "*");
    }}
}});
</script>
"""
    components.html(html_code, height=400, scrolling=False)

# ───────── PAGES ─────────────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown("""
Cliquez sur **Démarrer**.<br>
Un mot apparaîtra peu à peu ; appuyez sur la **barre Espace** dès que vous l’avez reconnu,
puis tapez-le au clavier.
""", unsafe_allow_html=True)
    if st.button("Démarrer"):
        st.session_state.page = "trial"
        st.session_state.waiting_js = True
        st.rerun()

def page_trial():
    i = st.session_state.i
    if i >= len(STIMULI):
        st.session_state.page = "end"
        st.rerun(); return

    word = STIMULI[i]

    # 1) phase JS
    if st.session_state.waiting_js:
        receiver_component()
        demask_component(word)

        # input caché où JS colle le JSON
        data = st.text_input("", key="receiver_input", label_visibility="collapsed")
        if data:
            msg = json.loads(data)
            st.session_state.rt = msg["rt"]
            st.session_state.waiting_js = False
            st.session_state.typing = True
            st.session_state["receiver_input"] = ""   # reset
            st.rerun()

    # 2) phase saisie clavier
    elif st.session_state.typing:
        st.write(f"Temps de réaction : **{st.session_state.rt} ms**")
        typed = st.text_input("Tapez le mot reconnu :", key=f"typed_{i}")
        if typed:
            st.session_state.results.append(
                dict(stimulus=word,
                     response=typed.upper(),
                     rt_ms=st.session_state.rt,
                     correct=(typed.upper() == word))
            )
            st.session_state.i += 1
            st.session_state.waiting_js = True
            st.session_state.typing = False
            st.rerun()

def page_end():
    st.title("Expérience terminée, merci !")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Télécharger les résultats", csv,
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE ───────────────────────────────────────────────────────
page = st.session_state.page
if   page == "intro":  page_intro()
elif page == "trial":  page_trial()
else:                  page_end()
