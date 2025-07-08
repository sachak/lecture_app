# -*- coding: utf-8 -*-
"""
Reconnaissance de mots masqués
• plein-écran permanent
• aucune barre de défilement / aucun scroll
"""

from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ───────────── CONFIG DE BASE ──────────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

# raccourci pour relancer le script
R = lambda: st.rerun()

# ───────────── ÉTAT SESSION ────────────────────────────────────────────
ss = st.session_state
ss.setdefault("page", "intro")      # intro → instr → fam → pre → test → fin
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)

# ───────────── TIRAGE 80 MOTS (exemple rapide) ────────────────────────
def tirer_80() -> list[str]:
    df = pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
    mots = df.ortho.astype(str).str.upper().unique().tolist()
    random.shuffle(mots)
    return mots[:80]

# ───────────── HTML / JS  des phases (fam + test) ─────────────────────
TPL = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;width:100%;overflow:hidden;display:flex;
align-items:center;justify-content:center;background:#000;color:#fff;
font-family:'Courier New',monospace;font-size:60px}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head><body tabindex="0">
<div id="scr">+</div><input id="ans"/>
<script>
const LIST=$WORDS,FLAG="$FLAG",CYCLE=350,STEP=14,START=14;
let i=0,scr=document.getElementById('scr'),ans=document.getElementById('ans');
function next(){ if(i>=LIST.length){parent.postMessage(FLAG,'*');return;}
 scr.textContent='+';setTimeout(()=>stim(LIST[i++]),500);}
function stim(w){
 const mask='#'.repeat(w.length);let sh=START,hd=CYCLE-sh,act=true,t0=performance.now();
 (function loop(){
   if(!act)return;scr.textContent=w;
   setTimeout(()=>{if(!act)return;scr.textContent=mask;
       setTimeout(()=>{if(act){sh+=STEP;hd=Math.max(0,CYCLE-sh);loop();}},hd);
   },sh);})();
 function onSp(e){
   if(e.code==='Space'&&act){
     act=false;removeEventListener('keydown',onSp);
     const rt=Math.round(performance.now()-t0);
     scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
     ans.addEventListener('keydown',function onEnt(ev){
       if(ev.key==='Enter'){ev.preventDefault();
         ans.removeEventListener('keydown',onEnt);ans.style.display='none';
         parent.postMessage({w,rt,r:ans.value.trim()},'*');next();}});
 }}
 addEventListener('keydown',onSp);}
next();
</script></body></html>""")

def phase_html(lst, flag): return TPL.substitute(WORDS=json.dumps(lst), FLAG=flag)

# ───────────── CSS + JS pour plein-écran et blocage scroll ─────────────
def full_screen_setup():
    st.markdown("""
<style>
html,body,.block-container{margin:0;padding:0;height:100%;overflow:hidden}
</style>
<script>
document.documentElement.requestFullscreen().catch(()=>{});
addEventListener('wheel',e=>e.preventDefault(),{passive:false});
</script>""", unsafe_allow_html=True)

# ───────────────────  PAGES  ───────────────────────────────────────────
# PAGE 1 ----------------------------------------------------------------
if ss.page == "intro":
    st.title("Test de reconnaissance de mots")
    st.write("Cliquez pour passer en plein-écran puis lire les instructions.")
    if st.button("▶  Plein-écran + instructions"):
        full_screen_setup()
        ss.page = "instr"
        R()

# PAGE 2 ----------------------------------------------------------------
elif ss.page == "instr":
    st.header("Instructions")
    st.write(
        "Fixez la croix, appuyez sur Espace dès que le mot apparaît, "
        "retapez-le, validez avec Entrée."
    )
    if st.button("▶  Démarrer la familiarisation (2 mots)"):
        ss.page = "fam"
        R()

# PAGE 3 ----------------------------------------------------------------
elif ss.page == "fam":
    full_screen_setup()
    components.v1.html(phase_html(["PAIN","EAU"], "FAM_OK"),
                       height=9999, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FAM_OK'){ parent.location.search='fam=1'; }});
</script>""",height=0,width=0)
    if st.query_params.get("fam")=="1":
        st.query_params.clear(); ss.page="pre"; R()

# PAGE 4 ----------------------------------------------------------------
elif ss.page == "pre":
    st.header("Familiarisation terminée")
    if st.button("▶  Commencer le test principal (80 mots)"):
        if not ss.tirage_ok:
            ss.stimuli = tirer_80(); ss.tirage_ok=True
        ss.page = "test"; R()

# PAGE 5 ----------------------------------------------------------------
elif ss.page == "test":
    full_screen_setup()
    components.v1.html(phase_html(ss.stimuli, "FIN"),
                       height=9999, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FIN'){ parent.location.search='fin=1'; }});
</script>""",height=0,width=0)
    if st.query_params.get("fin")=="1":
        st.query_params.clear()
        st.header("Merci ! Le test est terminé.")
