# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JS)
– Le champ de réponse n’existe qu’entre Espace et Entrée.
"""

import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as cpn

# ───────────────── PARAMÈTRES ─────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK = 350, 14, "#"
WORDS = ["AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI",
         "NAGER","PARLE","PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE",
         "TABLE","TIGRE","VIVRE","VOILE"]
random.shuffle(WORDS)

# ───────────────── ÉTAT SESSION ───────────────────────────────────────
s = st.session_state
if "stage" not in s:
    s.stage, s.idx, s.phase = "intro", 0, "js"   # phases : js ▸ typing
    s.rt = None
    s.data = []

# ───────────────── CHAMP CACHÉ (dans la sidebar, hors vue) ────────────
st.sidebar.text_input("", key="receiver", label_visibility="collapsed")

# ───────────────── GABARIT JS (aucune accolade interprétée) ───────────
RAW_JS = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>
<script>
const WORD ="%%W%%", MASK="%%M%%", CYCLE=%%C%%, STEP=%%S%%;
let start=performance.now(), stop=false, raf, div=document.getElementById('stim');
function flip(ts){ if(stop) return;
  const e=ts-start,i=Math.floor(e/CYCLE),d=Math.min(STEP*(i+1),CYCLE);
  div.textContent=(e% CYCLE)<d?WORD:MASK; raf=requestAnimationFrame(flip);}
raf=requestAnimationFrame(flip);
function finish(){ stop=true; cancelAnimationFrame(raf); div.remove();
  const rt=Math.round(performance.now()-start);
  const tgt=window.parent.document.querySelector('input[id="receiver"]');
  if(tgt){ tgt.value=JSON.stringify({rt:rt});
           tgt.dispatchEvent(new Event('input',{bubbles:true}));}}
document.addEventListener('keydown',e=>{
  if(e.code==='Space'||e.key===' ') finish();});
</script>
"""
def show_js(word):
    html=(RAW_JS.replace("%%W%%",word)
                .replace("%%M%%",MASK*len(word))
                .replace("%%C%%",str(CYCLE_MS))
                .replace("%%S%%",str(STEP_MS)))
    cpn.html(html,height=400,scrolling=False)

# ───────────────── CALLBACK Après Entrée ──────────────────────────────
def validated():
    s.validated = True

# ───────────────── PAGES ───────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.write("1. Le mot se dévoile progressivement.\n"
             "2. Appuyez sur **Espace** dès que vous l’avez reconnu.\n"
             "3. Tapez le mot, validez avec **Entrée**.")
    if st.button("Démarrer"): s.stage="trial"; st.experimental_rerun()

def page_trial():
    if s.idx>=len(WORDS):
        s.stage="end"; st.experimental_rerun(); return
    word=WORDS[s.idx]

    # PHASE JS (pas de champ réponse)
    if s.phase=="js":
        show_js(word)
        if s.receiver.startswith("{"):
            s.rt=json.loads(s.receiver)["rt"]
            s.receiver=""
            s.phase="typing"
            st.experimental_rerun()

    # PHASE TYPING (champ réponse visible)
    elif s.phase=="typing":
        st.write(f"RT: **{s.rt} ms**")
        answer=st.text_input("Votre réponse :", key=f"a_{s.idx}",
                             on_change=validated)
        if getattr(s,"validated",False):
            s.validated=False
            s.data.append(dict(stimulus=word,
                               response=answer.upper(),
                               correct=answer.upper()==word,
                               rt_ms=s.rt))
            # suppression du champ
            del st.session_state[f"a_{s.idx}"]
            s.idx+=1; s.phase="js"
            st.experimental_rerun()

def page_end():
    st.title("Merci !")
    df=pd.DataFrame(s.data)
    st.dataframe(df,use_container_width=True)
    st.download_button("💾 CSV",df.to_csv(index=False).encode(),
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")

# ───────────────── ROUTAGE ────────────────────────────────────────────
{"intro":page_intro,"trial":page_trial,"end":page_end}[s.stage]()
