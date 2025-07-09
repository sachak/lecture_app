# -*- coding: utf-8 -*-
"""
Expérience 3 – Démo responsive plein-écran
Un test 60 Hz dans une i-frame + bouton « Suivant » toujours cliquable
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

# ═════════════ configuration 100 % viewport ══════════════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp      {height:100%; margin:0; overflow:hidden;}
main.block-container   {height:100%;
                        display:flex; flex-direction:column;
                        align-items:center; justify-content:space-between;
                        padding:0;}
#MainMenu,header,footer{visibility:hidden;}
button:disabled        {opacity:.45!important; cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ═════════════ état de session (simple) ══════════════════════════════════
st.session_state.setdefault("page", "screen_test")
p = st.session_state
def go(pg:str): p.page = pg; st.rerun()

# ═════════════ HTML du test 60 Hz (i-frame) ══════════════════════════════
def test_iframe() -> str:
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
function send(v){parent.postMessage({isStreamlitMessage:true,
                                     type:"streamlit:componentValue",
                                     value:v},"*")}
function resize(){parent.postMessage({isStreamlitMessage:true,
                                      type:"streamlit:setFrameHeight",
                                      height:Math.round(window.innerHeight*0.70)},"*")}
window.addEventListener("load",resize); window.addEventListener("resize",resize);

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
</script></body></html>"""

# ═════════════ page 0 : test + bouton Suivant ════════════════════════════
if p.page == "screen_test":

    st.markdown("<h3 style='margin-top:2vh'>1.&nbsp;Vérification (facultative) "
                "de la fréquence d’écran</h3>", unsafe_allow_html=True)

    # bloc 1 : i-frame (70 % du viewport, hauteur fixée via JS)
    val = components.html(test_iframe(), height=10, scrolling=False)

    # bloc 2 : bouton indépendant et toujours cliquable
    if st.button("Suivant ➜", use_container_width=True):
        go("intro")

    # (facultatif) on stocke la mesure, si besoin par la suite
    if isinstance(val, (int, float, str)):
        try:
            st.session_state.hz_val = float(val)
        except ValueError:
            pass

# ═════════════ pages suivantes (exemple minimal) ═════════════════════════
elif p.page == "intro":
    st.markdown("<h2>Page Intro</h2>", unsafe_allow_html=True)
    st.write("Ceci est la page suivante. Pas de scroll, bouton en bas.")
    if st.button("Fin", use_container_width=True):
        go("fin")

elif p.page == "fin":
    st.markdown("<h2>Fin de la démo ✅</h2>", unsafe_allow_html=True)
