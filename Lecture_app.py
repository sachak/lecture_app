#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Sélection adaptative de 80 mots (4 × 20)
Lexique : CSV UTF-8, séparateur « ; », décimales « . ».
"""

import json, random
import pandas as pd, numpy as np
import streamlit as st, streamlit.components.v1 as components

# ────────────────────────────────────────────────────────
# 0. CONFIGURATION STREAMLIT
# ────────────────────────────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}</style>",
    unsafe_allow_html=True
)

# ────────────────────────────────────────────────────────
# 1. CHARGE LE LEXIQUE
# ────────────────────────────────────────────────────────
CSV_FILE = "Lexique383.csv"        # UTF-8 ; « ; » ; « . »

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    # harmonise les noms de colonnes
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
    if miss := (need - set(df.columns)):
        raise ValueError(f"Colonnes manquantes : {', '.join(miss)}")

    df.word = df.word.str.upper()
    for c in need - {"word"}:
        df[c] = df[c].astype(float)

    return df.dropna()

LEX = load_lexique()

# ────────────────────────────────────────────────────────
# 2. CRITÈRES FIXES (OLD/PLD)
# ────────────────────────────────────────────────────────
MASKS = {
    "LOW_OLD" :  LEX.old20 < 1.11,
    "HIGH_OLD":  LEX.old20 > 3.79,
    "LOW_PLD" :  LEX.pld20 < 0.70,
    "HIGH_PLD":  LEX.pld20 > 3.20,
}

BASE_WIN = dict(freq=(0.44, 2.94),
                let =(8.5 , 9.5 ),
                pho =(6.5 , 7.5 ))

def enlarge(win: dict, step: float) -> dict:
    """Élargit chaque intervalle de ±step."""
    return {k: (v[0]-step, v[1]+step) for k, v in win.items()}

# ────────────────────────────────────────────────────────
# 3. SÉLECTION ADAPTATIVE DES 80 MOTS
# ────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = np.random.default_rng()

    step = 0.0
    while step <= 2.0:                         # élargissement max ±2
        win = enlarge(BASE_WIN, step)
        chosen: set[str] = set()
        final:  list[str] = []
        success = True

        for name, mask in MASKS.items():
            pool = LEX.loc[mask & ~LEX.word.isin(chosen)].reset_index(drop=True)

            if len(pool) < 20:                 # pas assez de candidats
                success = False
                break

            # 10 000 échantillons de 20 mots
            idx_samples = rng.choice(len(pool), size=(10_000, 20), replace=False)
            med_freq = np.median(pool.freq.values[idx_samples], axis=1)
            med_let  = np.median(pool.let .values[idx_samples], axis=1)
            med_pho  = np.median(pool.pho .values[idx_samples], axis=1)

            ok = ((win["freq"][0] <= med_freq) & (med_freq <= win["freq"][1]) &
                  (win["let" ][0] <= med_let ) & (med_let  <= win["let" ][1]) &
                  (win["pho" ][0] <= med_pho ) & (med_pho  <= win["pho" ][1]))

            if ok.any():                       # échantillon parfait
                best_idx = np.flatnonzero(ok)[0]
            else:                              # meilleur compromis
                penalty = (np.clip(win["freq"][0]-med_freq,0,None) +
                           np.clip(med_freq-win["freq"][1],0,None) +
                           np.clip(win["let"][0]-med_let ,0,None) +
                           np.clip(med_let -win["let"][1],0,None) +
                           np.clip(win["pho"][0]-med_pho ,0,None) +
                           np.clip(med_pho -win["pho"][1],0,None))
                best_idx = penalty.argmin()
                st.warning(f"{name} : médianes approchées (pénalité {penalty[best_idx]:.2f}).")

            sample = pool.iloc[idx_samples[best_idx]]
            final.extend(sample.word.tolist())
            chosen.update(sample.word)

        if success and len(final) == 80:       # réussite
            if step > 0:
                st.info(f"Fenêtres élargies de ±{step:.1f} pour satisfaire les contraintes.")
            random.shuffle(final)
            return final

        step += 0.1                            # élargit et réessaye

    st.error("Impossible de constituer 80 mots même avec un élargissement ±2.")
    st.stop()

STIMULI = pick_stimuli()

# ────────────────────────────────────────────────────────
# 4. PARAMÈTRES VISUELS
# ────────────────────────────────────────────────────────
CYCLE = 350      # durée mot + masque (ms)
START = 14       # 1ʳᵉ exposition (ms)
STEP  = 14       # incrément (ms)

# ────────────────────────────────────────────────────────
# 5. INTERFACE UTILISATEUR
# ────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPÉRIENCE 3 – mots masqués (CSV décimal '.') ")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

# ────────────────────────────────────────────────────────
# 6. PAGE EXPÉRIMENTALE (HTML/JS)
# ────────────────────────────────────────────────────────
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

// paramètres envoyés par Python
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
