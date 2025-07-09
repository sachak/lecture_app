# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
Test 60 Hz dans une i-frame ; bouton « Suivant » séparé, sans scroll.
"""
from __future__ import annotations
from pathlib import Path
import inspect, random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# =============== utilitaire « rerun » ====================================
def _rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# =============== configuration globale plein-écran =======================
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp      {height:100%; margin:0; overflow:hidden;}
main.block-container   {height:100%; padding:0;
                        display:flex; flex-direction:column;
                        align-items:center; justify-content:space-between;}
#MainMenu,header,footer{visibility:hidden;}
button:disabled        {opacity:.45!important; cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# =============== état de session =========================================
st.session_state.setdefault("page", "screen_test")
p = st.session_state
go = lambda pg: (p.__setitem__("page", pg), _rerun())

# ───────────────── helper : i-frame auto-resize (ratio 0.70) ─────────────
def test_iframe_html() -> str:
    return r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;background:#000;color:#fff;
display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}
h2{margin:0 0 4vh;font-size:6vh} #res{font-size:8vh;margin:4vh 0}
button{font-size:4vh;padding:1vh 4vh}
</style></head><body>
<h2>Test&nbsp;de&nbsp;fréquence</h2><div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>
<script>
function send(val){
  parent.postMessage({isStreamlitMessage:true,
                      type:"streamlit:componentValue", value:val},"*");}
function setH(){parent.postMessage({isStreamlitMessage:true,
                                    type:"streamlit:setFrameHeight",
                                    height:Math.round(window.innerHeight*0.70)},"*");}
window.addEventListener("load",setH); window.addEventListener("resize",setH);

function mesure(){
  const res=document.getElementById('res'),b=document.getElementById('go');
  b.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0,t0=performance.now();
  (function loop(){
     f++; if(f<120){requestAnimationFrame(loop);}
     else{
        const hz=f*1000/(performance.now()-t0);
        res.textContent='≈ '+hz.toFixed(1)+' Hz';
        res.style.color=Math.abs(hz-60)<1.5?'lime':'red';
        send(hz.toFixed(1));  b.disabled=false;
  }})();
}
</script></body></html>"""

def iframe_component(key:str="hz") -> str|None:
    return components.html(test_iframe_html(),
                           height=10,  # corrigé par JS → 70 % du viewport
                           scrolling=False,
                           key=key if "key" in inspect.signature(components.html).parameters else None)

# =============== PAGE 0 : test 60 Hz + bouton « Suivant » ================
if p.page == "screen_test":

    st.markdown("<h3 style='margin-top:2vh'>1. Vérification (facultative) "
                "de la fréquence d’écran</h3>", unsafe_allow_html=True)

    # bloc 1 : i-frame noir (70 % hauteur fenêtre)
    val = iframe_component()

    # bloc 2 : bouton “Suivant” placé hors i-frame
    st.markdown(" ")           # petite marge
    if st.button("Suivant ➜", use_container_width=True):
        go("intro")

    # (facultatif) on stocke la valeur mesurée si c’est un nombre
    if isinstance(val, (int, float, str)):
        try: p.hz_val = float(val)
        except ValueError: pass


# ========================================================================
#  Les pages suivantes sont laissées ultra-simples
#  ─ remplacez-les par votre vrai contenu (tirage stimuli, etc.)
# ========================================================================

elif p.page == "intro":
    st.markdown("<h2>Page Intro</h2>", unsafe_allow_html=True)
    st.write("Ceci est la page suivante. Cliquez pour poursuivre.")
    if st.button("Continuer", use_container_width=True):
        go("fin")

elif p.page == "fin":
    st.markdown("<h2>Fin de la démo ✅</h2>", unsafe_allow_html=True)
