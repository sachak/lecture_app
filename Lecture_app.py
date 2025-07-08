# -*- coding: utf-8 -*-
"""
EXPERIENCE – Reconnaissance de mots
Navigation 100 % plein-écran (60 Hz)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ───────────── CONFIG GÉNÉRALE ──────────────────────────────────────────
st.set_page_config(page_title="Reconnaissance de mots", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)
rerun = lambda: (st.rerun if hasattr(st,"rerun") else st.experimental_rerun)()

# ───────────── ETAT SESSION ─────────────────────────────────────────────
ss = st.session_state
for k,v in {"page":"intro","tirage_ok":False,
            "stimuli":[], "fam_done":False}.items():
    ss.setdefault(k,v)

# -----------------------------------------------------------------------
# PETIT SCRIPT « Espace → clic sur 1ᵉ bouton »
auto_space = """<script>
document.addEventListener('keydown',e=>{
 if(e.code==='Space'){const b=document.querySelector('button');
   if(b){e.preventDefault();b.click();}}
});
</script>"""

# -----------------------------------------------------------------------
# CHARGEMENT & TIRAGE DES 80 MOTS (exemple simplifié)
def tirer_80() -> list[str]:
    xlsx = Path(__file__).with_name("Lexique.xlsx")
    df   = pd.read_excel(xlsx)
    mots = df.ortho.astype(str).str.upper().unique().tolist()
    random.shuffle(mots)
    return mots[:80]

# -----------------------------------------------------------------------
# HTML/JS COMMUN AUX PHASES FAMILIARISATION & TEST
HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;display:flex;flex-direction:column;
align-items:center;justify-content:center;background:#000;color:#fff;
font-family:'Courier New',monospace;font-size:60px}
</style></head>
<body tabindex="0"><div id="scr">+</div>
<script>
const WORDS = $WORDS;
let i=0; const scr=document.getElementById('scr');
function next(){
  if(i>=WORDS.length){parent.postMessage('$END','*'); return;}
  scr.textContent = '+';           // croix 500 ms
  setTimeout(()=>scr.textContent=WORDS[i++],500);
}
next();
document.addEventListener('keydown',e=>{
  if(e.code==='Space') next();
});
</script></body></html>""")

def phase_html(liste, end_msg):
    return HTML_TPL.substitute(WORDS=json.dumps(liste), END=end_msg)

# -----------------------------------------------------------------------
# PAGE 1 ─────────────  CLIC → plein-écran
if ss.page=="intro":
    st.title("Bienvenue au test de reconnaissance de mots")
    st.write("""
Écran 60 Hz recommandé.  
Cliquez sur le bouton ci-dessous ; la page passera en **plein-écran** et
vous n’en sortirez plus jusqu’à la fin du test.
(ESC ou F11 restent disponibles si vous deviez quitter.)
""")
    if st.button("▶ Cliquer : activer le plein-écran"):
        # demande plein-écran
        components.v1.html("""
        <script>
        document.documentElement.requestFullscreen().catch(()=>{});
        </script>""",height=0, width=0)
        ss.page="instr"; rerun()

# -----------------------------------------------------------------------
# PAGE 2 ─────────────  instructions → ESPACE
elif ss.page=="instr":
    st.header("Instructions")
    st.markdown("""
1. Vous verrez une croix « + » puis un mot très bref.  
2. Appuyez sur **Espace** dès que vous lisez le mot.  
3. Retapez-le au clavier, validez.  

Appuyez maintenant sur **Espace** pour démarrer la familiarisation
(ou cliquez sur le bouton).
""")
    st.markdown(auto_space, unsafe_allow_html=True)

    if not ss.tirage_ok:           # tirage unique
        ss.stimuli = tirer_80()
        ss.tirage_ok=True

    if st.button("▶ Commencer la familiarisation"):
        ss.page="fam"; rerun()

# -----------------------------------------------------------------------
# PAGE 3 ─────────────  FAMILIARISATION  (iframe plein-écran)
elif ss.page=="fam":
    components.v1.html(
        phase_html(["PAIN","EAU"], "FAM_DONE"),
        height=650, scrolling=False)

    # écoute message « FAM_DONE »
    components.v1.html("""
<script>
window.addEventListener('message',e=>{
  if(e.data==='FAM_DONE'){
     parent.location.search='step=fam_done';
  }
});
</script>""", height=0, width=0)

    if st.experimental_get_query_params().get("step")==["fam_done"]:
        ss.page="pretest"; st.experimental_set_query_params(); rerun()

# -----------------------------------------------------------------------
# PAGE 4 ─────────────  transition → ESPACE
elif ss.page=="pretest":
    st.header("Familiarisation terminée")
    st.write("Appuyez sur **Espace** pour lancer le test principal "
             "(ou cliquez).")
    st.markdown(auto_space, unsafe_allow_html=True)

    if st.button("▶ Commencer le test principal"):
        ss.page="test"; rerun()

# -----------------------------------------------------------------------
# PAGE 5 ─────────────  TEST PRINCIPAL  (iframe plein-écran)
elif ss.page=="test":
    components.v1.html(
        phase_html(ss.stimuli, "FIN"),
        height=650, scrolling=False)

    components.v1.html("""
<script>
window.addEventListener('message',e=>{
  if(e.data==='FIN'){
     parent.location.search='step=fin';
  }
});
</script>""", height=0, width=0)

    if st.experimental_get_query_params().get("step")==["fin"]:
        st.header("Merci ! Le test est terminé.")
