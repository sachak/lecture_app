# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots issus de Lexique 3.83 (CSV UTF-8)

Groupes (20 mots chacun, sans doublon)
  – OLD20  < 1.11
  – OLD20  > 3.79
  – PLD20  < 0.70
  – PLD20  > 3.20

Chaque groupe doit avoir les MÉDIANES suivantes :
  freqlemfilms2 ∈ [0.44 ; 2.94]
  nblettres     ∈ [8.5  ; 9.5]
  nbphons       ∈ [6.5  ; 7.5]
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components
import numpy as np

# ───────────── 0. CONFIG STREAMLIT (doit être en premier) ─────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE = "<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none;}</style>"

# ───────────── 1. LECTURE DU LEXIQUE ─────────────
LEXIQUE_FILE = "Lexique383.csv"            # CSV UTF-8 « ; »

def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    # renommage souple
    ren = {}
    for c in df.columns:
        low = c.lower()
        if ("étiquettes" in low) or ("ortho" in low) or ("word" in low):
            ren[c] = "word"
        elif "old20" in low:           ren[c] = "old20"
        elif "pld20" in low:           ren[c] = "pld20"
        elif "freqlemfilms2" in low:   ren[c] = "freq"
        elif "nblettres" in low:       ren[c] = "letters"
        elif "nbphons" in low:         ren[c] = "phons"
    df = df.rename(columns=ren)

    needed = {"word", "old20", "pld20", "freq", "letters", "phons"}
    if not needed.issubset(df.columns):
        st.error(f"Colonnes manquantes : {needed - set(df.columns)}"); st.stop()

    df["word"] = df["word"].str.upper()
    for c in needed - {"word"}:
        df[c] = (df[c].astype(str)
                        .str.replace(",", ".", regex=False)
                        .astype(float))
    return df.dropna()

DF = load_lexique(pathlib.Path(LEXIQUE_FILE))

# ───────────── 2. CRITÈRES & FONCTIONS D’AJUSTEMENT ─────────────
WINDOWS = dict(freq=(0.44, 2.94),
               letters=(8.5, 9.5),
               phons=(6.5, 7.5))

def medians_ok(sample: pd.DataFrame) -> bool:
    return all(lo <= sample[col].median() <= hi
               for col, (lo, hi) in WINDOWS.items())

GROUPS = {
    "LOW_OLD" : lambda d: d.old20 < 1.11,
    "HIGH_OLD": lambda d: d.old20 > 3.79,
    "LOW_PLD" : lambda d: d.pld20 < 0.70,
    "HIGH_PLD": lambda d: d.pld20 > 3.20,
}

@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = np.random.default_rng()
    chosen = set()
    final  = []

    for name, cond in GROUPS.items():
        pool = DF.loc[cond(DF) & ~DF.word.isin(chosen)].copy()
        if len(pool) < 20:
            st.error(f"{name} : seulement {len(pool)} candidats après exclusion doublons."); st.stop()

        idx = pool.index.to_numpy()
        ok  = False
        for _ in range(2000):          # 2 000 tirages aléatoires max → ≈ 0-0.2 s
            sel_idx = rng.choice(idx, size=20, replace=False)
            sample  = pool.loc[sel_idx]
            if medians_ok(sample):
                ok = True
                break
        if not ok:
            st.error(f"Impossible de calibrer les médianes pour {name} en 2000 tirages."); st.stop()

        final.extend(sample.word.tolist())
        chosen.update(sample.word)

    random.shuffle(final)
    return final

STIMULI = pick_stimuli()          # ← rapide (≤ 2 s)

# ───────────── 3. PARAMÈTRES TEMPORISATION ─────────────
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ───────────── 4. UI STREAMLIT & PROTOCOLE ─────────────
if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# ---------- PAGE INTRO ----------
if st.session_state.stage == "intro":
    st.markdown(HIDE, unsafe_allow_html=True)
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.write("80 mots tirés (OLD20 / PLD20) avec médianes calibrées.")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"; st.experimental_rerun()

# ---------- PAGE EXP ----------
elif st.session_state.stage == "exp":
    st.markdown(HIDE, unsafe_allow_html=True)

    html = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<style>
 html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
           background:#fff;font-family:'Courier New',monospace}}
 #scr{{font-size:60px;user-select:none}}
 #ans{{display:none;font-size:48px;width:60%;text-align:center}}
</style></head>
<body id="body" tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());

const WORDS={json.dumps(STIMULI)},C={CYCLE_MS},S={START_MS},P={STEP_MS};
let i=0,res=[],scr=document.getElementById('scr'),ans=document.getElementById('ans');

function trial(){{
 if(i>=WORDS.length){{fin();return;}}
 const w=WORDS[i],mask='#'.repeat(w.length);
 let sd=S,md=C-sd,t0=performance.now(),go=true,t1,t2;
 function loop(){{if(!go)return;
  scr.textContent=w;
  t1=setTimeout(()=>{{if(!go)return;
    scr.textContent=mask;
    t2=setTimeout(()=>{{if(go){{sd+=P;md=Math.max(0,C-sd);loop();}}}},md);
  }},sd);}} loop();

 window.addEventListener('keydown',function onSpace(e){{
   if(e.code==='Space'&&go){{go=false;clearTimeout(t1);clearTimeout(t2);
     const rt=Math.round(performance.now()-t0);
     window.removeEventListener('keydown',onSpace);
     scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
     ans.addEventListener('keydown',function onEnter(ev){{
       if(ev.key==='Enter'){{ev.preventDefault();
         res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
         ans.removeEventListener('keydown',onEnter);ans.style.display='none';i++;trial();}}}});
   }}
 }});
}}

function fin(){{
 scr.style.fontSize='40px';scr.textContent='Merci ! Fin.';
 const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
 const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));
 a.download='results.csv';a.textContent='Télécharger les résultats';
 a.style.fontSize='32px';a.style.marginTop='30px';document.body.appendChild(a);
}}

trial();
</script></body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
