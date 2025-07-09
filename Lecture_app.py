# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test principal ; contrôle 60 Hz)
(familiarisation + test principal ; contrôle 60 Hz facultatif)

Exécution :   streamlit run exp3.py
Dépendance :  Lexique.xlsx (4 feuilles : Feuil1 … Feuil4)
Dépendance :  Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations

from pathlib import Path
import inspect, random
import random, inspect
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ═════════════════════════════ OUTIL « rerun » ════════════════════════════
# ───────────────────────── utilitaire rerun ──────────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ══════════════ PARAMÈTRES D’AFFICHAGE STREAMLIT ═════════════════════════
# ─────────────────────── configuration Streamlit ─────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


# ══════════════ ÉTAT INITIAL DE L’APPLICATION ════════════════════════════
# ───────────────────────── état par défaut ───────────────────────────────
for k, v in dict(page="screen_test",
                 hz_val=None,          # valeur mesurée (float ou None)
                 hz_val=None,          # fréquence mesurée (float) ou None
                 tirage_running=False,
                 tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state     # alias court
p = st.session_state                                 # alias court


# ══════════════ CONSTANTES & OUTILS « TIRAGE DES 80 MOTS » ═══════════════
# ─────────────────────── constantes / tirage mots ───────────────────────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)
@@ -53,20 +53,19 @@
NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]


# ─────────────────────── fonctions utilitaires tirage ────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[ ,\u00a0]", "", regex=True)
         .str.replace(",", ".", regex=False),
        errors="coerce")


def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)


def cat_code(tag: str) -> int:            # –1 pour LOW, +1 pour HIGH
def cat_code(tag: str) -> int:
    return -1 if "LOW" in tag else 1


@@ -114,28 +113,22 @@
        LOW_OLD  = df.old20 < st_["m_old20"] - st_["sd_old20"],
        HIGH_OLD = df.old20 > st_["m_old20"] + st_["sd_old20"],
        LOW_PLD  = df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
        HIGH_PLD = df.pld20 > st_["m_pld20"] + st_["sd_pld20"]
    )

        HIGH_PLD = df.pld20 > st_["m_pld20"] + st_["sd_pld20"])

def sd_ok(sub, st_, fq) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq)
    )

        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq))

def mean_lp_ok(s, st_) -> bool:
    return (
        abs(s.nblettres.mean() - st_["m_nblettres"])
            <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(s.nbphons.mean()  - st_["m_nbphons"])
            <= MEAN_DELTA["phons"]   * st_["sd_nbphons"]
    )

            <= MEAN_DELTA["phons"]   * st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
@@ -167,13 +160,12 @@
        return samp
    return None


def build_sheet() -> pd.DataFrame:
    F        = load_sheets()
    all_freq = F["all_freq_cols"]

    for _ in range(MAX_TRY_FULL):
        taken  = {sh: set() for sh in F if sh != "all_freq_cols"}
        taken  = {sh:set() for sh in F if sh != "all_freq_cols"}
        groups = []; ok = True

        for tag in TAGS:
@@ -194,29 +186,29 @@
    st.error("Impossible de générer la liste."); st.stop()


# ══════════════ CODE HTML / JS : TEST FRÉQUENCE + VALEUR envoyée à Python ═
TEST60_HTML = r"""
# ────────────────────── composant HTML : test écran ──────────────────────
TEST_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:26px 0}
#res{font-size:48px;margin:24px 0}
button{font-size:22px;padding:6px 26px;margin:4px}
</style></head><body>
<h2>Test de fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>
<script>
function mesure(){
  const res=document.getElementById('res'),btn=document.getElementById('go');
  btn.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  const res=document.getElementById('res'),b=document.getElementById('go');
  b.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0,t0=performance.now();
  function loop(){
    f++; if(f<120){ requestAnimationFrame(loop); }
    else{
      const hz=f*1000/(performance.now()-t0);
      Streamlit.setComponentValue(hz.toFixed(1));   // envoi vers Python
      btn.disabled=false;
      Streamlit.setComponentValue(hz.toFixed(1));   // envoi la valeur à Python
      b.disabled=false;
    }}
  requestAnimationFrame(loop);
}
@@ -225,55 +217,54 @@
"""


# ══════════════ OUTIL : ARRONDIR À LA FRÉQUENCE « COMMERCE » LA + PROCHE ═
# ──────────────────── outil : arrondir à fréquence « commerce » ──────────
COMMERCIAL = [60, 75, 90, 120, 144]
def nearest_hz(x: float) -> int:
    return min(COMMERCIAL, key=lambda v: abs(v-x))
    return min(COMMERCIAL, key=lambda v: abs(v - x))


# ══════════════ NAVIGATION (changement de page) ══════════════════════════
# ───────────────────────── fonction navigation ───────────────────────────
def go(page: str):
    p.page = page
    do_rerun()


# ════════════════════════════ PAGE 0 : TEST ÉCRAN ════════════════════════
# ───────────────────────────────── pages ─────────────────────────────────
# 0. — test fréquence écran
if p.page == "screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")

    # compatibilité du paramètre key (toutes versions de Streamlit)
    html_sig = inspect.signature(components.html).parameters
    kwargs   = dict(height=550, scrolling=False)
    if "key" in html_sig:
        kwargs["key"] = "hz_test"

    hz_js = components.html(TEST60_HTML, **kwargs)
    # clé uniquement si la version de Streamlit l’accepte
    if "key" in inspect.signature(components.html).parameters:
        val = components.html(TEST_HTML, key="hz_test", height=520, scrolling=False)
    else:
        val = components.html(TEST_HTML,              height=520, scrolling=False)

    # Mémoriser la valeur renvoyée (str -> float) si différente
    if hz_js and hz_js != p.hz_val:
    # val peut être None, str, int, float ou … DeltaGenerator (selon versions)
    if isinstance(val, (float, int, str)):
        try:
            p.hz_val = float(hz_js)
            p.hz_val = float(val)
        except ValueError:
            p.hz_val = None
            pass     # ignore si conversion impossible

    # Affichage du résultat (simplifié)
    # Affichage du résultat simplifié
    if p.hz_val is not None:
        hz_round = nearest_hz(p.hz_val)
        if hz_round == 60:
            st.success("60 Hz – OK")
        hz_r = nearest_hz(p.hz_val)
        if hz_r == 60:
            st.success("60 Hz – OK ✅")
        else:
            st.error(f"Désolé, vous ne pouvez pas réaliser l’expérience.")
            st.markdown(f"Fréquence détectée ≈ **{hz_round} Hz**", unsafe_allow_html=True)
            st.error("Désolé, vous ne pouvez pas réaliser l’expérience.")
            st.write(f"Fréquence détectée ≈ **{hz_r} Hz**")
    else:
        st.info("Cliquez sur « Démarrer » pour lancer la mesure.")

    st.divider()
    # Bouton « Suivant » toujours présent
    # bouton toujours disponible
    if st.button("Suivant ➜"):
        go("intro")


# ═══════════════════ PAGE 1 : PRÉSENTATION + TIRAGE 80 MOTS ══════════════
# 1. — présentation + tirage
elif p.page == "intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown("""
@@ -286,7 +277,6 @@
Étapes : 1) Entraînement (2 mots) 2) Test principal (80 mots)
""")

    # Tirage aléatoire : déclenchement puis affichage d’un spinner
    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True; do_rerun()

@@ -302,7 +292,7 @@
        go("fam")


# ═════════════════════ PAGE 2 : FAMILIARISATION ══════════════════════════
# 2. — familiarisation
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Appuyez sur **ESPACE** dès que le mot apparaît, "
@@ -318,11 +308,11 @@
        go("exp")


# ═════════════════════ PAGE 3 : TEST PRINCIPAL ═══════════════════════════
# 3. — test principal
elif p.page == "exp":
    st.header("Test principal (80 mots)")
    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche principale ici —</div>",
        height=300, scrolling=False)
