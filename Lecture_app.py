# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – Streamlit (80 mots Lexique 3.83)
- 20 OLD20<2,65 ; 20 OLD20≥2,65 ; 20 PLD20<2 ; 20 PLD20≥2
- Protocole mot/masque + réponse.
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------
# 1. CHARGEMENT DU LEXIQUE & SÉLECTION DES MOTS
# ------------------------------------------------------
LEXIQUE_FILE = "Lexique383.xlsb"   # ou .xlsx / .csv
SHEET_NAME   = "Feuil1"            # ← nom de l’onglet

def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Fichier {path} introuvable."); st.stop()

    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path, sep=";", decimal=",", dtype=str)
    elif ext in (".xlsb", ".xlsx", ".xls"):
        engine = "pyxlsb" if ext == ".xlsb" else None
        df = pd.read_excel(path, sheet_name=SHEET_NAME, engine=engine, dtype=str)
    else:
        st.error("Format non pris en charge (csv, xls, xlsx, xlsb)."); st.stop()

    # Harmonisation des noms de colonnes
    rename = {}
    for col in df.columns:
        c = col.lower().strip()
        if "étiquettes" in c or "etiquettes" in c or "ortho" in c or "word" in c:
            rename[col] = "word"
        elif "old20" in c: rename[col] = "old20"
        elif "pld20" in c: rename[col] = "pld20"
    df = df.rename(columns=rename)

    needed = {"word", "old20", "pld20"}
    if not needed.issubset(df.columns):
        st.error(f"Colonnes manquantes : {needed}"); st.stop()

    df["word"]  = df["word"].str.upper()
    for c in ("old20", "pld20"):
        df[c] = (df[c].astype(str).str.replace(",", ".", regex=False).astype(float))
    df = df.dropna(subset=["word", "old20", "pld20"])
    return df

@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    df = load_lexique(pathlib.Path(LEXIQUE_FILE))
    rng = random.Random()

    def _sel(sub, n): return sub.sample(n, random_state=rng.randint(0,1e6)).word.tolist()
    stimuli = (
        _sel(df[df.old20 < 2.65] , 20) +
        _sel(df[df.old20 >=2.65], 20) +
        _sel(df[df.pld20 < 2.00] , 20) +
        _sel(df[df.pld20 >=2.00], 20)
    )
    rng.shuffle(stimuli)
    return stimuli

STIMULI = pick_stimuli()

# ------------------------------------------------------
# 2.   PARAMÈTRES TEMPORELS
# ------------------------------------------------------
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ------------------------------------------------------
# 3.   INTERFACE STREAMLIT
# ------------------------------------------------------
st.set_page_config(layout="wide", page_title="Expérience 3")
HIDE = "<style>#MainMenu, header, footer{visibility:hidden}.css-1d391kg{display:none;}</style>"

if "stage" not in st.session_state: st.session_state.stage = "intro"

# ----------------------- INTRO ------------------------
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 – mots masqués")
    st.markdown("80 mots tirés dans Lexique 3.83 (onglet **Feuil1**).")
    st.markdown("""
Procédure :
1. Fixez le centre.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Tapez le mot et validez par **Entrée**.  
""")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage="exp"; st.experimental_rerun()

# --------------------- EXPÉRIENCE ---------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE, unsafe_allow_html=True)
    html=f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
           background:#fff;font-family:"Courier New",monospace}}
 #scr{{font-size:60px;user-select:none}}
 #ans{{display:none;font-size:48px;width:60%;text-align:center}}
</style></head><body id="body" tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());
const WORDS={json.dumps(STIMULI)};
const CYCLE={CYCLE_MS},START={START_MS},STEP={STEP_MS};
let i=0,res=[];const scr=document.getElementById('scr'),ans=document.getElementById('ans');
function trial(){{
 if(i>=WORDS.length){{end();return}}
 const w=WORDS[i],mask="#".repeat(w.length);
 let sd=START,md=CYCLE-sd,t0=performance.now(),go=true,t1=null,t2=null;
 function loop(){{if(!go)return;
   scr.textContent=w;
   t1=setTimeout(()=>{{if(!go)return;scr.textContent=mask;
     t2=setTimeout(()=>{{if(go){{sd+=STEP;md=Math.max(0,CYCLE-sd);loop();}}}},md);
   }},sd);}}
 loop();
 function onSpace(e){{if(e.code==='Space'&&go){{go=false;clearTimeout(t1);clearTimeout(t2);
   const rt=Math.round(performance.now()-t0);window.removeEventListener('keydown',onSpace);
   scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
   ans.addEventListener('keydown',function onEnter(ev){{if(ev.key==='Enter'){{ev.preventDefault();
     res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
     ans.removeEventListener('keydown',onEnter);ans.style.display='none';i++;trial();}}}});
 }}}
 window.addEventListener('keydown',onSpace);}
function end(){{scr.style.fontSize='40px';scr.textContent='Merci ! Fin.';
 const SEP=';';const csv=['word','rt_ms','response'].join(SEP)+'\\n'+
  res.map(r=>[r.word,r.rt_ms,r.response].join(SEP)).join('\\n');
 const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));
 a.download='results.csv';a.textContent='Télécharger les résultats (.csv)';
 a.style.fontSize='32px';a.style.marginTop='30px';document.body.appendChild(a);}}
trial();
</script></body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
