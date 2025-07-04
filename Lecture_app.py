# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JavaScript)
– Zone de saisie invisible avant <Espace>
– Zone supprimée dès validation <Entrée>
© 2024 – usage pédagogique
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───────── PARAMÈTRES EXPÉRIMENTAUX ──────────────────────────────────
CYCLE_MS  = 350       # durée d’un cycle
STEP_MS   = 14        # incrément du mot
MASK_CHAR = "#"       # signe pour le masque

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───────── INITIALISATION DE SESSION ─────────────────────────────────
s = st.session_state
if "stage" not in s:                 # première exécution
    s.stage        = "intro"         # intro ▸ trial ▸ end
    s.idx          = 0               # index mot courant
    s.phase        = "js"            # js ▸ typing
    s.rt_ms        = None
    s.answer_ready = False
    s.results      = []

# ───────── CHAMP CACHÉ (JS ➜ Python) ─────────────────────────────────
def hidden_receiver():
    st.markdown("<style>#receiver{display:none;}</style>", unsafe_allow_html=True)
    st.text_input("", key="receiver", label_visibility="collapsed")

# ───────── Gabarit JS (aucune accolade à échapper) ───────────────────
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
  const idx = Math.floor(e / CYCLE);
  const d   = Math.min(STEP*(idx+1), CYCLE);
  div.textContent = (e % CYCLE) < d ? WORD : MASK;
  rafID = requestAnimationFrame(flip);
}
rafID = requestAnimationFrame(flip);

function finish(){
  stop = true;
  cancelAnimationFrame(rafID);
  div.textContent  = "";
  div.style.display= "none";
  const rt = Math.round(performance.now() - start);
  const hidden = window.parent.document.getElementById('receiver');
  if(hidden){
      hidden.value = JSON.stringify({idx:%%IDX%%, rt:rt});
      hidden.dispatchEvent(new Event('input', {bubbles:true}));
  }
}

document.addEventListener('keydown', ev=>{
  if(ev.code==='Space' || ev.key===' ') finish();
});
</script>
"""

def demask_component(word: str, idx: int):
    html = (RAW_JS
            .replace("%%WORD%%", word)
            .replace("%%MASK%%", MASK_CHAR * len(word))
            .replace("%%CYCLE%%", str(CYCLE_MS))
            .replace("%%STEP%%",  str(STEP_MS))
            .replace("%%IDX%%",   str(idx)))
    components.html(html, height=400, scrolling=False)

# ───────── CALLBACK : validation de la réponse ───────────────────────
def on_answer():
    s.answer_ready = True

# ───────── PAGE INTRO ────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.write(
        "• Le mot se dévoile progressivement.\n"
        "• Dès que vous l’avez reconnu, appuyez sur la **barre Espace**.\n"
        "• Tapez le mot, validez par **Entrée**."
    )
    if st.button("Démarrer"):
        s.stage, s.phase = "trial", "js"
        st.rerun()

# ───────── PAGE TRIAL : un essai ─────────────────────────────────────
def page_trial():
    if s.idx >= len(STIMULI):
        s.stage = "end"; st.rerun(); return

    word = STIMULI[s.idx]
    hidden_receiver()
    msg = s.get("receiver", "")

    # --- Phase 1 : présentation JS ---
    if s.phase == "js":
        demask_component(word, s.idx)
        if msg.startswith("{"):
            data = json.loads(msg)
            s.rt_ms      = data["rt"]
            s.phase      = "typing"
            s["receiver"] = ""              # réinitialise
            st.rerun()

    # --- Phase 2 : saisie ---
    elif s.phase == "typing":
        st.write(f"Temps de réaction : **{s.rt_ms} ms**")
        key_ans = f"ans_{s.idx}"
        st.text_input("Votre réponse :", key=key_ans, on_change=on_answer)

        # quand Entrée a été pressée
        if s.answer_ready:
            typed = st.session_state.get(key_ans, "")
            s.answer_ready = False

            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = typed.upper() == word,
                rt_ms    = s.rt_ms
            ))

            # on enlève la zone de saisie de l'état
            if key_ans in st.session_state:
                del st.session_state[key_ans]

            s.idx   += 1
            s.phase  = "js"
            st.rerun()

# ───────── PAGE FIN ─────────────────────────────────────────────────
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

# ───────── ROUTAGE PRINCIPAL ────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.stage]()
