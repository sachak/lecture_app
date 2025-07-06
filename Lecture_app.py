# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 : sélection adaptative de 80 mots (4 × 20).

Format du résultat : CSV UTF-8, séparateur « ; », décimales « . ».

Étapes :
1. Chargement du Lexique 383 (fichier « Lexique383.csv » placé dans le même
   dossier que ce script).
2. Sélection adaptative de 4 × 20 mots répondant à des contraintes OLD20/PLD20
   et équilibrés sur la fréquence, la longueur orthographique et le nombre
   de phonèmes ; les fenêtres sont élargies jusqu’à trouver une solution.
3. Protocole visuel (mot masqué progressivement) exécuté en HTML/Javascript
   dans Streamlit.
4. Export CSV des réponses.

Lancer :  streamlit run exp3.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from streamlit import components

# ───────────────────────────── 0. CONFIG STREAMLIT ─────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .css-1d391kg {display: none;}  /* ancien sélecteur Streamlit */
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────── 1. CHARGEMENT DU LEXIQUE ──────────────────────── #
CSV_FILE = Path(__file__).with_name("Lexique383.csv")

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    """Charge le fichier Lexique383.csv et met en forme les colonnes utiles."""
    if not CSV_FILE.exists():
        st.error(f"Fichier « {CSV_FILE.name} » introuvable.")
        st.stop()

    df = pd.read_csv(
        CSV_FILE,
        sep=";",
        decimal=".",
        dtype=str,
        encoding="utf-8",
        engine="python",
        on_bad_lines="skip",
    )

    # Harmonisation des noms de colonnes
    rename = {}
    for col in df.columns:
        lc = col.lower()
        if any(k in lc for k in ("étiquettes", "ortho", "word")):
            rename[col] = "word"
        elif "old20" in lc:
            rename[col] = "old20"
        elif "pld20" in lc:
            rename[col] = "pld20"
        elif "freqlemfilms2" in lc:
            rename[col] = "freq"
        elif "nblettres" in lc:
            rename[col] = "let"
        elif "nbphons" in lc:
            rename[col] = "pho"

    df = df.rename(columns=rename)

    required = {"word", "old20", "pld20", "freq", "let", "pho"}
    if not required.issubset(df.columns):
        st.error("Colonnes manquantes dans le lexique : "
                 + ", ".join(sorted(required - set(df.columns))))
        st.stop()

    df["word"] = df["word"].str.upper()
    for c in required - {"word"}:
        df[c] = df[c].astype(float)

    return df.dropna(subset=required)

LEX: pd.DataFrame = load_lexique()

# ─────────────────────── 2. MASQUES ET FENÊTRES INITIALES ──────────────────── #
MASKS = {
    "LOW_OLD" :  LEX.old20 < 10.11,
    "HIGH_OLD":  LEX.old20 > 0.79,
    "LOW_PLD" :  LEX.pld20 < 10.70,
    "HIGH_PLD":  LEX.pld20 > 0.20,
}

BASE_WIN = {
    "freq": (0.44, 59.94),   # Log-freq (freqlemfilms2)
    "let":  (0.5,  59.5),    # Nombre de lettres
    "pho":  (0.5,  59.5),    # Nombre de phonèmes
}

def enlarge(win: dict[str, tuple[float, float]], step: float
            ) -> dict[str, tuple[float, float]]:
    """Élargit chaque intervalle numérique d’une valeur ± step."""
    return {k: (v[0] - step, v[1] + step) for k, v in win.items()}

# ─────────────────────── 3. SÉLECTION ADAPTATIVE DES MOTS ──────────────────── #
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    """Retourne une liste aléatoire de 80 mots (4×20) satisfaisant les contraintes."""
    rng = np.random.default_rng()

    step = 0.0
    while step <= 2.0:                                      # élargissement max ± 2
        win = enlarge(BASE_WIN, step)
        chosen: set[str] = set()          # mots déjà tirés (unicité globale)
        final: list[str] = []
        success = True

        # Boucle sur les 4 conditions OLD/PLD
        for cond_name, cond_mask in MASKS.items():
            pool = LEX.loc[cond_mask & ~LEX.word.isin(chosen)].reset_index(drop=True)

            if len(pool) < 20:                              # impossible à ce pas
                success = False
                break

            # 10 000 tirages indépendants de 20 indices sans remise
            idx_samples = np.array(
                [rng.choice(len(pool), size=20, replace=False) for _ in range(10_000)]
            )

            med_freq = np.median(pool.freq.values[idx_samples], axis=1)
            med_let  = np.median(pool.let .values[idx_samples], axis=1)
            med_pho  = np.median(pool.pho .values[idx_samples], axis=1)

            ok = (
                (win["freq"][0] <= med_freq) & (med_freq <= win["freq"][1]) &
                (win["let" ][0] <= med_let ) & (med_let  <= win["let" ][1]) &
                (win["pho" ][0] <= med_pho ) & (med_pho  <= win["pho" ][1])
            )

            if ok.any():                                      # échantillon parfait
                best = int(np.flatnonzero(ok)[0])
            else:                                             # meilleur compromis
                penalty = (
                    np.clip(win["freq"][0] - med_freq, 0, None) +
                    np.clip(med_freq         - win["freq"][1], 0, None) +
                    np.clip(win["let" ][0] - med_let,  0, None) +
                    np.clip(med_let          - win["let" ][1], 0, None) +
                    np.clip(win["pho" ][0] - med_pho, 0, None) +
                    np.clip(med_pho          - win["pho" ][1], 0, None)
                )
                best = int(penalty.argmin())
                st.warning(f"{cond_name} : médianes approchées "
                           f"(pénalité {penalty[best]:.2f}).")

            sample = pool.iloc[idx_samples[best]]
            chosen.update(sample.word)
            final.extend(sample.word.tolist())

        if success and len(final) == 80:
            if step > 0:
                st.info(f"Fenêtres élargies de ±{step:.1f} pour atteindre la solution.")
            random.shuffle(final)
            return final

        step = round(step + 0.1, 9)                          # évite les flottants

    st.error("Impossible de constituer 80 mots uniques même après élargissement ± 2.")
    st.stop()

STIMULI: list[str] = pick_stimuli()

# ─────────────────────── 4. PROTOCOLE VISUEL (STREAMLIT) ───────────────────── #
CYCLE_MS = 350   # durée totale mot + masque
START_MS = 14    # premier affichage du mot (ms)
STEP_MS  = 14    # incrément (ms)

if "page" not in st.session_state:
    st.session_state.page = "intro"

# ----------------------------- page d'introduction --------------------------- #
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués (CSV décimal « . »)")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

# --------------------------------- expérience -------------------------------- #
else:
    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body {{
    height: 100%;
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'Courier New', monospace;
}}
#scr {{
    font-size: 60px;
    user-select: none;
}}
#ans {{
    display: none;
    font-size: 48px;
    width: 60%;
    text-align: center;
}}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load", () => document.body.focus());

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS};
const START = {START_MS};
const STEP  = {STEP_MS};

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

function nextTrial() {{

    if (trial >= WORDS.length) {{
        endExperiment();
        return;
    }}

    const w = WORDS[trial];
    const mask = "#".repeat(w.length);

    // Durées mot / masque variables
    let showDur = START;
    let hideDur = CYCLE - showDur;
    let tShow, tHide;
    const t0 = performance.now();
    let active = true;

    (function loop() {{
        if (!active) return;

        scr.textContent = w;
        tShow = setTimeout(() => {{
            if (!active) return;

            scr.textContent = mask;
            tHide = setTimeout(() => {{
                if (active) {{
                    showDur += STEP;
                    hideDur = Math.max(0, CYCLE - showDur);
                    loop();
                }}
            }}, hideDur);
        }}, showDur);
    }})();

    function onSpace(e) {{
        if (e.code === "Space" && active) {{
            active = false;
            clearTimeout(tShow);
            clearTimeout(tHide);

            const rt = Math.round(performance.now() - t0);
            window.removeEventListener("keydown", onSpace);

            scr.textContent = "";
            ans.style.display = "block";
            ans.value = "";
            ans.focus();

            function onEnter(ev) {{
                if (ev.key === "Enter") {{
                    ev.preventDefault();
                    results.push({{
                        word: w,
                        rt_ms: rt,
                        response: ans.value.trim()
                    }});
                    ans.removeEventListener("keydown", onEnter);
                    ans.style.display = "none";
                    trial += 1;
                    nextTrial();
                }}
            }}
            ans.addEventListener("keydown", onEnter);
        }}
    }}
    window.addEventListener("keydown", onSpace);
}}

function endExperiment() {{
    scr.style.fontSize = "40px";
    scr.textContent = "Merci !";

    const csv = [
        "word;rt_ms;response",
        ...results.map(r => `${{r.word}};${{r.rt_ms}};${{r.response}}`)
    ].join("\\n");

    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], {{type: "text/csv"}}));
    a.download = "results.csv";
    a.textContent = "Télécharger les résultats";
    a.style.fontSize = "32px";
    a.style.marginTop = "30px";
    document.body.appendChild(a);
}}

nextTrial();
</script>
</body>
</html>
"""
    components.v1.html(html, height=650, scrolling=False)
