# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 : sélection adaptative des 80 mots (4×20).
CSV UTF-8, séparateur « ; », décimales « . ».
Fenêtres élargies automatiquement jusqu’à réussite.
"""

import json, random, pathlib, pandas as pd, numpy as np, streamlit as st
import streamlit.components.v1 as components

# =============== 0. CONFIG STREAMLIT ===============
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}"
    ".css-1d391kg{display:none}</style>",
    unsafe_allow_html=True
)

# =============== 1. LEXIQUE (. comme décimale) ===============
CSV_FILE = "Lexique383.csv"      # placé à côté du script

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")

    ren = {}
    for col in df.columns:
        l = col.lower()
        if "étiquettes" in l or "ortho" in l or "word" in l:   ren[col] = "word"
        elif "old20" in l:           ren[col] = "old20"
        elif "pld20" in l:           ren[col] = "pld20"
        elif "freqlemfilms2" in l:   ren[col] = "freq"
        elif "nblettres" in l:       ren[col] = "let"
        elif "nbphons" in l:         ren[col] = "pho"
    df = df.rename(columns=ren)

    need = {"word", "old20", "pld20", "freq", "let", "pho"}
    if not need.issubset(df.columns):
        st.error(f"Colonnes manquantes : {need - set(df.columns)}")
        st.stop()

    df.word = df.word.str.upper()
    for c in need - {"word"}:
        df[c] = df[c].astype(float)

    return df.dropna()

LEX = load_lexique()

# =============== 2. CRITÈRES ET FENÊTRES ===============
MASKS = {
    "LOW_OLD" : LEX.old20 < 1.11,
    "HIGH_OLD": LEX.old20 > 3.79,
    "LOW_PLD" : LEX.pld20 < 0.70,
    "HIGH_PLD": LEX.pld20 > 3.20,
}

BASE_WIN = dict(freq=(0.44, 2.94),
                let =(8.5 , 9.5 ),
                pho =(6.5 , 7.5 ))

def enlarge(win, step):
    return {k: (v[0]-step, v[1]+step) for k, v in win.items()}

# =============== 3. SÉLECTION ADAPTATIVE (boucle élargissement) ===============
@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli():
    rng = np.random.default_rng()
    step = 0.0
    while step <= 2.0:                     # élargit max ±2
        win = enlarge(BASE_WIN, step)
        chosen, final = set(), []
        success = True

        for name, mask in MASKS.items():
            pool = LEX.loc[mask & ~LEX.word.isin(chosen)].reset_index(drop=True)
            if len(pool) < 20:
                success = False
                break

            # --------- tirages aléatoires (10 000 listes de 20 indices) ----------
            idx_samples = np.array(
                [rng.choice(len(pool), size=20, replace=False) for _ in range(10_000)]
            )

            med_freq = np.median(pool.freq.values[idx_samples], axis=1)
            med_let  = np.median(pool.let .values[idx_samples], axis=1)
            med_pho  = np.median(pool.pho .values[idx_samples], axis=1)

            ok = ((win["freq"][0] <= med_freq) & (med_freq <= win["freq"][1]) &
                  (win["let" ][0] <= med_let ) & (med_let  <= win["let" ][1]) &
                  (win["pho" ][0] <= med_pho ) & (med_pho  <= win["pho" ][1]))

            if ok.any():                                    # échantillon parfait
                best_idx = np.flatnonzero(ok)[0]
            else:                                           # meilleur compromis
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

        if success and len(final) == 80:
            if step > 0:
                st.info(f"Fenêtres élargies de ±{step:.1f} pour respecter unicité + médianes.")
            random.shuffle(final)
            return final

        step += 0.1

    st.error("Impossible de constituer 80 mots uniques même après élargissement ±2.")
    st.stop()

STIMULI = pick_stimuli()

# =============== 4. PROTOCOLE VISUEL ===============
CYCLE, START, STEP = 350, 14, 14
if "page" not in st.session_state: st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPERIMENT 3 – mots masqués (CSV décimal '.') ")
    if st.button("Démarrer l’expérience"):
        st.session_state.page = "exp"
        st.experimental_rerun()

else:  # page expérience
    html = f"""
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
let i=0,res=[];
const scr=document.getElementById('scr'), ans=document.getElementById('ans');

function run(){{ if(i>=W.length){{fin();return;}}
  const w=W[i],m='#'.repeat(w.length);
  let sd=S,md=C-sd,t0=performance.now(),on=true,t1,t2;
  (function loop(){{ if(!on)return;
    scr.textContent=w;
    t1=setTimeout(()=>{{ if(!on)return;
       scr.textContent=m;
       t2=setTimeout(()=>{{ if(on){{ sd+=P;md=Math.max(0,C-sd);loop(); }} }},md);
    }},sd);
  }})();
  window.addEventListener('keydown',function sp(e){{ if(e.code==='Space'&&on){{
        on=false;clearTimeout(t1);clearTimeout(t2);
        const rt=Math.round(performance.now()-t0);
        window.removeEventListener('keydown',sp);
        scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
        ans.addEventListener('keydown',function ent(ev){{ if(ev.key==='Enter'){{
           ev.preventDefault();
           res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
           ans.removeEventListener('keydown',ent);
           ans.style.display='none';i++;run();
        }}}); }} }});
}}
function fin(){{ scr.style.fontSize='40px';scr.textContent='Merci !';
  const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
  a.download='results.csv';
  a.textContent='Télécharger les résultats';
  a.style.fontSize='32px';a.style.marginTop='30px';
  document.body.appendChild(a);
}}
run();
</script></body></html>
"""
    components.html(html, height=650, scrolling=False)
