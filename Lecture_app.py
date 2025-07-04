# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JS)
— La zone de réponse est ABSENTE tant que l’utilisateur n’a pas
  appuyé sur <Espace>, et elle disparaît juste après validation <Entrée>.
"""

import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as cpn

# ────────────────── Paramètres ─────────────────────────
CYCLE_MS, STEP_MS, MASK = 350, 14, "#"
WORDS = ["AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI",
         "NAGER","PARLE","PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE",
         "TABLE","TIGRE","VIVRE","VOILE"]
random.shuffle(WORDS)

# ────────────────── État session ───────────────────────
s = st.session_state
if "page" not in s:
    s.page   = "intro"           # intro ▸ trial ▸ end
    s.idx    = 0                 # mot courant
    s.phase  = "js"              # js ▸ typing
    s.rt_ms  = None
    s.data   = []
    s.ph     = st.empty()        # placeholder PERMANENT pour la zone réponse

# ────────────────── Champ caché JS→Py (invisible) ─────
st.markdown("<style>#receiver{display:none}</style>", unsafe_allow_html=True)
hidden = st.text_input("", key="receiver", label_visibility="collapsed")

# ────────────────── Gabarit JavaScript ─────────────────
JS_TPL = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>
<script>
const WORD ="{w}", MASK="{m}", CYCLE={c}, STEP={s};
let start=performance.now(), stop=false, raf,
    div=document.getElementById('stim');
function flip(ts){ if(stop) return;
  const e=ts-start,i=Math.floor(e/CYCLE),d=Math.min(STEP*(i+1),CYCLE);
  div.textContent=(e% CYCLE)<d?WORD:MASK;
  raf=requestAnimationFrame(flip);}
raf=requestAnimationFrame(flip);
function finish(){ stop=true; cancelAnimationFrame(raf); div.remove();
  const rt=Math.round(performance.now()-start);
  const tgt=window.parent.document.getElementById('receiver');
  if(tgt){ tgt.value=JSON.stringify({rt:rt});
           tgt.dispatchEvent(new Event('input',{bubbles:true}));}}
document.addEventListener('keydown',e=>{
  if(e.code==='Space'||e.key===' ') finish();});
</script>
"""
def show_js(word:str):
    html = JS_TPL.format(w=word, m=MASK*len(word),
                         c=CYCLE_MS, s=STEP_MS)
    cpn.html(html, height=400, scrolling=False)

# ────────────────── Pages ──────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.write("1. Le mot se dévoile progressivement.\n"
             "2. Appuyez sur **Espace** dès que vous le reconnaissez.\n"
             "3. Tapez le mot et validez avec **Entrée**.")
    if st.button("Démarrer"):
        s.page, s.phase = "trial", "js"
        st.experimental_rerun()

def page_trial():
    # Fin ?
    if s.idx >= len(WORDS):
        s.page = "end"; st.experimental_rerun(); return

    word = WORDS[s.idx]

    # -------- Phase js : mot/masque, pas de champ réponse -------
    if s.phase == "js":
        s.ph.empty()                 # garantie : aucune case visible
        show_js(word)
        if hidden.startswith("{"):
            s.rt_ms = json.loads(hidden)["rt"]
            s.receiver = ""          # reset
            s.phase = "typing"
            st.experimental_rerun()

    # -------- Phase typing : champ réponse visible --------------
    elif s.phase == "typing":
        st.write(f"RT : **{s.rt_ms} ms**")
        answer = s.ph.text_input("Votre réponse :", key=f"a_{s.idx}")
        if answer:                   # Entrée pressée
            s.data.append(dict(
                stimulus = word,
                response = answer.upper(),
                correct  = answer.upper() == word,
                rt_ms    = s.rt_ms))
            # suppression immédiate
            s.ph.empty()
            del st.session_state[f"a_{s.idx}"]
            s.idx  += 1
            s.phase = "js"
            st.experimental_rerun()

def page_end():
    st.title("Merci pour votre participation !")
    df = pd.DataFrame(s.data)
    st.dataframe(df, use_container_width=True)
    st.download_button("💾 Télécharger CSV",
                       df.to_csv(index=False).encode(),
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")

# ────────────────── Routage ────────────────────────────
{"intro": page_intro,
 "trial": page_trial,
 "end":   page_end}[s.page]()
