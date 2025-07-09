# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
Version responsive plein-écran (aucun scroll)
Le bouton « Suivant » est actif dès le départ.
"""
from __future__ import annotations
from pathlib import Path
import inspect, random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ═════════════ utilitaire : re-run ═══════════════════════════════════════
def _rerun() -> None:
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ═════════════ configuration globale (100 % viewport) ════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp      {height:100%; margin:0; overflow:hidden;}
main.block-container   {padding:0;}
#MainMenu,header,footer{visibility:hidden;}
button:disabled        {opacity:.4!important; cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)


# ═════════════ état de session ═══════════════════════════════════════════
for k, v in dict(page="screen_test", hz_val=None,
                 tirage_running=False, tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state
go = lambda pg: (p.__setitem__("page", pg), _rerun())


# ═════════════ fonction helper : i-frame ajusté à 100 % ══════════════════
def full_html(body: str, *, key: str | None = None, height: int = 200):
    html = f"""
    <!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'/>
    <style>html,body{{height:100%;margin:0;overflow:hidden;}}</style></head>
    <body>{body}
      <script>
        const resize = () => Streamlit.setFrameHeight(window.innerHeight);
        window.addEventListener("load",  resize);
        window.addEventListener("resize",resize);
        Streamlit.setComponentReady();
      </script>
    </body></html>"""
    kw = dict(height=height, scrolling=False)
    if key and "key" in inspect.signature(components.html).parameters:
        kw["key"] = key
    return components.html(html, **kw)


# ═════════════ page 0 : Test de fréquence écran ══════════════════════════
if p.page == "screen_test":

    SCREEN_TEST_HTML = r"""
<div style="height:100%;display:flex;flex-direction:column;
            justify-content:center;align-items:center;text-align:center;
            font-family:sans-serif;padding:0 4vw;box-sizing:border-box;gap:2vh">

  <h1 style="margin:0;font-weight:700;font-size:clamp(16px,3vmin,28px)">
      1.&nbsp;Vérification (facultative) de la fréquence d’écran
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

    <!-- clickable dès le départ -->
    <button id="next"
            style="font-size:clamp(14px,3vmin,24px);
                   padding:.7em 2em;border-radius:8px"
            onclick="suivant()">Suivant&nbsp;➜</button>
  </div>
</div>

<script>
let hzVal = null;

/* Lancer la mesure ------------------------------------------------------*/
function mesure(){
  const res=document.getElementById('res'),
        go =document.getElementById('go');
  go.disabled=true;
  res.textContent='Mesure en cours…'; res.style.color='#000';

  let f=0,t0=performance.now();
  (function loop(){
      f++;
      if(f<120){requestAnimationFrame(loop);}
      else{
        const hz = f*1000/(performance.now()-t0);
        hzVal    = hz.toFixed(1);
        const ok = Math.abs(hz-60)<1.5;

        res.textContent = '≈ '+hzVal+' Hz';
        res.style.color = ok ? 'lime' : 'red';

        Streamlit.setComponentValue(hzVal);   // envoi du résultat
        go.disabled=false;
      }
  })();
}

/* Clic sur Suivant ------------------------------------------------------*/
function suivant(){
  /* valeur UNIQUE pour que Streamlit capte chaque clic */
  Streamlit.setComponentValue('NEXT_'+Date.now());
}
</script>"""

    val = full_html(SCREEN_TEST_HTML, key="hz_test")

    # côté Python : on enregistre la fréquence si c’est un nombre
    if isinstance(val, (int, float, str)):
        try:
            p.hz_val = float(val)
        except ValueError:
            pass

    # si l’on reçoit 'NEXT_*' → passage immédiat à la page suivante
    if isinstance(val, str) and val.startswith("NEXT_"):
        go("intro")


# ═════════════ pages suivantes (intro, fam, exp) ═════════════════════════
# Pour la concision, le code de tirage des stimuli est strictement celui
# que vous utilisiez déjà : rien n’a été changé ci-dessous, à l’exception
# des appels go("...") qui restent identiques.
# -------------------------------------------------------------------------
# Vous pouvez ré-insérer ici, tel quel, le reste de votre script
# (intro + familiarisation + test principal) ;
# il fonctionnera sans modification, le bouton « Suivant » étant désormais
# toujours actif dès l’affichage de la page « Test de fréquence ».
# -------------------------------------------------------------------------
