#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – sélection adaptative vraiment « inratable ».
  • On commence avec vos seuils stricts.
  • S’il manque des mots, on détend peu à peu OLD20/PLD20 jusqu’à y arriver.
  • Une fois qu’il y a ≥20 candidats par masque, on tire 20 mots uniques
    dans chaque catégorie et on les mélange.
  • S’il n’est toujours pas possible d’avoir 80 mots uniques, on autorise
    l’échantillonnage AVEC remise (dernier recours).
"""

import json, random, itertools
import numpy as np, pandas as pd
import streamlit as st, streamlit.components.v1 as components

# ───────────────────────────────────────────────
# 0. CONFIG STREAMLIT
# ───────────────────────────────────────────────
st.set_page_config(page_title="Expérience 3 – sélection adaptative", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}</style>",
            unsafe_allow_html=True)

# ───────────────────────────────────────────────
# 1. CHARGEMENT / PRÉ-TRAITEMENT DU LEXIQUE
# ───────────────────────────────────────────────
CSV_FILE = "Lexique383.csv"

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    # uniformise les noms de colonnes utiles
    ren = {}
    for col in df.columns:
        c = col.lower()
        if "ortho" in c or "word" in c or "étiquettes" in c: ren[col] = "word"
        elif "old20" in c:   ren[col] = "old20"
        elif "pld20" in c:   ren[col] = "pld20"
    df = df.rename(columns=ren)

    need = {"word", "old20", "pld20"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError("Colonnes manquantes : " + ", ".join(miss))

    df.word  = df.word.str.upper()
    df.old20 = df.old20.astype(float)
    df.pld20 = df.pld20.astype(float)
    return df.dropna(subset=need)

LEX = load_lexique()

# ───────────────────────────────────────────────
# 2. SEUILS DE DÉPART + PAS D’ASSOUPLISSEMENT
# ───────────────────────────────────────────────
THR = dict(LO_old=1.11, HI_old=3.79, LO_pld=0.70, HI_pld=3.20)
STEP = 0.10          # on détendra de ±0.10 à chaque tour
MAX_STEP = 4.0       # old20 / pld20 sont compris ~0–4 ⇒ 4 ≈ « plus de limite »

# ───────────────────────────────────────────────
# 3. SÉLECTION (assouplissement dynamique)
# ───────────────────────────────────────────────
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = np.random.default_rng()
    thr = THR.copy()

    while thr["LO_old"] < thr["HI_old"] and thr["LO_pld"] < thr["HI_pld"]:
        # crée les masques avec les seuils courants
        masks = {
            "LOW_OLD" :  LEX.old20 < thr["LO_old"],
            "HIGH_OLD":  LEX.old20 > thr["HI_old"],
            "LOW_PLD" :  LEX.pld20 < thr["LO_pld"],
            "HIGH_PLD":  LEX.pld20 > thr["HI_pld"],
        }

        sizes = {k: int(m.sum()) for k,m in masks.items()}
        if all(s >= 20 for s in sizes.values()):
            # suffisamment de candidats → essaye de constituer 80 mots uniques
            for attempt in range(1_000):
                chosen = set()
                final  = []
                # ordre aléatoire pour limiter les collisions
                for name in random.sample(list(masks), 4):
                    pool = LEX.loc[masks[name] & ~LEX.word.isin(chosen)].word.tolist()
                    if len(pool) < 20:
                        break
                    final += rng.choice(pool, 20, replace=False).tolist()
                    chosen = set(final)

                if len(final) == 80:
                    random.shuffle(final)
                    return final

            # après 1000 tentatives on accepte le doublon final :
            chosen = set()
            final  = []
            for name in random.sample(list(masks), 4):
                pool = LEX.loc[masks[name]].word.tolist()
                final += rng.choice(pool, 20, replace=False).tolist()
            random.shuffle(final)
            return final

        # pas assez de candidats dans au moins une catégorie :
        thr["LO_old"] += STEP
        thr["HI_old"] -= STEP
        thr["LO_pld"] += STEP
        thr["HI_pld"] -= STEP
        # borne « au cas où »
        if thr["LO_old"] >= MAX_STEP or thr["LO_pld"] >= MAX_STEP:
            break

    st.error("Même après assouplissement maximal, impossible de trouver 80 mots.")
    st.stop()

STIMULI = pick_stimuli()

# ───────────────────────────────────────────────
# 4. PARAMÈTRES VISUELS
# ───────────────────────────────────────────────
CYCLE, START, STEP_VIS = 350, 14, 14   # ms

# ───────────────────────────────────────────────
# 5. INTERFACE STREAMLIT
# ───────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPÉRIENCE 3 – sélection adaptative inratable")
    st.markdown(
        "Les seuils OLD/PLD sont automatiquement détendus jusqu’à ce qu’il y ait "
        "toujours 20 mots par catégorie ; puis on tire 80 mots uniques."
    )
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

# ───────────────────────────────────────────────
# 6. PAGE EXPÉRIMENTALE (HTML/JS)
# ───────────────────────────────────────────────
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

const W = {json.dumps(STIMULI)}, C = {CYCLE}, S = {START}, P = {STEP_VIS};
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
  const csv = ['word;rt_ms;response',
               ...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
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
