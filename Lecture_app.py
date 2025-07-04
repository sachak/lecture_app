# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – sélection ultra-rapide (vectorisée) de 80 mots

Groupes (20 mots) : OLD20<1.11 ; OLD20>3.79 ; PLD20<0.70 ; PLD20>3.20
Médianes exigées :
  freq  ∈ [0.44 ; 2.94]
  nblet ∈ [8.5  ; 9.5]
  nbpho ∈ [6.5  ; 7.5]
"""

import json, pathlib, pandas as pd, numpy as np, streamlit as st
import streamlit.components.v1 as components, time, random

# ───────── CONFIG PAGE ─────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none}</style>",
            unsafe_allow_html=True)

# ───────── 1. LECTURE CSV ─────────
CSV = "Lexique383.csv"

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique():
    df = pd.read_csv(CSV, sep=";", decimal=",", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    ren = {}
    for c in df.columns:
        l=c.lower()
        if "étiquettes" in l or "ortho" in l or "word" in l: ren[c]="word"
        elif "old20" in l:  ren[c]="old20"
        elif "pld20" in l:  ren[c]="pld20"
        elif "freqlemfilms2" in l: ren[c]="freq"
        elif "nblettres" in l: ren[c]="let"
        elif "nbphons" in l:  ren[c]="pho"
    df = df.rename(columns=ren)

    need={"word","old20","pld20","freq","let","pho"}
    if not need.issubset(df.columns):
        st.error(f"Colonnes manquantes : {need-set(df.columns)}"); st.stop()

    df["word"]=df.word.str.upper()
    for c in need-{"word"}:
        df[c]=df[c].str.replace(",",".",regex=False).astype(float)

    return df.dropna()

LEX=load_lexique()

# ───────── 2. PARAMÈTRES DE SÉLECTION ─────────
WINDOW = dict(freq=(0.44,2.94), let=(8.5,9.5), pho=(6.5,7.5))
GROUPS = [
    ("LOW_OLD" , LEX.old20 < 1.11),
    ("HIGH_OLD", LEX.old20 > 3.79),
    ("LOW_PLD" , LEX.pld20 < 0.70),
    ("HIGH_PLD", LEX.pld20 > 3.20),
]

def select_group(mask, forbidden, rng, draws=25_000):
    pool   = LEX.loc[mask & ~LEX.word.isin(forbidden)].reset_index(drop=True)
    n      = len(pool)
    if n < 20:
        st.error("Pas assez de candidats après exclusion."); st.stop()

    idx_mat = rng.integers(0, n, size=(draws, 20))          # (draws × 20)
    # récupère d'un coup les valeurs des 3 colonnes
    arr_freq = pool.freq.to_numpy()[idx_mat]
    arr_let  = pool.let .to_numpy()[idx_mat]
    arr_pho  = pool.pho .to_numpy()[idx_mat]

    med_freq = np.median(arr_freq, axis=1)
    med_let  = np.median(arr_let,  axis=1)
    med_pho  = np.median(arr_pho,  axis=1)

    ok = ((WINDOW["freq"][0] <= med_freq) & (med_freq <= WINDOW["freq"][1]) &
          (WINDOW["let" ][0] <= med_let ) & (med_let  <= WINDOW["let" ][1]) &
          (WINDOW["pho" ][0] <= med_pho ) & (med_pho  <= WINDOW["pho" ][1]))

    if ok.any():                              # au moins un tirage parfait
        first = np.flatnonzero(ok)[0]
    else:                                     # sinon meilleur compromis
        penalty = (
            np.abs(np.clip(WINDOW["freq"][0]-med_freq,0,None)) +
            np.abs(np.clip(med_freq-WINDOW["freq"][1],0,None)) +
            np.abs(np.clip(WINDOW["let"][0]-med_let,0,None))  +
            np.abs(np.clip(med_let-WINDOW["let"][1],0,None))  +
            np.abs(np.clip(WINDOW["pho"][0]-med_pho,0,None))  +
            np.abs(np.clip(med_pho-WINDOW["pho"][1],0,None))
        )
        first = penalty.argmin()
        st.warning("Un groupe n'obtient pas des médianes parfaites : "
                   f"pénalité {penalty[first]:.3f}")

    chosen_idx = idx_mat[first]
    return pool.iloc[chosen_idx]

@st.cache_data(show_spinner="Sélection vectorisée des 80 mots…")
def pick_stimuli():
    rng = np.random.default_rng()
    forbidden=set(); final=[]
    for name, m in GROUPS:
        sample = select_group(m, forbidden, rng)
        final.extend(sample.word.tolist())
        forbidden.update(sample.word)
    random.shuffle(final)
    return final

STIMULI = pick_stimuli()   # ← ≤ 0,1 s sur 4 600 mots

# ───────── 3. PROTOCOLE VISUEL (identique) ─────────
CYCLE, START, STEP = 350, 14, 14

if "page" not in st.session_state: st.session_state.page="intro"
if st.session_state.page=="intro":
    st.title("EXPERIMENT 3 : mots masqués (sélection vectorisée)")
    if st.button("Démarrer"):
        st.session_state.page="exp"; st.experimental_rerun()
else:
    html=f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
           font-family:'Courier New',monospace}}
#scr{{font-size:60px;user-select:none}}
#ans{{display:none;font-size:48px;width:60%;text-align:center}}
</style></head>
<body id="body" tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());
const W={json.dumps(STIMULI)},C={CYCLE},S={START},P={STEP};
let i=0,res=[],scr=document.getElementById('scr'),ans=document.getElementById('ans');
function trial(){{
 if(i>=W.length){{fin();return;}}
 const w=W[i],m='#'.repeat(w.length);let sd=S,md=C-sd,t0=performance.now(),run=true,t1,t2;
 (function loop(){{if(!run)return;scr.textContent=w;
  t1=setTimeout(()=>{{if(!run)return;scr.textContent=m;
    t2=setTimeout(()=>{{if(run){{sd+=P;md=Math.max(0,C-sd);loop();}}}},md);
  }},sd);}})();
 window.addEventListener('keydown',function onSpace(e){{
  if(e.code==='Space'&&run){{run=false;clearTimeout(t1);clearTimeout(t2);
    const rt=Math.round(performance.now()-t0);
    window.removeEventListener('keydown',onSpace);
    scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
    ans.addEventListener('keydown',function onEnter(ev){{
      if(ev.key==='Enter'){{ev.preventDefault();
        res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
        ans.removeEventListener('keydown',onEnter);ans.style.display='none';i++;trial();
      }}
    }});
  }} }});
}}
function fin(){{
 scr.style.fontSize='40px';scr.textContent='Merci ! Fin.';
 const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
 const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
 a.download='results.csv';a.textContent='Télécharger les résultats';
 a.style.fontSize='32px';a.style.marginTop='30px';document.body.appendChild(a);
}}
trial();
</script></body></html>
"""
    components.html(html, height=650, scrolling=False)
