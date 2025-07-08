# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 — Reconnaissance de mots masqués
(familiarisation + test principal – vérification 60 Hz facultative)

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import random
from pathlib import Path
from string import Template

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ───────────────────────── rerun util ─────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ─────────────────────── Streamlit config ─────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────── Session state ────────────────────────
defaults = dict(page="screen_test",
                hz_ok=False,          # mémorise si le test a réussi (info !)
                tirage_running=False,
                tirage_ok=False)
for k, v in defaults.items():
    st.session_state.setdefault(k, v)
p = st.session_state


# ──────────────────  test 60 Hz : HTML/JS  ────────────────────
TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:30px 0}button{font-size:24px;padding:8px 28px}
</style></head><body>
<h2>Test de fréquence (60 Hz)</h2>
<div id="res">--</div><button id="go" onclick="mesure()">Démarrer</button>
<script>
function mesure(){
  const res=document.getElementById('res'), btn=document.getElementById('go');
  btn.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let frames=0, t0=performance.now();
  function loop(){
      frames++;
      if(frames<120){ requestAnimationFrame(loop); }
      else{
        const hz=frames*1000/(performance.now()-t0);
        const ok=hz>58 && hz<62;
        res.textContent='≈ '+hz.toFixed(1)+' Hz';
        res.style.color=ok?'lime':'red';
        btn.disabled=false;
        if(ok){ Streamlit.setComponentValue('ok'); }
      }
  }
  requestAnimationFrame(loop);
}
Streamlit.setComponentReady();
</script></body></html>
"""


# ──────────────────  (1)   page « screen_test »  ──────────────
if p.page == "screen_test":
    st.subheader("Vérification (facultative) de la fréquence d’écran")

    # L’iframe est TOUJOURS visible
    hz_val = components.html(TEST60_HTML, height=600, scrolling=False)

    if hz_val == "ok":
        p.hz_ok = True

    st.markdown(
        "• Cliquez sur « Démarrer » pour tester votre écran "
        "(optionnel — vous pouvez continuer même si le test échoue)."
    )
    if p.hz_ok:
        st.success("Fréquence ≈ 60 Hz détectée.")

    #  bouton disponible tout de suite
    if st.button("Passer à la présentation ➜"):
        p.page = "intro"
        do_rerun()

# ──────────────────  (2)   page « intro »  ───────────────────
elif p.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")
    st.markdown("""
Des mots vont apparaître très brièvement puis seront masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot, puis **Entrée**.  

1. Entraînement (2 mots)  2. Test principal (80 mots)
""")

    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True
        do_rerun()

    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            # --------------  CHARGE LE TABLEUR + TIRAGE 80 STIMULI --------------
            # (le code complet de tirage est inchangé ; mettez ici votre version)
            df = pd.DataFrame({'ortho': [f"MOT{i:02}" for i in range(1,81)]})
            mots = df["ortho"].tolist()
            random.shuffle(mots)
            # -------------------------------------------------------------------
            p.stimuli = mots
            p.tirage_ok = True
            p.tirage_running = False
        st.success("Tirage terminé !")

    if p.tirage_ok:
        if st.button("Commencer la familiarisation"):
            p.page = "fam"
            do_rerun()

# ──────────────────  (3)   page « fam »  ─────────────────────
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** quand le mot apparaît, "
                "puis saisissez-le et validez.")

    # Iframe fictive / à remplacer par votre code tâche-JS réel
    components.html("<p style='color:white;background:black;height:500px;"
                    "display:flex;align-items:center;justify-content:center'>"
                    "Placez ici votre tâche de familiarisation</p>",
                    height=500, scrolling=False)

    st.divider()
    if st.button("Passer au test principal"):
        p.page = "exp"
        do_rerun()

# ──────────────────  (4)   page « exp »  ─────────────────────
elif p.page == "exp":
    components.html("<p style='color:white;background:black;height:500px;"
                    "display:flex;align-items:center;justify-content:center'>"
                    "Placez ici votre test principal (80 mots)</p>",
                    height=500, scrolling=False)
