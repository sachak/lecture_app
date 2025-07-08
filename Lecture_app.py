# -*- coding: utf-8 -*-
"""
EXPÉRIENCE – Reconnaissance de mots masqués
(plein-écran permanent, contrôle 60 Hz)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ────────── STREAMLIT CONFIG ────────────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)
ss = st.session_state
ss.setdefault("page", "intro")
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)

# ────────── TIRAGE 80 MOTS (exemple simple) ─────────────────────────────
def tirer_80() -> list[str]:
    df = pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
    mots = df.ortho.astype(str).str.upper().unique().tolist()
    random.shuffle(mots)
    return mots[:80]

# ────────── JS : ESPACE = clic 1ᵉ bouton ────────────────────────────────
AUTO_SPACE = """
<script>
addEventListener('keydown',e=>{
 if(e.code==='Space'){
   const b=parent.document.querySelector('button');
   if(b){e.preventDefault();b.click();}
 }});
</script>"""

# ────────── HTML FAMILIARISATION / TEST ─────────────────────────────────
HTML_PHASE = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:courier;font-size:60px}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head><body tabindex="0"><div id="scr">+</div><input id="ans"/>
<script>
const WORDS=$WORDS,CYCLE=350,STEP=14,START=14;
let t=0,res=[],scr=document.getElementById('scr'),ans=document.getElementById('ans');
function go(){
 if(t>=WORDS.length){parent.postMessage('$FLAG','*');return;}
 scr.textContent='+'; setTimeout(()=>show(WORDS[t++]),500);
}
function show(w){
 let show=START,hide=CYCLE-show,mask='#'.repeat(w.length),t0=performance.now(),act=true;
 function loop(){
  if(!act)return; scr.textContent=w;
  setTimeout(()=>{if(!act)return;scr.textContent=mask;
     setTimeout(()=>{if(act){show+=STEP;hide=Math.max(0,CYCLE-show);loop();}},hide);
  },show);}
 loop();
 function onSp(e){
  if(e.code==='Space'&&act){
   act=false;removeEventListener('keydown',onSp);
   const rt=Math.round(performance.now()-t0);
   scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
   ans.addEventListener('keydown',function ent(ev){
     if(ev.key==='Enter'){ev.preventDefault();ans.removeEventListener('keydown',ent);
        ans.style.display='none';res.push({w,rt,r:ans.value.trim()});go();}});}}
 addEventListener('keydown',onSp);}
go();
</script></body></html>""")

def phase_html(liste, flag): return HTML_PHASE.substitute(WORDS=json.dumps(liste), FLAG=flag)

# ─────────────────── PAGE 1 – PLEIN-ÉCRAN + CHECK 60 Hz ─────────────────
if ss.page == "intro":
    st.title("Bienvenue au test de reconnaissance de mots")
    st.write("""
Cette expérience requiert un moniteur **60 Hz**.  
Cliquez (ou appuyez sur Espace) : la page passera en plein-écran puis la
fréquence sera mesurée automatiquement.
""")
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)

    if st.button("▶  Plein-écran + vérification 60 Hz"):
        components.v1.html("""
<script>
(async ()=>{
  await parent.document.documentElement.requestFullscreen().catch(()=>{});
  /* mesure fréquence */
  let t=[]; function s(ts){t.push(ts);
     t.length<120?requestAnimationFrame(s):
     verif(1000/((t.slice(1).reduce((a,b,i)=>a+b-t[i],t[0]))/(t.length-1))); }
  requestAnimationFrame(s);
  function verif(fps){
    if(fps<55||fps>65){
      parent.document.body.innerHTML='<h1 style="font-family:Arial;text-align:center">\
      Écran '+fps.toFixed(1)+' Hz – Veuillez passer à 60 Hz.</h1>';
    }else{ parent.location.search='ok=1'; }
  }
})();</script>""",height=0,width=0)

# si la vérification a réussi, l’URL porte ?ok=1
    if st.query_params.get("ok") == "1":
        st.query_params.clear()
        ss.page = "instr"
        rerun()

# ─────────────────── PAGE 2 – INSTRUCTIONS ─────────────────────────────
elif ss.page == "instr":
    st.header("Instructions")
    st.markdown("""
Fixez la croix, appuyez sur **Espace** dès que le mot apparaît, tapez-le
puis **Entrée**.

Appuyez sur **Espace** (ou cliquez) pour démarrer la familiarisation.""",
                unsafe_allow_html=True)
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)
    if st.button("▶  Démarrer la familiarisation"):
        ss.page="fam"; rerun()

# ─────────────────── PAGE 3 – FAMILIARISATION ──────────────────────────
elif ss.page == "fam":
    components.v1.html(phase_html(["PAIN","EAU"], "FIN_FAM"),
                       height=650, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FIN_FAM'){ parent.location.search='fam=ok'; }});
</script>""",height=0,width=0)

    if st.query_params.get("fam")=="ok":
        st.query_params.clear()
        ss.page="pretest"; rerun()

# ─────────────────── PAGE 4 – TRANSITION ───────────────────────────────
elif ss.page == "pretest":
    st.header("Familiarisation terminée")
    st.write("Appuyez sur **Espace** pour commencer le test principal.")
    st.markdown(AUTO_SPACE, unsafe_allow_html=True)
    if st.button("▶  Commencer le test principal"):
        if not ss.tirage_ok:
            ss.stimuli = tirer_80(); ss.tirage_ok=True
        ss.page="test"; rerun()

# ─────────────────── PAGE 5 – TEST PRINCIPAL ───────────────────────────
elif ss.page == "test":
    if not ss.tirage_ok: ss.stimuli = tirer_80(); ss.tirage_ok=True
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
