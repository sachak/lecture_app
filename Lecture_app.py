# -*- coding: utf-8 -*-
"""
Expérience 3 – Test 60 Hz + bouton « Suivant » hors i-frame, zéro scroll
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

# ══════════ MEP plein-écran sans scroll ══════════════════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp      {height:100%; margin:0; overflow:hidden;}
main.block-container   {height:100%;
                        display:flex; flex-direction:column;
                        align-items:center; justify-content:flex-start;
                        padding:0;}
#MainMenu,header,footer{visibility:hidden;}
button:disabled        {opacity:.45!important; cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ══════════ session minimale ═════════════════════════════════════════════
st.session_state.setdefault("page", "test")
go = lambda pg: (st.session_state.__setitem__("page", pg), st.rerun())

# ══════════ HTML de l’i-frame (test) ═════════════════════════════════════
def make_test_html() -> str:
    return r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;background:#000;color:#fff;
display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}
h2{margin:0 0 4vh;font-size:6vh} #res{font-size:8vh;margin:4vh 0}
button{font-size:4vh;padding:1vh 4vh}
</style></head><body>
<h2>Test&nbsp;de&nbsp;fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>

<script>
function sendValue(v){
  if(window.Streamlit && Streamlit.setComponentValue){
      Streamlit.setComponentValue(v);
  }else{
      parent.postMessage({isStreamlitMessage:true,
                          type:"streamlit:componentValue",value:v},"*");
  }
}
function resize(){
  const h=Math.round(window.innerHeight*0.70);
  if(window.Streamlit && Streamlit.setFrameHeight){
      Streamlit.setFrameHeight(h);
  }else{
      parent.postMessage({isStreamlitMessage:true,
                          type:"streamlit:setFrameHeight",height:h},"*");
  }
}
window.addEventListener("load",resize);
window.addEventListener("resize",resize);

function mesure(){
  const res=document.getElementById('res'), b=document.getElementById('go');
  b.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0, t0=performance.now();
  (function loop(){
     f++; if(f<120){requestAnimationFrame(loop);}
     else{
        const hz=f*1000/(performance.now()-t0);
        res.textContent='≈ '+hz.toFixed(1)+' Hz';
        res.style.color=Math.abs(hz-60)<1.5?'lime':'red';
        sendValue(hz.toFixed(1));
        b.disabled=false;
  }})();
}
</script></body></html>"""

# ══════════ page 0 : test + bouton séparé ════════════════════════════════
if st.session_state.page == "test":
    st.markdown("<h3 style='margin-top:2vh'>1. Vérification (facultative) "
                "de la fréquence d’écran</h3>", unsafe_allow_html=True)

    # i-frame : hauteur initiale 500 px, ensuite ajustée à 70 % du viewport
    val = components.html(make_test_html(), height=500, scrolling=False)

    st.markdown(" ")   # petite marge
    if st.button("Suivant ➜", use_container_width=True):
        go("intro")

    # on peut mémoriser la valeur reçue si besoin
    if isinstance(val, (int, float, str)):
        try:
            st.session_state.hz_val = float(val)
        except ValueError:
            pass

# ══════════ page suivante (démo) ════════════════════════════════════════
elif st.session_state.page == "intro":
    st.markdown("<h2>Page suivante : Intro</h2>", unsafe_allow_html=True)
    st.write("Plus de contenu ici…")
    if st.button("Fin", use_container_width=True):
        go("fin")

elif st.session_state.page == "fin":
    st.markdown("<h2>Fin de la démo ✅</h2>", unsafe_allow_html=True)
