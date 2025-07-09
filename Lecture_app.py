# -*- coding: utf-8 -*-
"""
Test 60 Hz + bouton « Suivant » ZÉRO-SCROLL (tout centré)
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

# ────────────────── Mise en page 100 vh ──────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp{height:100vh;margin:0;overflow:hidden;}

main.block-container{
    height:100vh;
    display:grid;
    grid-template-rows:auto 1fr auto;          /* titre – i-frame – bouton */
    justify-items:center;                      /* centres colonne          */
    align-items:center;                        /* centres chaque ligne     */
    row-gap:0;
    padding:0;
}

/* suppression des marges/paddings par défaut */
section,div,article,header,footer{margin:0;padding:0;}
h3{margin:0; font-size:clamp(18px,3.5vmin,32px);}
button.stButton>button{width:240px; font-size:clamp(14px,2.8vmin,22px);}
#MainMenu,header,footer{visibility:hidden;}
</style>""", unsafe_allow_html=True)

# ────────────────── mini routeur ─────────────────────────────────────────
st.session_state.setdefault("page","test")
def go(pg): st.session_state.page=pg; st.rerun()

# ────────────────── HTML de l’i-frame (test) ─────────────────────────────
TEST_HTML=r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
          display:flex;flex-direction:column;justify-content:center;
          align-items:center;text-align:center;box-sizing:border-box}
h2{font-size:6vh;margin:0 0 4vh}
#res{font-size:8vh;margin:4vh 0}
button{font-size:4vh;padding:1vh 4vh}
</style></head><body>
<h2>Test&nbsp;de&nbsp;fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>

<script>
function send(v){
  if(window.Streamlit?.setComponentValue){Streamlit.setComponentValue(v);}
  else{parent.postMessage({isStreamlitMessage:true,
        type:"streamlit:componentValue",value:v},"*");}
}

/* occupe 100 % de la 2ᵉ ligne (1 fr) */
function resize(){
  const h=document.documentElement.clientHeight;
  if(window.Streamlit?.setFrameHeight){Streamlit.setFrameHeight(h);}
  else{parent.postMessage({isStreamlitMessage:true,
        type:"streamlit:setFrameHeight",height:h},"*");}
}
addEventListener("load",resize); addEventListener("resize",resize);

function mesure(){
  const res=document.getElementById('res'),b=document.getElementById('go');
  b.disabled=true;res.textContent='Mesure en cours…';res.style.color='#fff';
  let f=0,t0=performance.now();
  (function loop(){
    f++; if(f<120){requestAnimationFrame(loop);}else{
      const hz=f*1000/(performance.now()-t0);
      res.textContent='≈ '+hz.toFixed(1)+' Hz';
      res.style.color=Math.abs(hz-60)<1.5?'lime':'red';
      send(hz.toFixed(1)); b.disabled=false;
  }})();
}
</script></body></html>
"""

# ────────────────── PAGE 0 : test + bouton ───────────────────────────────
if st.session_state.page=="test":

    st.markdown("<h3>1.&nbsp;Vérification (facultative) de la fréquence d’écran</h3>",
                unsafe_allow_html=True)

    # ligne i-frame (row 2) : hauteur initiale 500 px, remplacée ensuite
    _ = components.html(TEST_HTML, height=500, scrolling=False)

    # ligne bouton (row 3)
    if st.button("Suivant ➜"): go("intro")

# ────────────────── PAGE Intro (démo) ────────────────────────────────────
elif st.session_state.page=="intro":
    st.markdown("<h3>Page Intro (aucun scroll)</h3>", unsafe_allow_html=True)
    if st.button("Fin"): go("fin")

elif st.session_state.page=="fin":
    st.markdown("<h2>Fin de la démo ✅</h2>", unsafe_allow_html=True)
