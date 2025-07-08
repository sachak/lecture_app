# -*- coding: utf-8 -*-
"""
Reconnaissance de mots masqués
Plein-écran permanent – aucune barre de scroll
streamlit run exp3.py
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template

import pandas as pd
import streamlit as st
from streamlit import components

# ─────────────────────── CONFIG GÉNÉRALE ───────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

PAGES = ["intro", "instr", "fam", "pre", "test", "fin"]
ss = st.session_state
ss.setdefault("page", "intro")
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)

def R(): st.rerun()            # raccourci rerun

# ────────────────────────── OUTILS ──────────────────────────────────────
def tirer_80() -> list[str]:
    mots = (pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
              .ortho.astype(str).str.upper().unique().tolist())
    random.shuffle(mots)
    return mots[:80]

# plein-écran + blocage scroll : injecté une fois et pour toujours
FULLSCREEN_JS = """
<script>
(async ()=>{
  try{await document.documentElement.requestFullscreen();}catch(e){}
  /* désactive la molette */
  addEventListener('wheel',e=>e.preventDefault(),{passive:false});
  /* cache scrollbars résiduelles */
  const css=document.createElement('style');
  css.textContent='html,body,.block-container{height:100%;overflow:hidden;padding:0;margin:0}';
  document.head.appendChild(css);
  /* signale au parent que le FS est lancé */
  parent.postMessage('fs_ok','*');
})();
</script>"""

# HTML (fam + test) ------------------------------------------------------
PHASE_TPL = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;overflow:hidden;
display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:'Courier New',monospace;font-size:60px}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head><body tabindex="0">
<div id="scr">+</div><input id="ans"/>
<script>
const WORDS=$WORDS, FLAG="$FLAG",
      CYCLE=350, STEP=14, START=14;
let i=0, scr=document.getElementById('scr'),
    ans=document.getElementById('ans');

function next(){
 if(i>=WORDS.length){ parent.postMessage(FLAG,'*'); return; }
 scr.textContent='+'; setTimeout(()=>stim(WORDS[i++]),500);
}
function stim(w){
 const mask='#'.repeat(w.length);
 let sh=START, hd=CYCLE-sh, act=true, t0=performance.now();
 (function loop(){
  if(!act)return; scr.textContent=w;
  setTimeout(()=>{ if(!act)return; scr.textContent=mask;
      setTimeout(()=>{ if(act){sh+=STEP;hd=Math.max(0,CYCLE-sh);loop();}},hd);
  }, sh);})();
 function onSp(e){
  if(e.code!=='Space'||!act) return;
  act=false; removeEventListener('keydown',onSp);
  const rt=Math.round(performance.now()-t0);
  scr.textContent=''; ans.style.display='block'; ans.value=''; ans.focus();
  ans.addEventListener('keydown',function onEnt(ev){
     if(ev.key==='Enter'){
        ev.preventDefault();
        ans.removeEventListener('keydown',onEnt);
        ans.style.display='none';
        parent.postMessage({w,rt,r:ans.value.trim()},'*');
        next();
  }});}
 addEventListener('keydown',onSp);
}
next();
</script></body></html>""")

def phase_html(words:list[str], flag:str)->str:
    return PHASE_TPL.substitute(WORDS=json.dumps(words), FLAG=flag)

# ──────────────────────── ROUTAGE  ──────────────────────────────────────
flag = st.query_params.get("flag", "")
if flag and flag in PAGES and flag != ss.page:
    ss.page = flag
    st.query_params.clear()

# ─────────────────────── PAGE intro ─────────────────────────────────────
if ss.page == "intro":
    st.title("Test de reconnaissance de mots (60 Hz)")
    st.write("Cliquez pour passer en plein-écran, puis lisez les instructions.")
    if st.button("▶  Activer le plein-écran"):
        # injecte JS plein-écran et attend le message 'fs_ok'
        components.v1.html(FULLSCREEN_JS, height=0, width=0)
        components.v1.html("""
<script>
addEventListener('message',e=>{
  if(e.data==='fs_ok'){ parent.location.search='flag=instr'; }});
</script>""", height=0, width=0)

# ─────────────────────── PAGE instructions ──────────────────────────────
elif ss.page == "instr":
    st.header("Instructions")
    st.write("Fixez la croix, appuyez sur Space dès que le mot apparaît, "
             "tapez-le, puis Entrée.")
    if st.button("▶  Démarrer la familiarisation (2 mots)"):
        ss.page = "fam"; R()

# ─────────────────────── PAGE familiarisation ───────────────────────────
elif ss.page == "fam":
    components.v1.html(phase_html(["PAIN","EAU"], "pre"),
                       height=9999, scrolling=False)

# ─────────────────────── PAGE transition ───────────────────────────────
elif ss.page == "pre":
    st.header("Familiarisation terminée")
    if st.button("▶  Commencer le test principal (80 mots)"):
        if not ss.tirage_ok:
            ss.stimuli = tirer_80(); ss.tirage_ok = True
        ss.page = "test"; R()

# ─────────────────────── PAGE test principal ────────────────────────────
elif ss.page == "test":
    components.v1.html(phase_html(ss.stimuli, "fin"),
                       height=9999, scrolling=False)

# ─────────────────────── PAGE fin ───────────────────────────────────────
elif ss.page == "fin":
    st.header("Merci ! Le test est terminé.")
