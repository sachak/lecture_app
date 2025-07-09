# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
Version responsive plein-écran : le bouton « Suivant » est hors i-frame.
"""
from __future__ import annotations
from pathlib import Path
import random, inspect
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ──────────────── Outil « rerun » ────────────────────────────────────────
def _rerun():   (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ──────────────── MEP Streamlit (zéro scroll) ───────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp        {height:100%; margin:0; overflow:hidden;}
main.block-container     {padding:0; display:flex; flex-direction:column;
                          align-items:center; justify-content:flex-start;}
#MainMenu,header,footer  {visibility:hidden;}
button:disabled          {opacity:.45!important; cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ──────────────── État de session ───────────────────────────────────────
for k, v in dict(page="screen_test",
                 hz_val=None,
                 tirage_running=False,
                 tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state
go = lambda pg: (p.__setitem__("page", pg), _rerun())

# ──────────────── Fonction helper i-frame plein-écran ───────────────────
def full_html(body:str, *, height:int, key:str|None=None):
    html = f"""
    <!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'/>
    <style>html,body{{height:100%;margin:0;overflow:hidden;}}</style></head>
    <body>{body}
      <script>
        const resize = ()=>Streamlit.setFrameHeight(window.innerHeight);
        window.addEventListener("load",resize); window.addEventListener("resize",resize);
        Streamlit.setComponentReady();
      </script>
    </body></html>"""
    kwargs = dict(height=height, scrolling=False)
    if key and "key" in inspect.signature(components.html).parameters:
        kwargs["key"] = key
    return components.html(html, **kwargs)

# ──────────────── Code de tirage des stimuli (inchangé) ────────────────
MEAN_FACTOR_OLDPLD=.45
MEAN_DELTA = dict(letters=.68, phons=.68)
SD_MULT    = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)
XLSX       = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG=5
TAGS=("LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD")
MAX_TRY_TAG=MAX_TRY_FULL=1_000
rng=random.Random()
NUM_BASE=["nblettres","nbphons","old20","pld20"]
# → les fonctions load_sheets(), build_sheet() … (elles ne changent pas)
#   Pour alléger l’exemple on ne les recopie pas ; replacez ici vos définitions
#   telles qu’elles figuraient déjà dans votre script original.
# (------------- placez ici tout le bloc de fonctions « tirage » -------------)

# ──────────────── HTML du test 60 Hz (i-frame) ──────────────────────────
TEST_HTML=r"""
<h2 style="margin:0;font-size:6vh">Test&nbsp;de&nbsp;fréquence</h2>
<div id="res" style="font-size:8vh;margin:4vh 0">--</div>
<button id="go" onclick="mesure()"
        style="font-size:4vh;padding:.8em 2em">Démarrer</button>
<script>
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
        Streamlit.setComponentValue(hz.toFixed(1));
        b.disabled=false;
  }})();
}
</script>"""

COMMERCIAL=[60,75,90,120,144]
nearest=lambda x:min(COMMERCIAL,key=lambda v:abs(v-x))

# ───────────────────────── PAGE 0 : Test écran ───────────────────────────
if p.page=="screen_test":

    st.markdown("<h3 style='margin:2vh 0 1vh'>1. Vérification (facultative) "
                "de la fréquence d’écran</h3>", unsafe_allow_html=True)

    col_iframe, col_side = st.columns([3,2], gap="large")

    # i-frame noire dans la colonne de gauche
    with col_iframe:
        val = full_html(f"<div style='background:#000;color:#fff;"
                        "height:100%;display:flex;flex-direction:column;"
                        "align-items:center;justify-content:center'>"
                        f"{TEST_HTML}</div>",
                        height=340, key="hz")

    # Affichage du résultat et bouton « Suivant » dans la colonne de droite
    with col_side:
        if isinstance(val,(int,float,str)):
            try: p.hz_val=float(val)
            except ValueError: pass
        if p.hz_val is not None:
            hz_r=nearest(p.hz_val)
            st.write(f"Fréquence détectée : **{hz_r} Hz**")
        else:
            st.info("Cliquez sur « Démarrer » pour effectuer la mesure.")

        st.markdown(" ")  # petite marge
        if st.button("Suivant ➜", use_container_width=True):
            go("intro")

# ───────────────────────── PAGE 1 : Présentation ─────────────────────────
elif p.page=="intro":
    st.markdown("<h3>2. Présentation de la tâche</h3>", unsafe_allow_html=True)
    st.markdown("""
Des mots seront affichés très brièvement puis masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.  

Étapes : 1) Entraînement (2 mots) 2) Test principal (80 mots)
""")
    # tirage des mots (inchangé)
    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running=True; _rerun()
    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df=build_sheet()
            p.stimuli=df["ortho"].tolist(); random.shuffle(p.stimuli)
            p.tirage_ok,p.tirage_running=True,False
        st.success("Tirage terminé !")
    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")

# ───────────────────────── PAGE 2 : Familiarisation ──────────────────────
elif p.page=="fam":
    st.header("Familiarisation (2 mots)")
    st.write("Appuyez sur **ESPACE** dès que le mot apparaît, "
             "tapez-le puis **Entrée**.")
    components.html("<div style='height:300px;background:#000;color:#fff;"
                    "display:flex;align-items:center;justify-content:center'>"
                    "— Votre tâche de familiarisation ici —</div>",
                    height=300, scrolling=False)
    if st.button("Passer au test principal"):
        go("exp")

# ───────────────────────── PAGE 3 : Test principal ───────────────────────
elif p.page=="exp":
    st.header("Test principal (80 mots)")
    components.html("<div style='height:300px;background:#000;color:#fff;"
                    "display:flex;align-items:center;justify-content:center'>"
                    "— Votre tâche principale ici —</div>",
                    height=300, scrolling=False)
