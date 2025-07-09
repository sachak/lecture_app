# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test principal ; contrôle 60 Hz invisible)

Exécution  :  streamlit run exp3.py
Dépendance :  Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations

from pathlib import Path
import random, inspect
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ───────────────────────── Configuration générale ────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled {opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


# ────────────────────────  État par défaut  ──────────────────────────────
for k, v in dict(page="intro",
                 hz_ok=None, hz_val=None,
                 tirage_running=False, tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state


# ──────────────────────  Rerun utilitaire  ───────────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ──────────  Test de fréquence INVISIBLE (lancé immédiatement)  ──────────
COMMERCIAL = [60, 75, 90, 120, 144]
def nearest_hz(x: float) -> int:
    return min(COMMERCIAL, key=lambda v: abs(v - x))

def hidden_screen_test() -> None:
    """
    Mesure automatique et invisible ; arrête l’appli si ≠ 60 Hz ±1,5 Hz.
    S’exécute avant toute interface « utile ».
    """
    # Test déjà effectué
    if p.hz_ok is not None:
        if p.hz_ok:
            return                      # OK -> continuer
        st.error("Votre écran n’affiche pas à 60 Hz ; "
                 "l’expérience ne peut pas démarrer.")
        st.stop()

    # Première passe : on lance la mesure
    st.info("Initialisation de l’expérience …")          # message visible
    TEST_HTML = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;overflow:hidden}</style></head><body>
<script>
let f=0,t0=performance.now();
(function loop(){
  f++; if(f<120){ requestAnimationFrame(loop); }
  else{
    const hz=f*1000/(performance.now()-t0);
    Streamlit.setComponentValue(hz.toFixed(1));   // renvoi Python
  }
})();
</script></body></html>"""
    html_args = dict(height=1, scrolling=False)          # 1 px : quasi invisible
    if "key" in inspect.signature(components.html).parameters:
        html_args["key"] = "auto_hz_test"
    val = components.html(TEST_HTML, **html_args)

    # Dès que le composant renvoie quelque chose on l’exploite
    if isinstance(val, (int, float, str)):
        try:
            hz = float(val)
            p.hz_val = hz
            p.hz_ok  = (nearest_hz(hz) == 60)
        finally:
            do_rerun()            # relance pour poursuivre ou bloquer
    else:
        st.stop()                 # on attend la fin de la mesure

# Appel AVANT toute autre interface
hidden_screen_test()


# ──────────  (le reste du script est inchangé : tirage, pages, etc.)  ────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

XLSX             = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG  = 5
TAGS             = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG      = MAX_TRY_FULL = 1_000
rng              = random.Random()

NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

# … (toutes les fonctions load_sheets, build_sheet, etc. restent identiques)
# Pour économiser de l’espace elles ne sont pas recopiées ici,
# reprenez-les telles quelles depuis votre version actuelle,
# juste en dessous de cette ligne, sans rien changer.

# ─────────── Navigation & pages (identiques à l’original, sauf « screen_test ») ───────────
def go(page: str):
    p.page = page
    do_rerun()


# 1. Présentation + tirage
if p.page == "intro":
    st.subheader("1. Présentation de la tâche")
    st.markdown("""
Des mots seront affichés très brièvement puis masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.  

Étapes : 1) Entraînement (2 mots) 2) Test principal (80 mots)
""")

    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True; do_rerun()

    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet()
            mots = df["ortho"].tolist(); random.shuffle(mots)
            p.stimuli = mots
            p.tirage_ok, p.tirage_running = True, False
        st.success("Tirage terminé !")

    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")


# 2. Familiarisation
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Appuyez sur **ESPACE** dès que le mot apparaît, "
             "tapez-le puis **Entrée**.")

    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche de familiarisation ici —</div>",
        height=300, scrolling=False)

    if st.button("Passer au test principal"):
        go("exp")


# 3. Test principal
elif p.page == "exp":
    st.header("Test principal (80 mots)")
    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche principale ici —</div>",
        height=300, scrolling=False)
