#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – version « ultra-souple »
  • CSV Lexique 383 : UTF-8, séparateur « ; », décimales « . »
  • Objectif : 80 mots uniques (4 × 20) répondant aux 4 masques OLD/PLD.
  • Aucune contrainte supplémentaire → sélection en quelques millisecondes.
"""

import json, random
import numpy as np, pandas as pd
import streamlit as st, streamlit.components.v1 as components

# ───────────────────────────────────────────────
# 0. CONFIG STREAMLIT
# ───────────────────────────────────────────────
st.set_page_config(page_title="Expérience 3 – ultra-souple", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

# ───────────────────────────────────────────────
# 1. LEXIQUE
# ───────────────────────────────────────────────
CSV_FILE = "Lexique383.csv"

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")
    ren = {}
    for col in df.columns:
        l = col.lower()
        if "ortho" in l or "word" in l or "étiquettes" in l: ren[col] = "word"
        elif "old20" in l:       ren[col] = "old20"
        elif "pld20" in l:       ren[col] = "pld20"
    df = df.rename(columns=ren)

    need = {"word", "old20", "pld20"}
    if miss := need - set(df.columns):
        raise ValueError(f"Colonnes manquantes : {', '.join(miss)}")

    df.word = df.word.str.upper()
    df.old20 = df.old20.astype(float)
    df.pld20 = df.pld20.astype(float)
    return df.dropna(subset=list(need))

LEX = load_lexique()

# ───────────────────────────────────────────────
# 2. MASQUES OLD / PLD
# ───────────────────────────────────────────────
MASKS = {
    "LOW_OLD" :  LEX.old20 < 1.11,
    "HIGH_OLD":  LEX.old20 > 3.79,
    "LOW_PLD" :  LEX.pld20 < 0.70,
    "HIGH_PLD":  LEX.pld20 > 3.20,
}

# ───────────────────────────────────────────────
# 3. SÉLECTION ULTRA-SOUPE
# ───────────────────────────────────────────────
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = np.random.default_rng()
    masks_names = list(MASKS.keys())

    for _ in range(10_000):                 # 10 000 tentatives max (≪ 1 s)
        random.shuffle(masks_names)         # ordre aléatoire → évite blocages
        chosen = set()
        final  = []
        ok = True

        for name in masks_names:
            pool = LEX.loc[MASKS[name] & ~LEX.word.isin(chosen)].word.tolist()
            if len(pool) < 20:              # pas assez de candidats → new try
                ok = False
                break
            final += rng.choice(pool, 20, replace=False).tolist()
            chosen = set(final)

        if ok and len(final) == 80:
            random.shuffle(final)
            return final

    st.error("Impossible de trouver 80 mots uniques – vérifiez le lexique.")
    st.stop()

STIMULI = pick_stimuli()

# ───────────────────────────────────────────────
# 4. PARAMÈTRES VISUELS
# ───────────────────────────────────────────────
CYCLE, START, STEP = 350, 14, 14   # ms

# ───────────────────────────────────────────────
# 5. INTERFACE
# ───────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPÉRIENCE 3 – ultra-souple (80 mots)")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

elif st.session_state.page == "exp":
    html = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<style>
body {{user-select:none;margin:0;display:flex;flex-direction:column;
       align-items:center;justify-content:center;height:100vh}}
#scr {{font-family:Arial,Helvetica,sans-serif;font-size:64px}}
#ans {{font-size:32px;margin-top:20px}}
</style></head><body id="body" tabindex="0">

<div id="scr"></div>
<input id="ans" style="display:none" autocomplete="off">

<script>
window.onload = () => document.getElementById('body').focus();

const W = {json.dumps(STIMULI)}, C = {CYCLE}, S = {START}, P = {STEP};
let i = 0, res = [];
const scr = document.getElementById('scr'), ans = document.getElementById('ans');

function run(){{
  if(i >= W.length) return fin();
  const w = W[i], mask = '#'.repeat(w.length);
  let sd = S, md = C - sd, t0 = performance.now(), on = true, t1, t2;

  (function loop(){{
    if(!on) return;
    scr.textContent = w;
    t1 = setTimeout(()=>{{ if(!on) return;
      scr.textContent = mask;
      t2 = setTimeout(()=>{{ if(on){{ sd += P; md = Math.max(0, C - sd); loop(); }} }}, md);
    }}, sd);
  }})();

  function space(e){{
    if(e.code !== 'Space' || !on) return;
    on = false; clearTimeout(t1); clearTimeout(t2);
    const rt = Math.round(performance.now() - t0);
    window.removeEventListener('keydown', space);

    scr.textContent = '';
    ans.style.display='block'; ans.value=''; ans.focus();

    ans.onkeydown = ev => {{
      if(ev.key !== 'Enter') return;
      ev.preventDefault();
      res.push({{word:w, rt_ms:rt, response:ans.value.trim()}});
      ans.onkeydown = null; ans.style.display='none'; i++; run();
    }};
  }}
  window.addEventListener('keydown', space);
}}

function fin(){{
  scr.style.fontSize='40px'; scr.textContent='Merci !';
  const csv = ['word;rt_ms;response', ...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
  const a = Object.assign(document.createElement('a'), {{
    href:URL.createObjectURL(new Blob([csv], {{type:'text/csv'}})),
    download:'results.csv',
    textContent:'Télécharger les résultats',
    style:'font-size:32px;margin-top:30px'
  }});
  document.body.appendChild(a);
}}

run();
</script></body></html>
"""
    components.html(html, height=650, scrolling=False)
