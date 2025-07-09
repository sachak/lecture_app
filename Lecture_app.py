# -*- coding: utf-8 -*-
"""
Expérience 3 – démonstration « responsive plein-écran »
Le bouton « Suivant » est cliquable immédiatement.
"""
from __future__ import annotations
from pathlib import Path
import inspect, random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ────────────────────────── utilitaire « rerun » ─────────────────────────
def _rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ─────────────────── configuration globale plein-écran ───────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp      {height:100%; margin:0; overflow:hidden;}
main.block-container   {padding:0;}
#MainMenu,header,footer{visibility:hidden;}
button:disabled        {opacity:.4!important; cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


# ───────────────────────────── session state ─────────────────────────────
for k, v in dict(page="screen_test").items():
    st.session_state.setdefault(k, v)
p = st.session_state
go = lambda pg: (p.__setitem__("page", pg), _rerun())


# ─────────────────── helper : composant HTML « plein écran » ─────────────
def full_html(body: str, *, key: str | None = None, height: int = 200):
    """
    Insère un bloc HTML qui renvoie des valeurs à Streamlit.
    Fallback : si l’objet Streamlit n’existe pas encore, on passe par
    parent.postMessage pour garantir la transmission.
    """
    html = f"""
<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'/>
<style>html,body{{height:100%;margin:0;overflow:hidden;}}</style></head>
<body>{body}
<script>
function sendToStreamlit(v){{
  if(window.Streamlit && Streamlit.setComponentValue){{
      Streamlit.setComponentValue(v);
  }}else{{
      parent.postMessage({{
        isStreamlitMessage:true,
        type:"streamlit:componentValue",
        value:v
      }},"*");
  }}
}}
const resize = () => {{
  if(window.Streamlit && Streamlit.setFrameHeight){{
      Streamlit.setFrameHeight(window.innerHeight);
  }}else{{
      parent.postMessage({{
        isStreamlitMessage:true,
        type:"streamlit:setFrameHeight",
        height:window.innerHeight
      }},"*");
  }}
}};
window.addEventListener("load",resize);
window.addEventListener("resize",resize);
if(window.Streamlit && Streamlit.setComponentReady) Streamlit.setComponentReady();
</script>
</body></html>"""
    kw = dict(height=height, scrolling=False)
    if key and "key" in inspect.signature(components.html).parameters:
        kw["key"] = key
    return components.html(html, **kw)


# ──────────────────────── PAGE 0 : test de fréquence ─────────────────────
if p.page == "screen_test":

    TEST_HTML = r"""
<div style="height:100%;display:flex;flex-direction:column;
            justify-content:center;align-items:center;text-align:center;
            font-family:sans-serif;padding:0 4vw;box-sizing:border-box;gap:2vh">

  <h1 style="margin:0;font-weight:700;font-size:clamp(16px,3vmin,28px)">
      1.&nbsp;Vérification de la fréquence d’écran (facultatif)
  </h1>

  <h2 style="margin:0;font-weight:700;font-size:clamp(22px,5vmin,48px)">
      Test&nbsp;de&nbsp;fréquence
  </h2>

  <div id="res" style="font-size:clamp(18px,4.5vmin,40px)">--</div>

  <div style="display:flex;gap:3vw;flex-wrap:wrap;justify-content:center">
    <button id="go"
            style="font-size:clamp(14px,3vmin,24px);
                   padding:.7em 2em;border-radius:8px"
            onclick="mesure()">Démarrer</button>

    <!-- Toujours activé -->
    <button id="next"
            style="font-size:clamp(14px,3vmin,24px);
                   padding:.7em 2em;border-radius:8px"
            onclick="suivant()">Suivant&nbsp;➜</button>
  </div>
</div>

<script>
function mesure(){
  const res=document.getElementById('res'), go=document.getElementById('go');
  go.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#000';
  let f=0,t0=performance.now();
  (function loop(){
     f++; if(f<120){requestAnimationFrame(loop);}
     else{
       const hz=f*1000/(performance.now()-t0);
       res.textContent='≈ '+hz.toFixed(1)+' Hz';
       res.style.color=Math.abs(hz-60)<1.5?'lime':'red';
       sendToStreamlit(hz.toFixed(1));           // résultat facultatif
       go.disabled=false;
  }})();
}
function suivant(){
  sendToStreamlit('NEXT_'+Date.now());            // valeur UNIQUE
}
</script>"""

    val = full_html(TEST_HTML, key="hz")

    # si l’on reçoit NEXT_* => page suivante
    if isinstance(val, str) and val.startswith("NEXT_"):
        go("intro")


# ─────────────────────── PAGE 1 : intro (exemple) ────────────────────────
elif p.page == "intro":
    st.markdown(
        "<div style='height:100%;display:flex;flex-direction:column;"
        "justify-content:center;align-items:center;text-align:center;'>"
        "<h2>Page intro</h2>"
        "<p>Cliquez pour continuer.</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Continuer", use_container_width=True):
        go("fin")


# ─────────────────────── PAGE 2 : fin (exemple) ──────────────────────────
elif p.page == "fin":
    st.markdown(
        "<div style='height:100%;display:flex;flex-direction:column;"
        "justify-content:center;align-items:center;text-align:center;'>"
        "<h2>Fin de la démo ✅</h2></div>",
        unsafe_allow_html=True,
    )
