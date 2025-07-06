#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – sélection adaptative (version rapide)
Lexique : CSV UTF-8, séparateur « ; », décimales « . ».
"""

import json, random
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ────────────────────────────────────────────────
# 0. CONFIGURATION STREAMLIT
# ────────────────────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}</style>",
    unsafe_allow_html=True
)

# ────────────────────────────────────────────────
# 1. CHARGEMENT DU LEXIQUE
# ────────────────────────────────────────────────
CSV_FILE = "Lexique383.csv"          # UTF-8 ; « ; » ; « . »

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    df = pd.read_csv(
        CSV_FILE, sep=";", decimal=".", encoding="utf-8",
        dtype=str, engine="python", on_bad_lines="skip"
    )

    # harmonisation des noms de colonnes
    ren = {}
    for col in df.columns:
        low = col.lower()
        if "étiquettes" in low or "ortho" in low or "word" in low:
            ren[col] = "word"
        elif "old20" in low:
            ren[col] = "old20"
        elif "pld20" in low:
            ren[col] = "pld20"
        elif "freqlemfilms2" in low:
            ren[col] = "freq"
        elif "nblettres" in low:
            ren[col] = "let"
        elif "nbphons" in low:
            ren[col] = "pho"
    df = df.rename(columns=ren)

    need = {"word", "old20", "pld20", "freq", "let", "pho"}
    if miss := need - set(df.columns):
        raise ValueError(f"Colonnes manquantes : {', '.join(miss)}")

    df.word = df.word.str.upper()
    for c in need - {"word"}:
        df[c] = df[c].astype(float)

    return df.dropna()

LEX = load_lexique()

# ────────────────────────────────────────────────
# 2. CRITÈRES FIXES (OLD / PLD)
# ────────────────────────────────────────────────
MASKS = {
    "LOW_OLD" :  LEX.old20 < 1.11,
    "HIGH_OLD":  LEX.old20 > 3.79,
    "LOW_PLD" :  LEX.pld20 < 0.70,
    "HIGH_PLD":  LEX.pld20 > 3.20,
}

# ────────────────────────────────────────────────
# 3. PARAMÈTRES « ASSOUPLIS » DE SÉLECTION
# ────────────────────────────────────────────────
INIT_WIN      = dict(freq=(0.0, 3.5),   # fenêtres de départ déjà larges
                     let =(4.0,12.0),
                     pho =(4.0,10.0))
STEP_ENLARGE  = 0.30                    # pas d’élargissement ±0.30
MAX_ENLARGES  = 7                       # donc élargissement total possible ±2.1
TRY_PER_MASK  = 20                      # essais « one-shot » avant recours exhaustif
N_EXHAUSTIVE  = 2_000                   # échantillons aléatoires détaillés

# ────────────────────────────────────────────────
# 4. SÉLECTION ADAPTATIVE (rapide)
# ────────────────────────────────────────────────
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = np.random.default_rng()
    win = INIT_WIN.copy()

    for enlarge_round in range(0, MAX_ENLARGES + 1):
        chosen: set[str] = set()
        final : list[str] = []
        ok_all = True

        for name, mask in MASKS.items():
            pool = LEX.loc[mask & ~LEX.word.isin(chosen)].reset_index(drop=True)

            if len(pool) < 20:          # trop peu de candidats : élargir
                ok_all = False
                break

            # 1) jusqu’à 20 tentatives simples
            success = False
            for _ in range(TRY_PER_MASK):
                idx = rng.choice(len(pool), 20, replace=False)
                sample = pool.iloc[idx]
                med   = sample.median(numeric_only=True)

                if (win["freq"][0] <= med.freq <= win["freq"][1] and
                    win["let" ][0] <= med.let  <= win["let" ][1] and
                    win["pho" ][0] <= med.pho  <= win["pho" ][1]):
                    success = True
                    break

            # 2) sinon, 2 000 tirages → meilleur compromis
            if not success:
                idx_samples = np.array(
                    [rng.choice(len(pool), 20, replace=False) for _ in range(N_EXHAUSTIVE)]
                )
                meds = np.stack([
                    np.median(pool.freq.values[idx_samples], axis=1),
                    np.median(pool.let .values[idx_samples], axis=1),
                    np.median(pool.pho .values[idx_samples], axis=1)
                ], axis=1)

                penalty = (
                    np.clip(win["freq"][0] - meds[:,0], 0, None) +
                    np.clip(meds[:,0] - win["freq"][1], 0, None) +
                    np.clip(win["let" ][0] - meds[:,1], 0, None) +
                    np.clip(meds[:,1] - win["let" ][1], 0, None) +
                    np.clip(win["pho" ][0] - meds[:,2], 0, None) +
                    np.clip(meds[:,2] - win["pho" ][1], 0, None)
                )
                idx = idx_samples[penalty.argmin()]
                sample = pool.iloc[idx]

            # ajoute les 20 mots trouvés
            final.extend(sample.word.tolist())
            chosen.update(sample.word)

        if ok_all and len(final) == 80:
            if enlarge_round:
                st.info(f"Fenêtres élargies de ±{enlarge_round*STEP_ENLARGE:.1f}.")
            random.shuffle(final)
            return final

        # élargit toutes les bornes
        win = {k: (v[0]-STEP_ENLARGE, v[1]+STEP_ENLARGE) for k, v in win.items()}

    st.error("Impossible de constituer 80 mots même après élargissement maximal.")
    st.stop()

STIMULI = pick_stimuli()

# ────────────────────────────────────────────────
# 5. PARAMÈTRES VISUELS
# ────────────────────────────────────────────────
CYCLE = 350      # durée mot+masque (ms)
START = 14       # première présentation (ms)
STEP  = 14       # incrément (ms)

# ────────────────────────────────────────────────
# 6. INTERFACE UTILISATEUR
# ────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPÉRIENCE 3 – mots masqués (version rapide)")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

# ────────────────────────────────────────────────
# 7. PAGE EXPÉRIMENTALE (HTML + JS)
# ────────────────────────────────────────────────
elif st.session_state.page == "exp":
    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<style>
body {{ user-select:none; margin:0; display:flex; flex-direction:column;
       align-items:center; justify-content:center; height:100vh; }}
#scr {{ font-family:Arial,Helvetica,sans-serif; font-size:64px; }}
#ans {{ font-size:32px; margin-top:20px; }}
</style>
</head>
<body id="body" tabindex="0">

<div id="scr"></div>
<input id="ans" style="display:none;" autocomplete="off"/>

<script>
// focus automatique
window.addEventListener('load', () => document.getElementById('body').focus());

const W = {json.dumps(STIMULI)};
const C = {CYCLE};
const S = {START};
const P = {STEP};

let i = 0;
let res = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

function run() {{
    if (i >= W.length) {{ fin(); return; }}
    const w = W[i];
    const mask = '#'.repeat(w.length);
    let sd = S;
    let md = C - sd;
    const t0 = performance.now();
    let on = true;
    let t1, t2;

    (function loop() {{
        if (!on) return;
        scr.textContent = w;
        t1 = setTimeout(() => {{
            if (!on) return;
            scr.textContent = mask;
            t2 = setTimeout(() => {{
                if (on) {{
                    sd += P;
                    md = Math.max(0, C - sd);
                    loop();
                }}
            }}, md);
        }}, sd);
    }})();

    function spaceListener(e) {{
        if (e.code === 'Space' && on) {{
            on = false;
            clearTimeout(t1);
            clearTimeout(t2);
            const rt = Math.round(performance.now() - t0);
            window.removeEventListener('keydown', spaceListener);

            scr.textContent = '';
            ans.style.display = 'block';
            ans.value = '';
            ans.focus();

            function enterListener(ev) {{
                if (ev.key === 'Enter') {{
                    ev.preventDefault();
                    res.push({{word: w, rt_ms: rt, response: ans.value.trim()}});
                    ans.removeEventListener('keydown', enterListener);
                    ans.style.display = 'none';
                    i++;
                    run();
                }}
            }}
            ans.addEventListener('keydown', enterListener);
        }}
    }}
    window.addEventListener('keydown', spaceListener);
}}

function fin() {{
    scr.style.fontSize = '40px';
    scr.textContent = 'Merci !';
    const csv = ['word;rt_ms;response',
                 ...res.map(r => r.word + ';' + r.rt_ms + ';' + r.response)].join('\\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], {{type: 'text/csv'}}));
    a.download = 'results.csv';
    a.textContent = 'Télécharger les résultats';
    a.style.fontSize = '32px';
    a.style.marginTop = '30px';
    document.body.appendChild(a);
}}

run();
</script>
</body>
</html>
"""
    components.html(html, height=650, scrolling=False)
