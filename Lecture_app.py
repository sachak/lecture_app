import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as cpn

# ---------- PARAMÈTRES ------------------------------------------------
CYCLE_MS, STEP_MS, MASK_CH = 350, 14, "#"
WORDS = ["AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI",
         "NAGER","PARLE","PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE",
         "TABLE","TIGRE","VIVRE","VOILE"]
random.shuffle(WORDS)

# ---------- ÉTAT SESSION ----------------------------------------------
s = st.session_state
if "page" not in s:
    s.page   = "intro"      # intro ▸ trial ▸ end
    s.idx    = 0
    s.phase  = "js"         # js ▸ typing
    s.rt     = None
    s.data   = []

# ---------- CHAMP CACHÉ RÉCEPTION JS ----------------------------------
st.markdown("<style>#receiver{display:none}</style>", unsafe_allow_html=True)
hidden = st.text_input("", key="receiver", label_visibility="collapsed")

# ---------- Gabarit JavaScript ----------------------------------------
JS_RAW = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>
<script>
const WORD  = "%%WORD%%";
const MASK  = "%%MASK%%";
const CYCLE = %%CYCLE%%;
const STEP  = %%STEP%%;
let start = performance.now(), stop=false, raf;
const div  = document.getElementById('stim');

function flip(ts){
  if(stop) return;
  const e = ts - start,
        i = Math.floor(e/CYCLE),
        d = Math.min(STEP*(i+1), CYCLE);
  div.textContent = (e % CYCLE) < d ? WORD : MASK;
  raf = requestAnimationFrame(flip);
}
raf = requestAnimationFrame(flip);

function finish(){
  stop = true;
  cancelAnimationFrame(raf);
  div.remove();
  const rt = Math.round(performance.now()-start);
  const tgt = window.parent.document.getElementById('receiver');
  if(tgt){
      tgt.value = JSON.stringify({rt:rt});
      tgt.dispatchEvent(new Event('input',{bubbles:true}));
  }
}
document.addEventListener('keydown', e=>{
  if(e.code==='Space' || e.key===' ') finish();
});
</script>
"""

def show_js(word:str):
    html = (JS_RAW
            .replace("%%WORD%%", word)
            .replace("%%MASK%%", MASK_CH*len(word))
            .replace("%%CYCLE%%", str(CYCLE_MS))
            .replace("%%STEP%%",  str(STEP_MS)))
    cpn.html(html, height=400, scrolling=False)

# ---------- PAGES ------------------------------------------------------
def page_intro():
    st.title("Tâche de dévoilement progressif")
    st.write("1. Le mot apparaît peu à peu.\n"
             "2. Appuyez sur **Espace** dès que vous le reconnaissez.\n"
             "3. Tapez le mot et validez **Entrée**.")
    if st.button("Démarrer"):
        s.page, s.phase = "trial", "js"
        st.experimental_rerun()

def page_trial():
    # Fin d’expérience ?
    if s.idx >= len(WORDS):
        s.page = "end"; st.experimental_rerun(); return
    word = WORDS[s.idx]

    # 1) phase présentation ------------------------------------------------
    if s.phase == "js":
        show_js(word)
        if hidden.startswith("{"):
            s.rt   = json.loads(hidden)["rt"]
            s.receiver = ""                # purge
            s.phase = "typing"
            st.experimental_rerun()

    # 2) phase saisie ------------------------------------------------------
    elif s.phase == "typing":
        st.write(f"Temps de réaction : **{s.rt} ms**")
        answer = st.text_input("Votre réponse :", key=f"ans_{s.idx}")
        if answer:                         # Entrée pressée
            s.data.append(dict(stimulus=word,
                                response=answer.upper(),
                                correct=answer.upper()==word,
                                rt_ms=s.rt))
            del st.session_state[f"ans_{s.idx}"]  # retire le widget
            s.idx  += 1
            s.phase = "js"
            st.experimental_rerun()

def page_end():
    st.title("Merci !")
    df = pd.DataFrame(s.data)
    st.dataframe(df, use_container_width=True)
    st.download_button("💾 CSV", df.to_csv(index=False).encode(),
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")

# ---------- ROUTAGE ----------------------------------------------------
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
