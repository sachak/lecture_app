# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JS)
champ de réponse : visible UNIQUEMENT après <Espace>,
retiré immédiatement après validation <Entrée>.
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─── paramètres ──────────────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"
STIMULI = [
    "AVION", "BALAI", "CARTE", "CHAUD", "CRANE", "GARDE", "LIVRE", "MERCI",
    "NAGER", "PARLE", "PORTE", "PHOTO", "RADIO", "ROULE", "SALON", "SUCRE",
    "TABLE", "TIGRE", "VIVRE", "VOILE"
]
random.shuffle(STIMULI)

# ─── état ------------------------------------------------------------------
s = st.session_state
if "stage" not in s:            # première exécution
    s.stage   = "intro"         # intro ▸ trial ▸ end
    s.idx     = 0               # index mot courant
    s.rt_ms   = None
    s.results = []
    s.show_box = False          # le champ de réponse doit-il être affiché ?

# ─── champ caché (réception JSON JS → Py) ----------------------------------
st.markdown("<style>#receiver{display:none;}</style>", unsafe_allow_html=True)
hidden = st.text_input("", key="receiver", label_visibility="collapsed")

# ─── composant JS (mot / masque) -------------------------------------------
RAW_JS = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>

<script>
const WORD  = "%%WORD%%";
const MASK  = "%%MASK%%";
const CYCLE = %%CYCLE%%;
const STEP  = %%STEP%%;
let start = performance.now();
let stop  = false;
let rafID = null;
const div = document.getElementById('stim');

function flip(ts){
  if(stop) return;
  const e   = ts - start;
  const i   = Math.floor(e / CYCLE);
  const d   = Math.min(STEP*(i+1), CYCLE);
  div.textContent = (e % CYCLE) < d ? WORD : MASK;
  rafID = requestAnimationFrame(flip);
}
rafID = requestAnimationFrame(flip);

function finish(){
  stop = true;
  cancelAnimationFrame(rafID);
  div.textContent = "";
  div.style.display = "none";
  const rt = Math.round(performance.now() - start);
  const hid = window.parent.document.getElementById('receiver');
  if(hid){
      hid.value = JSON.stringify({rt:rt});
      hid.dispatchEvent(new Event('input', {bubbles:true}));
  }
}
document.addEventListener('keydown', ev=>{
  if(ev.code==='Space' || ev.key===' ') finish();
});
</script>
"""

def js_stimulus(word: str):
    html = (RAW_JS
            .replace("%%WORD%%", word)
            .replace("%%MASK%%", MASK_CHAR * len(word))
            .replace("%%CYCLE%%", str(CYCLE_MS))
            .replace("%%STEP%%",  str(STEP_MS)))
    components.html(html, height=400, scrolling=False)

# ─── pages -----------------------------------------------------------------
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.write(
        "1. Le mot est d’abord masqué puis se dévoile peu à peu.\n"
        "2. Dès que vous le reconnaissez, appuyez sur **Espace**.\n"
        "3. Tapez alors le mot et appuyez sur **Entrée**."
    )
    if st.button("Démarrer"):
        s.stage, s.show_box = "trial", False
        st.experimental_rerun()

def page_trial():
    if s.idx >= len(STIMULI):
        s.stage = "end"; st.experimental_rerun(); return

    word = STIMULI[s.idx]

    # 1) présentation (si la boîte n’est pas encore affichée)
    if not s.show_box:
        js_stimulus(word)

    # 2) si le JS vient d’envoyer le RT → afficher la boîte
    if hidden.startswith("{") and not s.show_box:
        s.rt_ms = json.loads(hidden)["rt"]
        s.show_box = True
        st.session_state.receiver = ""   # reset
        st.experimental_rerun()

    # 3) gérer la boîte de réponse uniquement si show_box == True
    if s.show_box:
        st.write(f"Temps de réaction : **{s.rt_ms} ms**")
        placeholder = st.empty()         # conteneur temporaire

        # affiche la zone de saisie dans le placeholder
        answer = placeholder.text_input("Votre réponse :", key=f"a_{s.idx}")

        # dès qu’on validera (Entrée), answer sera non-vide
        if answer:
            s.results.append(dict(
                stimulus = word,
                response = answer.upper(),
                correct  = answer.upper() == word,
                rt_ms    = s.rt_ms
            ))
            placeholder.empty()          # SUPPRIME la zone de saisie
            del st.session_state[f"a_{s.idx}"]  # nettoie le key
            s.idx     += 1
            s.show_box = False           # repasse en mode présentation
            st.experimental_rerun()

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

# ─── routage ----------------------------------------------------------------
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.stage]()
