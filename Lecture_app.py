# -*- coding: utf-8 -*-
"""
Expérience 3 – test 60 Hz plein-écran, bouton « Suivant » séparé,
AUCUN scroll possible (layout CSS grid 100 vh).
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

# ═══ 1) Configuration plein-écran et layout grid ═════════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
      /* Tout le viewport, et on masque les barres de scroll éventuelles */
      html,body,.stApp {height:100vh; margin:0; overflow:hidden;}

      /* Grille : ligne titre – ligne i-frame (flex:1) – ligne bouton */
      main.block-container{
          height:100vh;
          display:grid;
          grid-template-rows: auto 1fr auto;
          padding:0;
      }

      /* On neutralise presque toutes les marges par défaut */
      section,div,article,header,footer{margin:0; padding:0;}
      h3 {margin:.8vh 0 1.2vh;}

      #MainMenu,header,footer{visibility:hidden;}
      button:disabled{opacity:.45!important; cursor:not-allowed!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ═══ 2) Mini “router” dans session_state ═════════════════════════════════
st.session_state.setdefault("page", "test")
def go(pg): st.session_state.page = pg; st.rerun()

# ═══ 3) HTML du test 60 Hz (i-frame) ═════════════════════════════════════
TEST_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;background:#000;color:#fff;
          display:flex;flex-direction:column;align-items:center;
          justify-content:center;text-align:center}
h2{margin:0 0 4vh;font-size:6vh}
#res{font-size:8vh;margin:4vh 0}
button{font-size:4vh;padding:1vh 4vh}
</style></head><body>
<h2>Test&nbsp;de&nbsp;fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>

<script>
function send(v){
  if(window.Streamlit && Streamlit.setComponentValue){
      Streamlit.setComponentValue(v);
  }else{
      parent.postMessage(
        {isStreamlitMessage:true,type:"streamlit:componentValue",value:v},"*");
  }
}
/* Demande d’agrandissement automatique : toute la ligne grid (1fr) = 100 % */
function resize(){
  const h = document.documentElement.clientHeight;
  if(window.Streamlit && Streamlit.setFrameHeight){
      Streamlit.setFrameHeight(h);
  }else{
      parent.postMessage(
        {isStreamlitMessage:true,type:"streamlit:setFrameHeight",height:h},"*");
  }
}
window.addEventListener("load",resize);
window.addEventListener("resize",resize);

function mesure(){
  const res=document.getElementById('res'), b=document.getElementById('go');
  b.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0,t0=performance.now();
  (function loop(){
     f++; if(f<120){requestAnimationFrame(loop);}
     else{
        const hz=f*1000/(performance.now()-t0);
        res.textContent='≈ '+hz.toFixed(1)+' Hz';
        res.style.color=Math.abs(hz-60)<1.5?'lime':'red';
        send(hz.toFixed(1));
        b.disabled=false;
     }
  })();
}
</script></body></html>
"""

# ═══ 4) PAGE 0 : test + bouton “Suivant” (aucun scroll) ══════════════════
if st.session_state.page == "test":

    st.markdown(
        "<h3>1.&nbsp;Vérification (facultative) de la fréquence d’écran</h3>",
        unsafe_allow_html=True,
    )

    # i-frame : on fixe une hauteur initiale (400 px) ; elle est
    # immédiatement remplacée par resize() → remplit toute la 2ᵉ ligne grid.
    _val = components.html(TEST_HTML, height=400, scrolling=False)

    # Ligne “bouton” (grid-row:3)
    if st.button("Suivant ➜", use_container_width=True):
        go("intro")

# ═══ 5) PAGE Intro (démo) – aucun scroll non plus ════════════════════════
elif st.session_state.page == "intro":
    st.markdown("<h3>Page intro (zéro scroll)</h3>", unsafe_allow_html=True)
    st.write("Contenu de votre présentation…")
    if st.button("Fin", use_container_width=True):
        go("fin")

elif st.session_state.page == "fin":
    st.markdown("<h2>Fin de la démo ✅</h2>", unsafe_allow_html=True)
