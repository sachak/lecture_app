# -*- coding: utf-8 -*-
"""
Reconnaissance de mots masqués – plein-écran uniquement pour le test
streamlit run exp3.py
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ────────── CONFIG DE BASE ────────────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)
R = lambda: st.rerun()

ss = st.session_state
ss.setdefault("page", "intro")        # intro → instr → fam → pre → test → fin
ss.setdefault("stimuli", [])
ss.setdefault("tirage_ok", False)

# ────────── TIRAGE 80 MOTS (exemple simple) ───────────────────────────
def tirer_80() -> list[str]:
    df = pd.read_excel(Path(__file__).with_name("Lexique.xlsx"))
    mots = df.ortho.astype(str).str.upper().unique().tolist()
    random.shuffle(mots)
    return mots[:80]

# ────────── HTML FAMILIARISATION / TEST ───────────────────────────────
TPL = Template(r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;$EXTRA}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
body{display:flex;align-items:center;justify-content:center;
font-family:'Courier New',monospace;font-size:60px}
</style></head><body tabindex="0">
<div id="scr">+</div><input id="ans"/>
<script>
const W=$WORDS, FLAG="$FLAG", C=350, STEP=14, START=14;
let i=0, scr=document.getElementById('scr'), ans=document.getElementById('ans');
function n(){ if(i>=W.length){parent.postMessage(FLAG,'*');return;}
 scr.textContent='+';setTimeout(()=>s(W[i++]),500);}
function s(w){
 const m='#'.repeat(w.length);let sh=START,hd=C-sh,act=true,t0=performance.now();
 (function loop(){if(!act)return;scr.textContent=w;
   setTimeout(()=>{if(!act)return;scr.textContent=m;
        setTimeout(()=>{if(act){sh+=STEP;hd=Math.max(0,C-sh);loop();}},hd);
   },sh);})();
 function onSp(e){if(e.code!=='Space'||!act)return;
  act=false;removeEventListener('keydown',onSp);
  const rt=Math.round(performance.now()-t0);scr.textContent='';
  ans.style.display='block';ans.value='';ans.focus();
  ans.addEventListener('keydown',function ent(ev){
    if(ev.key==='Enter'){ev.preventDefault();
      ans.removeEventListener('keydown',ent);ans.style.display='none';
      parent.postMessage({w,rt,r:ans.value.trim()},'*');n();}});}
 addEventListener('keydown',onSp);}
n();
</script></body></html>""")

def phase_html(lst, flag, black=False):
    extra = "overflow:hidden;background:#000;color:#fff" if black else ""
    return TPL.substitute(WORDS=json.dumps(lst), FLAG=flag, EXTRA=extra)

# ────────── PAGES ────────────────────────────────────────────────────
if ss.page == "intro":
    st.title("Test de reconnaissance de mots (60 Hz)")
    st.write("Cliquez pour afficher les instructions.")
    if st.button("▶  Instructions"):
        ss.page="instr"; R()

# --------------------------------------------------------------------
elif ss.page == "instr":
    st.header("Instructions")
    st.markdown("""
Fixez la croix, appuyez sur **Espace** dès que le mot apparaît,
tapez-le puis **Entrée**.

Cliquez pour lancer la familiarisation (2 mots).
""")
    if st.button("▶  Familiarisation"):
        ss.page="fam"; R()

# --------------------------------------------------------------------
elif ss.page == "fam":
    components.v1.html(phase_html(["PAIN","EAU"], "FAM_FIN"),
                       height=500, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FAM_FIN'){ parent.location.search='step=pre'; }});
</script>""",height=0,width=0)
    if st.query_params.get("step") == "pre":
        st.query_params.clear()
        ss.page="pre"; R()

# --------------------------------------------------------------------
elif ss.page == "pre":
    st.header("Familiarisation terminée")
    st.write("Cliquez pour passer en plein-écran et démarrer le test principal.")
    if st.button("▶  Plein-écran + test principal"):
        ss.page="test"
        ss.fs_pending=True      # drapeau pour demander FS à la prochaine page
        if not ss.tirage_ok:
            ss.stimuli = tirer_80(); ss.tirage_ok=True
        R()

# --------------------------------------------------------------------
elif ss.page == "test":
    # demande plein-écran et blocage scroll une fois
    if ss.get("fs_pending", False):
        components.v1.html("""
<script>
document.documentElement.requestFullscreen().catch(()=>{});
document.addEventListener('wheel',e=>e.preventDefault(),{passive:false});
document.documentElement.style.overflow='hidden';
</script>""",height=0,width=0)
        ss.fs_pending=False
    components.v1.html(phase_html(ss.stimuli, "FIN", black=True),
                       height=9999, scrolling=False)
    components.v1.html("""
<script>
addEventListener('message',e=>{
 if(e.data==='FIN'){ parent.location.search='step=fin'; }});
</script>""",height=0,width=0)
    if st.query_params.get("step") == "fin":
        st.query_params.clear(); ss.page="fin"; R()

# --------------------------------------------------------------------
elif ss.page == "fin":
    st.header("Merci ! Le test est terminé.")
