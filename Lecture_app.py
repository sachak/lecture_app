# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
Exécution :   streamlit run exp3.py
Dépendance :  Lexique.xlsx (Feuil1 … Feuil4)
"""

from __future__ import annotations

# ==========================================================================
# Imports
# ==========================================================================
from pathlib import Path
import random
import inspect

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ==========================================================================
# Outil « rerun » (compatibilité toutes versions)
# ==========================================================================
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ==========================================================================
# Paramètres d’affichage Streamlit
# ==========================================================================
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
      #MainMenu, header, footer {visibility:hidden;}
      button:disabled{opacity:.45!important;cursor:not-allowed!important;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================================
# État initial de l’application
# ==========================================================================
DEFAULT_SESSION_STATE = dict(
    page="screen_test",
    hz_val=None,          # fréquence mesurée (float) ou None
    tirage_running=False,
    tirage_ok=False,
)
for k, v in DEFAULT_SESSION_STATE.items():
    st.session_state.setdefault(k, v)
p = st.session_state        # alias court


# ==========================================================================
# CONSTANTES & OUTILS « TIRAGE DES 80 MOTS »
# (vous pouvez compléter/refactoriser plus tard)
# ==========================================================================
MEAN_FACTOR_OLDPLD = 0.45
MEAN_DELTA = dict(letters=.68, phons=.68)
SD_MULT = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

MAX_TRY_FULL = 3
TAGS = ["LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD"]
NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

rng = random.Random()


# ---------- fonctions utilitaires tirage (extraits) ----------
def to_float(s: pd.Series) -> pd.Series:
    """Convertit proprement une série vers float (gère , / espace / nbsp)."""
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[ \u00a0 ]", "", regex=True)  # NBSP + espace
         .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)


def cat_code(tag: str) -> int:         # –1 pour LOW, +1 pour HIGH
    return -1 if "LOW" in tag else 1


# --------------------------- À COMPLÉTER ---------------------------
#  • load_sheets()
#  • pick_five(...)
#  • build_sheet()
# ------------------------------------------------------------------


# ==========================================================================
# Composant HTML/JS de mesure de fréquence écran
# ==========================================================================
TEST_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:24px 0}
button{font-size:22px;padding:6px 26px;margin:4px}
</style></head><body>
<h2>Test de fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>
<script>
function mesure(){
  const res=document.getElementById('res'), b=document.getElementById('go');
  b.disabled = true;
  res.textContent = 'Mesure en cours…';
  let f = 0, t0 = performance.now();
  function loop(){
    f++;
    if(f < 120){ requestAnimationFrame(loop); }
    else{
      const hz = f * 1000 / (performance.now() - t0);
      Streamlit.setComponentValue(hz.toFixed(1));   // renvoi vers Python
      b.disabled = false;
    }}
  requestAnimationFrame(loop);
}
</script></body></html>
"""


# ==========================================================================
# Petite fonction utilitaire : arrondir à la fréquence « commerce »
# ==========================================================================
COMMERCIAL = [60, 75, 90, 120, 144]
nearest_hz = lambda x: min(COMMERCIAL, key=lambda v: abs(v - x))


# ==========================================================================
# Navigation (changement de page)
# ==========================================================================
def go(page: str):
    p.page = page
    do_rerun()


# ==========================================================================
# PAGE 0 – Test écran
# ==========================================================================
if p.page == "screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")

    html_args = dict(height=520, scrolling=False)
    if "key" in inspect.signature(components.html).parameters:
        html_args["key"] = "hz_test"

    returned = components.html(TEST_HTML, **html_args)

    # returned peut être None, str, int, float ou… DeltaGenerator
    if isinstance(returned, (float, int, str)) and returned != p.hz_val:
        try:
            p.hz_val = float(returned)
        except Exception:
            pass  # ignore si la conversion échoue

    # Affichage du résultat
    if p.hz_val is not None:
        hz_r = nearest_hz(p.hz_val)
        if hz_r == 60:
            st.success("60 Hz – OK ✅")
        else:
            st.error("Désolé, vous ne pouvez pas réaliser l’expérience.")
            st.write(f"Fréquence détectée ≈ **{hz_r} Hz**")
    else:
        st.info("Cliquez sur « Démarrer » pour lancer la mesure.")

    st.divider()

    if st.button("Suivant ➜"):
        go("intro")


# ==========================================================================
# PAGE 1 – Présentation + tirage
# ==========================================================================
elif p.page == "intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown(
        """
        Dans cette tâche, vous devez appuyer sur **ESPACE** dès que le mot masqué apparaît.

        Étapes :
        1) Entraînement (2 mots)  
        2) Test principal (80 mots)
        """
    )

    # Tirage aléatoire (fictif pour l'instant)
    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True
        do_rerun()

    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Génération de la liste de mots…"):
            # build_sheet()  ➜ à activer quand la fonction existera
            pass
        p.tirage_running = False
        p.tirage_ok = True
        do_rerun()

    else:
        st.success("Liste de 80 mots générée ✔️")
        if st.button("Commencer la familiarisation ➜"):
            go("fam")


# ==========================================================================
# PAGE 2 – Familiarisation
# ==========================================================================
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Appuyez sur **ESPACE** dès que le mot apparaît…")

    if st.button("Passer au test principal ➜"):
        go("exp")


# ==========================================================================
# PAGE 3 – Test principal
# ==========================================================================
elif p.page == "exp":
    st.header("Test principal (80 mots)")

    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche principale ici —</div>",
        height=300,
        scrolling=False,
    )
