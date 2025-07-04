# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots tirés dans Lexique 3.83 (CSV UTF-8)

Groupes (20 mots chacun, tous différents)
  1. OLD20 < 1.11
  2. OLD20 > 3.79
  3. PLD20 < 0.70
  4. PLD20 > 3.20

Chacun des 4 groupes doit satisfaire SANS approximation :
  0.44 ≤ médiane(freqlemfilms2) ≤ 2.94
  8.5  ≤ médiane(nblettres)     ≤ 9.5
  6.5  ≤ médiane(nbphons)       ≤ 7.5
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───────── 0. configuration Streamlit (toujours avant le 1er st.*) ─────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none}</style>",
    unsafe_allow_html=True,
)

# ───────── 1. lecture du CSV (UTF-8, ‘;’ comme séparateur) ─────────
LEXIQUE_FILE = "Lexique383.csv"          # placez le fichier à côté de app.py

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    ren = {}
    for c in df.columns:
        l = c.lower()
        if "étiquettes" in l or "ortho" in l or "word" in l: ren[c] = "word"
        elif "old20"      in l:  ren[c] = "old20"
        elif "pld20"      in l:  ren[c] = "pld20"
        elif "freqlemfilms2" in l: ren[c] = "freq"
        elif "nblettres"  in l:  ren[c] = "letters"
        elif "nbphons"    in l:  ren[c] = "phons"
    df = df.rename(columns=ren)

    need = {"word","old20","pld20","freq","letters","phons"}
    if not need.issubset(df.columns):
        st.error(f"Colonnes manquantes : {need - set(df.columns)}"); st.stop()

    df["word"] = df.word.str.upper()
    for c in need - {"word"}:
        df[c] = df[c].str.replace(",",".",regex=False).astype(float)

    return df.dropna()

LEX = load_lexique(pathlib.Path(LEXIQUE_FILE))

# ───────── 2. critères & tirage rapide ─────────
BOUNDS = dict(freq=(0.44,2.94), letters=(8.5,9.5), phons=(6.5,7.5))

def medians_ok(df: pd.DataFrame) -> bool:
    return all(lo <= df[col].median() <= hi for col,(lo,hi) in BOUNDS.items())

GROUPS = [
    ("LOW_OLD" , lambda d: d.old20 < 1.11),
    ("HIGH_OLD", lambda d: d.old20 > 3.79),
    ("LOW_PLD" , lambda d: d.pld20 < 0.70),
    ("HIGH_PLD", lambda d: d.pld20 > 3.20),
]

@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    rng = random.Random()
    chosen, final = set(), []

    for name, cond in GROUPS:
        pool = LEX.loc[cond(LEX) & ~LEX.word.isin(chosen)].copy()
        if len(pool) < 20:
            st.error(f"{name} : pas assez de candidats ({len(pool)})"); st.stop()

        for _ in range(300):          # 300 tirages max → < 0,05 s
            sample = pool.sample(20, random_state=rng.randint(0,999999))
            if medians_ok(sample):
                final.extend(sample.word.tolist())
                chosen.update(sample.word)
                break
        else:
            st.error(f"{name} : impossible de satisfaire les médianes en 300 essais"); st.stop()

    rng.shuffle(final)
    return final

STIMULI = pick_stimuli()          # ← ~200 ms avec 4 664 mots

# ───────── 3. paramètres temporels du protocole ─────────
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ───────── 4. interface + JavaScript de l’expérience ─────────
if "page" not in st.session_state: st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.write("80 mots (OLD20 / PLD20) avec médianes calibrées.")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

else:  # page == exp
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

const W   = {json.dumps(STIMULI)};
const C   = {CYCLE_MS}, S = {START_MS}, P = {STEP_MS};
let i=0,res=[];
const scr=document.getElementById('scr'), ans=document.getElementById('ans');

function trial(){{
 if(i>=W.length){{fin();return;}}
 const w=W[i], m='#'.repeat(w.length);
 let sd=S, md=C-sd, t0=performance.now(), run=true, t1, t2;

 (function loop(){{ if(!run)return;
   scr.textContent=w;
   t1=setTimeout(()=>{{ if(!run)return;
     scr.textContent=m;
     t2=setTimeout(()=>{{ if(run){{ sd+=P; md=Math.max(0,C-sd); loop(); }} }}, md);
   }}, sd);
 }})();

 function onSpace(e){{ if(e.code==='Space'&&run){{
   run=false; clearTimeout(t1); clearTimeout(t2);
   const rt=Math.round(performance.now()-t0);
   window.removeEventListener('keydown',onSpace);
   scr.textContent=''; ans.style.display='block'; ans.value=''; ans.focus();

   ans.addEventListener('keydown',function onEnter(ev){{
     if(ev.key==='Enter'){{
       ev.preventDefault();
       res.push({{word:w, rt_ms:rt, response:ans.value.trim()}});
       ans.removeEventListener('keydown',onEnter);
       ans.style.display='none'; i++; trial();
     }}
   }});
 }} }}
 window.addEventListener('keydown',onSpace);
}}

function fin(){{
 scr.style.fontSize='40px'; scr.textContent='Merci ! Fin.';
 const sep=';', csv=['word','rt_ms','response'].join(sep)+'\\n'+
           res.map(r=>[r.word,r.rt_ms,r.response].join(sep)).join('\\n');
 const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
 a.download='results.csv'; a.textContent='Télécharger les résultats';
 a.style.fontSize='32px'; a.style.marginTop='30px';
 document.body.appendChild(a);
}}

trial();
</script></body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
