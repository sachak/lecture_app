# -*- coding: utf-8 -*-
"""
Reconnaissance de mots masqués
– plein-écran permanent
– aucune barre de défilement
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ───────── CONFIG STREAMLIT ───────────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("page", "intro")
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)

# ───────── TIRAGE 80 MOTS (exemple rapide) ────────────────────────────
def tirer_80() -> list[str]:
    df = pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
    mots = df.ortho.astype(str).str.upper().unique().tolist()
    random.shuffle(mots)
    return mots[:80]

# ───────── HTML PHASES (mot → masque) ─────────────────────────────────
PHASE = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;width:100%;overflow:hidden;
display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:courier;font-size:60px}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head><body tabindex="0">
<div id="scr">+</div><input id="ans"/>
<script>
const WORDS=$WORDS, FLAG="$FLAG";
let i=0,scr=document.getElementById('scr'),ans=document.getElementById('ans');
function cycle(){
 if(i>=WORDS.length){parent.postMessage(FLAG,'*');return;}
 scr.textContent='+';setTimeout(()=>stim(WORDS[i++]),500);}
function stim(w){
 const m='#'.repeat(w.length);let sh=14,hd=336,act=true,t0=performance.now();
 (function loop(){
   if(!act)return;scr.textContent=w;
   setTimeout(()=>{if(!act)return;scr.textContent=m;
      setTimeout(()=>{if(act){sh+=14;hd=Math.max(0,350-sh);loop();}},hd);
   },sh);})();
 function onKey(e){
   if(e.code!=='Space'||!act)return;
   act=false;removeEventListener('keydown',onKey);
   const rt=Math.round(performance.now()-t0);
   scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
   ans.addEventListener('keydown',function ent(ev){
     if(ev.key==='Enter'){ev.preventDefault();
        ans.removeEventListener('keydown',ent);ans.style.display='none';
        parent.postMessage({w,rt,r:ans.value.trim()},'*');cycle();}});
 }
 addEventListener('keydown',onKey);}
cycle();
</script></body></html>""")

def phase_html(lst, flag): return PHASE.substitute(WORDS=json.dumps(lst), FLAG=flag)

# ───────── Fonction full-screen + no-scroll (injectée une fois) ────────
def inject_fullscreen_css():
    st.markdown("""
    <style>
      html,body,.block-container{padding:0;margin:0;height:100%;overflow:hidden}
    </style>
    <script>
      document.documentElement.requestFullscreen().catch(()=>{});
      /* bloque le scroll molette */
      addEventListener('wheel',e=>e.preventDefault(),{passive:false});
    </script>""", unsafe_allow_html=True)

# ─────────────────────────  PAGES  ─────────────────────────────────────
if ss.page == "intro":
    st.title("Test de reconnaissance de mots")
    st.write("Cliquez pour passer en plein-écran et démarrer.")
    if st.button("▶  Plein-écran et instructions"):
        inject_fullscreen_css()
        ss.page="instr"
        st.experimental_rerun()

elif ss.page == "instr":
    st.header("Instructions")
    st.write("Fixez la croix, pressez Espace quand le mot apparaît, "
             "retapez-le puis Entrée.")
    if st.button("▶  Démarrer la familiarisation"):
        ss.page="fam"; st.experimental_rerun()

elif ss.page == "fam":
    inject_fullscreen_css()
    components.v1.html(phase_html(["PAIN","EAU"], "FAM_DONE"),
                       height=9999, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{ if(e.data==='FAM_DONE')
   parent.location.search='fam=1';});
</script>""",height=0,width=0)

    if st.query_params.get("fam")=="1":
        st.query_params.clear(); ss.page="pre"; st.experimental_rerun()

elif ss.page == "pre":
    st.header("Familiarisation terminée")
    st.write("Cliquez pour commencer le test principal.")
    if st.button("▶  Commencer le test"):
        if not ss.tirage_ok:
            ss.stimuli=tirer_80(); ss.tirage_ok=True
        ss.page="test"; st.experimental_rerun()

elif ss.page == "test":
    inject_fullscreen_css()
    components.v1.html(phase_html(ss.stimuli, "FIN"),
                       height=9999, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FIN'){ parent.location.search='fin=1'; }});
</script>""",height=0,width=0)
    if st.query_params.get("fin")=="1":
        st.query_params.clear(); st.header("Merci ! Le test est terminé.")
