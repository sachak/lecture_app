# -*- coding: utf-8 -*-
"""
Reconnaissance de mots masqués  –  plein-écran permanent  –  contrôle 60 Hz
streamlit run exp3.py
"""

from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ───────────────────────────  CONFIG  ──────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)
ss = st.session_state
ss.setdefault("page", "intro")       # intro → instr → fam → pre → test → fin
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)
ss.setdefault("fs_pending", False)   # demande plein-écran à la prochaine page

# ─────────────────────  OUTILS  ────────────────────────────────────────
def tirer_80() -> list[str]:
    mots = (pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
              .ortho.astype(str).str.upper().unique().tolist())
    random.shuffle(mots)
    return mots[:80]

AUTO_SPACE = """<script>
addEventListener('keydown',e=>{
 if(e.code==='Space'){
     const b=parent.document.querySelector('button');
     if(b){e.preventDefault();b.click();}
 }});
</script>"""

PHASE_TPL = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:'Courier New',monospace;font-size:60px}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head><body tabindex="0"><div id="scr">+</div><input id="ans"/>
<script>
const WORDS=$WORDS, FLAG="$FLAG", C=350, STEP=14, START=14;
let i=0, scr=document.getElementById('scr'), ans=document.getElementById('ans');
function next(){
 if(i>=WORDS.length){parent.postMessage(FLAG,'*');return;}
 scr.textContent='+'; setTimeout(()=>show(WORDS[i++]),500);}
function show(w){
 const mask='#'.repeat(w.length);let sh=START,hd=C-sh,act=true,t0=performance.now();
 (function loop(){
   if(!act)return; scr.textContent=w;
   setTimeout(()=>{ if(!act)return; scr.textContent=mask;
       setTimeout(()=>{if(act){sh+=STEP;hd=Math.max(0,C-sh);loop();}},hd);
   },sh);})();
 function onSp(e){
   if(e.code==='Space'&&act){
     act=false;removeEventListener('keydown',onSp);
     const rt=Math.round(performance.now()-t0);
     scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
     ans.addEventListener('keydown',function ent(ev){
        if(ev.key==='Enter'){ev.preventDefault();
           ans.removeEventListener('keydown',ent);ans.style.display='none';
           parent.postMessage({word:w,rt:rt,resp:ans.value.trim()},'*');
           next();}});
 }} addEventListener('keydown',onSp);}
next();
</script></body></html>""")

def phase_html(words:list[str], flag:str)->str:
    return PHASE_TPL.substitute(WORDS=json.dumps(words), FLAG=flag)

# helper pour rerun
def R(): st.rerun() if hasattr(st,'rerun') else st.experimental_rerun()

# ─────────────────────  PAGE 1  ─────────────────────────────────────────
if ss.page=="intro":
    st.title("Bienvenue au test de reconnaissance de mots")
    st.write("""Un moniteur **60 Hz** est requis.
Cliquez (ou appuyez sur **Espace**) : la page passera en plein-écran et la
fréquence sera vérifiée automatiquement.""")
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)

    if st.button("▶  Passer en plein-écran et continuer"):
        ss.page="instr"
        ss.fs_pending=True
        R()

# ─────────────────────  PAGE 2  – INSTRUCTIONS  ────────────────────────
elif ss.page=="instr":
    if ss.fs_pending:                     # demande de plein-écran
        components.v1.html(
            "<script>parent.document.documentElement.requestFullscreen()"
            ".catch(()=>{});</script>", height=0,width=0)
        ss.fs_pending=False

    # script de contrôle 60 Hz (bandeau rouge si hors plage)
    components.v1.html("""
<script>
(function(){
 let t=[];function s(ts){t.push(ts);
  t.length<120?requestAnimationFrame(s):check();}
 function check(){
  const fps=1000/((t.slice(1).reduce((a,b,i)=>a+b-t[i],t[0]))/(t.length-1));
  if(fps<55||fps>65){
    const d=document.createElement('div');
    d.style='position:fixed;inset:0;background:#c00;color:#fff;font:48px Arial;\
             display:flex;align-items:center;justify-content:center;text-align:center';
    d.textContent='Fréquence détectée '+fps.toFixed(1)+' Hz\\nVeuillez basculer en 60 Hz.';
    document.body.appendChild(d);
  }}
 requestAnimationFrame(s);
})();</script>""",height=0,width=0)

    st.header("Instructions")
    st.markdown("""
Fixez la croix. Dès que vous reconnaissez le mot → **Espace**.  
Tapez ensuite le mot et validez avec **Entrée**.

Appuyez sur **Espace** (ou cliquez) pour démarrer la familiarisation.
""",unsafe_allow_html=True)
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)

    if st.button("▶  Démarrer la familiarisation"):
        ss.page="fam"; R()

# ─────────────────────  PAGE 3  – FAMILIARISATION  ──────────────────────
elif ss.page=="fam":
    components.v1.html(phase_html(["PAIN","EAU"], "FAM_DONE"),
                       height=650, scrolling=False)
    # écoute le flag
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FAM_DONE'){ parent.location.search='fam=1'; }});
</script>""",height=0,width=0)

    if st.query_params.get("fam")=="1":
        st.query_params.clear()
        ss.page="pre"; R()

# ─────────────────────  PAGE 4  – TRANSITION  ───────────────────────────
elif ss.page=="pre":
    st.header("Familiarisation terminée")
    st.write("Appuyez sur **Espace** pour commencer le test principal.")
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)

    if st.button("▶  Commencer le test principal"):
        if not ss.tirage_ok:
            ss.stimuli = tirer_80(); ss.tirage_ok=True
        ss.page="test"; R()

# ─────────────────────  PAGE 5  – TEST PRINCIPAL  ───────────────────────
elif ss.page=="test":
    if not ss.tirage_ok:
        ss.stimuli = tirer_80(); ss.tirage_ok=True
    components.v1.html(phase_html(ss.stimuli, "FIN_TEST"),
                       height=650, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FIN_TEST'){ parent.location.search='fin=1'; }});
</script>""",height=0,width=0)

    if st.query_params.get("fin")=="1":
        st.query_params.clear()
        st.header("Merci ! Le test est terminé.")
