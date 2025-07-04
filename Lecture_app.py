# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots tirés dans Lexique 3.83 (CSV)
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ─────────────────── 1. FICHIER LEXIQUE ───────────────────
LEXIQUE_FILE = "Lexique383.csv"     # même dossier que ce script

def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    """Lit le CSV (UTF-8 ou latin-1) et renvoie word / old20 / pld20."""
    if not path.exists():
        st.error(f"Fichier {path} introuvable."); st.stop()

    # tentative UTF-8 puis fallback latin-1
    for enc in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(
                path, sep=";", decimal=",", encoding=enc,
                dtype=str, engine="python", on_bad_lines="skip"
            )
            break
        except UnicodeDecodeError:
            df = None
    if df is None:
        st.error("Impossible de lire le CSV (encodage inconnu)."); st.stop()

    # renommage souple des colonnes
    ren = {}
    for col in df.columns:
        low = col.lower()
        if any(k in low for k in ("étiquettes", "etiquettes", "ortho", "word")):
            ren[col] = "word"
        elif "old20" in low: ren[col] = "old20"
        elif "pld20" in low: ren[col] = "pld20"
    df = df.rename(columns=ren)

    need = {"word", "old20", "pld20"}
    if not need.issubset(df.columns):
        st.error(f"Colonnes manquantes : {need}"); st.stop()

    df["word"] = df["word"].str.upper()
    for c in ("old20", "pld20"):
        df[c] = (df[c].astype(str)
                        .str.replace(",", ".", regex=False)
                        .astype(float))
    df = df.dropna(subset=["word", "old20", "pld20"])
    return df

@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    df = load_lexique(pathlib.Path(LEXIQUE_FILE))
    rng = random.Random()
    chosen = set()

    def sample(sub, n):
        pool = sub.loc[~sub.word.isin(chosen)]
        if len(pool) < n:
            st.error("Pas assez de mots uniques pour cette catégorie."); st.stop()
        pick = pool.sample(n, random_state=rng.randint(0, 1_000_000)).word.tolist()
        chosen.update(pick); return pick

    low_old  = sample(df[df.old20  < 2.65], 20)
    high_old = sample(df[df.old20 >= 2.65], 20)
    low_pld  = sample(df[df.pld20  < 2.00], 20)
    high_pld = sample(df[df.pld20 >= 2.00], 20)

    words = low_old + high_old + low_pld + high_pld
    rng.shuffle(words)
    return words

STIMULI = pick_stimuli()

# ─────────────────── 2. PARAMÈTRES TEMPORELS ───────────────────
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ─────────────────── 3. INTERFACE STREAMLIT ───────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE = "<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none;}</style>"

if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# --------------------------- INTRO ---------------------------
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.markdown("80 mots tirés dans Lexique 3.83 (CSV).")
    st.markdown("""
1. Fixez le centre.  
2. Appuyez sur **ESPACE** quand vous reconnaissez le mot.  
3. Tapez le mot puis **Entrée**.  
""")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"; st.experimental_rerun()

# ------------------------- EXPÉRIENCE ------------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE, unsafe_allow_html=True)

    html = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
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

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

let i=0,res=[];
const scr=document.getElementById('scr'), ans=document.getElementById('ans');

function trial(){{
  if(i>=WORDS.length){{fin();return;}}
  const w=WORDS[i], mask='#'.repeat(w.length);
  let sd=START, md=CYCLE-sd, t0=performance.now(), go=true, t1=null, t2=null;

  function loop(){{if(!go)return;
    scr.textContent=w;
    t1=setTimeout(()=>{{if(!go)return;
      scr.textContent=mask;
      t2=setTimeout(()=>{{if(go){{sd+=STEP;md=Math.max(0,CYCLE-sd);loop();}}}}, md);
    }}, sd);}}
  loop();

  function onSpace(e){{if(e.code==='Space'&&go){{go=false;
    clearTimeout(t1);clearTimeout(t2);
    const rt=Math.round(performance.now()-t0);
    window.removeEventListener('keydown',onSpace);
    scr.textContent=''; ans.style.display='block'; ans.value=''; ans.focus();
    ans.addEventListener('keydown',function onEnter(ev){{if(ev.key==='Enter'){{ev.preventDefault();
      res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
      ans.removeEventListener('keydown',onEnter); ans.style.display='none'; i++; trial();}}}});
  }}}}
  window.addEventListener('keydown',onSpace);
}}

function fin() {{
  scr.style.fontSize='40px'; scr.textContent='Merci ! Fin.';
  const SEP=';';
  const csv=['word','rt_ms','response'].join(SEP)+'\\n'+
            res.map(r=>[r.word,r.rt_ms,r.response].join(SEP)).join('\\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));
  a.download='results.csv'; a.textContent='Télécharger les résultats (.csv)';
  a.style.fontSize='32px'; a.style.marginTop='30px'; document.body.appendChild(a);
}}

trial();
</script></body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
