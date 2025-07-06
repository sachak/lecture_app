# -*- coding: utf-8 -*-
# =============================================================
#  Lecture_app.py  –  version minimale 100 % fonctionnelle
# =============================================================
import json, random, threading, time, pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from get_stimuli import get_stimuli          # ← ta fonction de tirage

# ---------- CONFIG ------------------------------------------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

# ---------- LEXIQUE pour 3 essais d’entraînement ------------------------
@st.cache_data
def lex3():
    df = pd.read_csv("Lexique383.csv", sep=";", decimal=".", encoding="utf-8",
                     usecols=["ortho"])
    df.ortho = df.ortho.str.upper()
    return random.sample([w for w in df.ortho if len(w) == 3], 3)
TRAIN_WORDS = lex3()

# ---------- LANCER la sélection en tâche de fond ------------------------
def _select():
    try:
        st.session_state["stimuli"] = get_stimuli()
        st.session_state["ready"]   = True
    except Exception as e:
        st.session_state["error"]   = str(e)
    finally:
        try: st.experimental_rerun()
        except st.runtime.scriptrunner.StopException: pass

if "ready" not in st.session_state:
    st.session_state.update(dict(page="intro", idx=0, ready=False, error=None))
    threading.Thread(target=_select, daemon=True).start()

# ========================================================================
#  NAVIGATION
# ========================================================================
pg = st.session_state.page

# -------- INTRO ---------------------------------------------------------
if pg == "intro":
    st.title("Expérience 3 — instructions")
    st.write("Appuyez sur **Espace** dès que le mot apparaît ; retapez-le puis "
             "validez avec **Entrée**. 3 essais d’entraînement vont suivre.")
    if st.button("Je suis prêt·e"):
        st.session_state.page = "train"
        st.experimental_rerun()

# -------- ENTRAÎNEMENT --------------------------------------------------
elif pg == "train":
    i = st.session_state.idx
    if i >= 3:
        st.session_state.page = "wait"
        st.experimental_rerun()
    else:
        st.subheader(f"Essai d’entraînement {i+1}/3")
        st.write("Mot cible :", TRAIN_WORDS[i])
        if st.button("Valider (fictif)"):
            st.session_state.idx += 1
            st.experimental_rerun()

# -------- ATTENTE -------------------------------------------------------
elif pg == "wait":
    if st.session_state.get("ready"):
        st.session_state.page = "exp"
        st.experimental_rerun()
    elif st.session_state.get("error"):
        st.error("Erreur lors du tirage :\n\n" + st.session_state["error"])
    else:
        st.info("Préparation des 80 mots… merci de patienter.")
        st.progress(None)
        time.sleep(2)
        st.experimental_rerun()

# -------- EXPÉRIENCE RÉELLE --------------------------------------------
elif pg == "exp":
    words_json = json.dumps(st.session_state["stimuli"])
    html = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
html,body{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body id="body" tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());

const W=__WORDS__,C=350,S=14,P=14;
let i=0,res=[];
const scr=document.getElementById('scr'), ans=document.getElementById('ans');

function run(){ if(i>=W.length){ fin();return; }
  const w=W[i],m='#'.repeat(w.length);
  let sd=S,md=C-sd,t0=performance.now(),on=true,t1,t2;
  (function loop(){ if(!on)return;
    scr.textContent=w;
    t1=setTimeout(()=>{ if(!on)return;
       scr.textContent=m;
       t2=setTimeout(()=>{ if(on){ sd+=P;md=Math.max(0,C-sd);loop(); } },md);
    },sd);
  })();
  window.addEventListener('keydown',function sp(e){ if(e.code==='Space'&&on){ 
        on=false;clearTimeout(t1);clearTimeout(t2);
        const rt=Math.round(performance.now()-t0);
        window.removeEventListener('keydown',sp);
        scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
        ans.addEventListener('keydown',function ent(ev){ if(ev.key==='Enter'){ 
           ev.preventDefault();
           res.push({word:w,rt_ms:rt,response:ans.value.trim()});
           ans.removeEventListener('keydown',ent);
           ans.style.display='none';i++;run();
        }});
  }});
}

function fin(){
  scr.style.fontSize='40px';
  scr.textContent='Merci !';
  const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='results.csv';
  a.textContent='Télécharger les résultats';
  a.style.fontSize='32px';a.style.marginTop='30px';
  document.body.appendChild(a);
}
run();
</script></body></html>
"""
    html = html.replace("__WORDS__", words_json)
    components.html(html, height=650, scrolling=False)
