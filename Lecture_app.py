# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – sélection adaptative : élargit les fenêtres jusqu’à obtenir
80 mots uniques (4×20).
"""

import json, random, pathlib, pandas as pd, numpy as np, streamlit as st
import streamlit.components.v1 as components

# ───────────── CONFIG STREAMLIT ─────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE = "<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none}</style>"
st.markdown(HIDE, unsafe_allow_html=True)

# ───────────── 1. LEXIQUE ─────────────
FILE = "Lexique383.csv"          # UTF-8 ; séparateur « ; »

def load_lex():
    df = pd.read_csv(FILE, sep=";", decimal=",", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")
    ren={}; cols=df.columns.str.lower()
    for c in df.columns:
        l=c.lower()
        if "étiquettes" in l or "ortho" in l or "word" in l: ren[c]="word"
        elif "old20" in l:  ren[c]="old20"
        elif "pld20" in l:  ren[c]="pld20"
        elif "freqlemfilms2" in l: ren[c]="freq"
        elif "nblettres" in l: ren[c]="let"
        elif "nbphons" in l: ren[c]="pho"
    df=df.rename(columns=ren)
    need={"word","old20","pld20","freq","let","pho"}
    if not need.issubset(df.columns): st.error("Colonnes manquantes"); st.stop()
    df.word=df.word.str.upper()
    for c in need-{"word"}: df[c]=df[c].str.replace(",","." ,regex=False).astype(float)
    return df.dropna()

LEX=load_lex()

# ───────────── 2. CRITÈRES FIXES OLD / PLD ─────────────
MASKS = {
    "LOW_OLD" : LEX.old20 < 1.11,
    "HIGH_OLD": LEX.old20 > 3.79,
    "LOW_PLD" : LEX.pld20 < 0.70,
    "HIGH_PLD": LEX.pld20 > 3.20,
}

# ───────────── 3. FENÊTRES INITIALES & FONCTIONS ─────────────
INIT = dict(freq=(0.44,2.94), let=(8.5,9.5), pho=(6.5,7.5))

def medians(sample):
    return dict(freq=sample.freq.median(),
                let =sample.let .median(),
                pho =sample.pho .median())

def inside(meds, win):
    return all(win[k][0] <= meds[k] <= win[k][1] for k in win)

# ───────────── 4. ALGO : élargissement progressif ─────────────
def enlarge(win, step):
    return {k:(v[0]-step, v[1]+step) for k,v in win.items()}

@st.cache_data(show_spinner="Sélection adaptative des 80 mots…")
def pick():
    rng=np.random.default_rng()
    step=0.0
    while step<=2.0:                    # on ouvre au max de ±2
        win=enlarge(INIT, step)
        chosen=set(); final=[]; ok=True
        for name,mask in MASKS.items():
            pool=LEX.loc[mask & ~LEX.word.isin(chosen)].reset_index(drop=True)
            if len(pool)<20: ok=False; break
            idx=rng.choice(len(pool),size=(10_000,20),replace=False)
            meds=medians(pool.iloc[idx[0]])
            good=None
            # vérif vectorisée
            med_freq=np.median(pool.freq.values[idx],axis=1)
            med_let =np.median(pool.let .values[idx],axis=1)
            med_pho =np.median(pool.pho .values[idx],axis=1)
            ok_rows=((win["freq"][0]<=med_freq)&(med_freq<=win["freq"][1])&
                     (win["let" ][0]<=med_let )&(med_let <=win["let" ][1])&
                     (win["pho" ][0]<=med_pho )&(med_pho <=win["pho" ][1]))
            if ok_rows.any():
                good=pool.iloc[idx[np.flatnonzero(ok_rows)[0]]]
            else:                           # meilleur compromis
                penalty=(np.clip(win["freq"][0]-med_freq,0,None)+
                         np.clip(med_freq-win["freq"][1],0,None)+
                         np.clip(win["let"][0]-med_let,0,None)+
                         np.clip(med_let-win["let"][1],0,None)+
                         np.clip(win["pho"][0]-med_pho,0,None)+
                         np.clip(med_pho-win["pho"][1],0,None))
                best=penalty.argmin()
                good=pool.iloc[idx[best]]
            final.extend(good.word); chosen.update(good.word)
        if ok and len(final)==80:          # succès
            if step>0:
                st.info(f"Fenêtres élargies de ±{step:.1f} pour satisfaire l’unicité.")
            random.shuffle(final)
            return final
        step+=0.1                          # élargit de 0.1 et recommence
    st.error("Impossible même après élargissement ±2."); st.stop()

STIMULI=pick()   # << très rapide (≤1 s)

# ───────── 5. PROTOCOLE (identique) ─────────
C,S,P=350,14,14
if "page" not in st.session_state: st.session_state.page="intro"
if st.session_state.page=="intro":
    st.title("EXPERIMENT 3 – mots masqués (sélection adaptative)")
    if st.button("Démarrer"): st.session_state.page="exp"; st.experimental_rerun()
else:
    html=f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
font-family:'Courier New',monospace}}#scr{{font-size:60px}}#ans{{display:none;font-size:48px;width:60%;text-align:center}}</style></head>
<body id="body" tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());
const W={json.dumps(STIMULI)},C={C},S={S},P={P};
let i=0,res=[],scr=document.getElementById('scr'),ans=document.getElementById('ans');
function trial(){{if(i>=W.length){{fin();return;}}const w=W[i],m='#'.repeat(w.length);
let sd=S,md=C-sd,t0=performance.now(),run=true,t1,t2;(function loop(){{if(!run)return;scr.textContent=w;
t1=setTimeout(()=>{{if(!run)return;scr.textContent=m;
t2=setTimeout(()=>{{if(run){{sd+=P;md=Math.max(0,C-sd);loop();}}}},md);}},sd);}})();
window.addEventListener('keydown',function onSpace(e){{if(e.code==='Space'&&run){{run=false;clearTimeout(t1);clearTimeout(t2);
const rt=Math.round(performance.now()-t0);window.removeEventListener('keydown',onSpace);scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
ans.addEventListener('keydown',function onEnter(ev){{if(ev.key==='Enter'){{ev.preventDefault();res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
ans.removeEventListener('keydown',onEnter);ans.style.display='none';i++;trial();}}}});}}}});
}}
function fin(){{scr.style.fontSize='40px';scr.textContent='Merci !';
const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
a.download='results.csv';a.textContent='Télécharger les résultats';a.style.fontSize='32px';a.style.marginTop='30px';document.body.appendChild(a);}}
trial();
</script></body></html>
"""
    components.html(html,height=650,scrolling=False)
