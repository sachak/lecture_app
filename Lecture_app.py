# -*- coding: utf-8 -*-
"""
EXPERIENCE  –  Reconnaissance de mots
Navigation : 100 % plein-écran  (écran 60 Hz)
Pilotage : clic unique au départ, puis touche Espace
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template

import pandas as pd
import streamlit as st
from streamlit import components

# ─────────────────────────── CONFIG ──────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

rerun = lambda: (st.rerun if hasattr(st, "rerun")
                 else st.experimental_rerun)()

# ──────────────────────── ÉTAT SESSION ───────────────────────────────────
ss = st.session_state
ss.setdefault("page",       "intro")     # intro → instr → fam → pretest → test
ss.setdefault("tirage_ok",  False)
ss.setdefault("stimuli",    [])

# ──────────────────── FONCTION TIRAGE 80 MOTS ────────────────────────────
def tirer_80() -> list[str]:
    xlsx = Path(__file__).with_name("Lexique.xlsx")
    mots = (pd.read_excel(xlsx)
              .ortho.astype(str).str.upper().unique().tolist())
    random.shuffle(mots)
    return mots[:80]

# ───────────────────── SCRIPT « ESPACE = CLIC » ──────────────────────────
auto_space = """<script>
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){
      const b=parent.document.querySelector('button');
      if(b){e.preventDefault();b.click();}
  }});
</script>"""

# ─────────────────────── TEMPLATE HTML PHASES ────────────────────────────
HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:'Courier New',monospace;font-size:60px}
</style></head><body tabindex="0"><div id="scr">+</div>
<script>
const WORDS = $WORDS;
let idx = 0, scr = document.getElementById('scr');
function next(){
  if(idx >= WORDS.length){ parent.postMessage('$END','*'); return;}
  scr.textContent = '+'; setTimeout(()=>scr.textContent = WORDS[idx++],500);
}
next();
addEventListener('keydown',e=>e.code==='Space'&&next());
</script></body></html>""")

def phase_html(liste, end_flag):
    return HTML_TPL.substitute(WORDS=json.dumps(liste), END=end_flag)

# ────────────────────────── PAGE 1  (clic) ───────────────────────────────
if ss.page == "intro":
    st.title("Bienvenue au test de reconnaissance de mots")
    st.write("""
Écran **60 Hz** recommandé.  
Cliquez sur le bouton pour passer en <b>plein-écran</b>.  
(ESC ou F11 quitteront le plein-écran si nécessaire.)""",
             unsafe_allow_html=True)

    if st.button("▶  Activer le plein-écran et continuer"):
        # déclenche le plein-écran
        components.html(
            "<script>parent.document.documentElement.requestFullscreen()\
                   .catch(()=>{});</script>",
            height=0, width=0)
        ss.page = "instr"
        rerun()

# ────────────────────────── PAGE 2  (Espace) ─────────────────────────────
elif ss.page == "instr":
    st.header("Instructions")
    st.markdown("""
1. Fixez la croix « + ».  
2. Dès que vous reconnaissez le mot, <b>appuyez sur Espace</b>.  
3. Tapez le mot lu et validez.  

Quand vous êtes prêt·e :  
<b>appuyez sur Espace</b> ou cliquez sur le bouton.""",
                unsafe_allow_html=True)
    st.markdown(auto_space, unsafe_allow_html=True)

    if not ss.tirage_ok:
        ss.stimuli   = tirer_80()
        ss.tirage_ok = True

    if st.button("▶  Démarrer la familiarisation"):
        ss.page = "fam"
        rerun()

# ────────────────────────── PAGE 3  (familiarisation) ────────────────────
elif ss.page == "fam":
    components.html(
        phase_html(["PAIN","EAU"], "FAM_DONE"),
        height=650, scrolling=False)

    # Réception du message « FAM_DONE »
    components.html("""
<script>
addEventListener('message',e=>{
   if(e.data==='FAM_DONE'){
      parent.location.search='step=fam';
   }});</script>""", height=0, width=0)

    if st.query_params.get("step") == "fam":
        st.query_params.clear()
        ss.page = "pretest"
        rerun()

# ────────────────────────── PAGE 4  (transition) ─────────────────────────
elif ss.page == "pretest":
    st.header("Familiarisation terminée")
    st.write("Appuyez sur **Espace** pour commencer le test principal "
             "ou cliquez.")
    st.markdown(auto_space, unsafe_allow_html=True)

    if st.button("▶  Commencer le test principal"):
        ss.page = "test"
        rerun()

# ────────────────────────── PAGE 5  (test) ───────────────────────────────
elif ss.page == "test":
    components.html(
        phase_html(ss.stimuli, "FIN"), height=650, scrolling=False)

    components.html("""
<script>
addEventListener('message',e=>{
   if(e.data==='FIN'){ parent.location.search='step=fin'; }});</script>""",
        height=0, width=0)

    if st.query_params.get("step") == "fin":
        st.query_params.clear()
        st.header("Merci ! Le test est terminé.")
