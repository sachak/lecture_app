# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots tirés dans Lexique 3.83 (onglet Feuil1)
  • 20 OLD20  < 2,65   • 20 OLD20 > 2,65
  • 20 PLD20  < 2,00   • 20 PLD20 > 2,00
Protocole mot / masque ##### (+14 ms par cycle sur le mot).
CSV final séparé par « ; » (compatible Excel FR).
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------------
# 1.  LEXIQUE : lecture + tirage aléatoire (sans doublon)
# ------------------------------------------------------------------
LEXIQUE_FILE = "Lexique383.xlsb"     # changez si besoin
SHEET_NAME   = "Feuil1"              # nom de l’onglet

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

    # Renommage générique des colonnes
    ren = {}
    for col in df.columns:
        c = col.lower()
        if "étiquettes" in c or "etiquettes" in c or "word" in c or "ortho" in c:
            ren[col] = "word"
        elif "old20" in c: ren[col] = "old20"
        elif "pld20" in c: ren[col] = "pld20"
    df = df.rename(columns=ren)

    needed = {"word", "old20", "pld20"}
    if not needed.issubset(df.columns):
        st.error(f"Colonnes manquantes : {needed}"); st.stop()

    df["word"] = df["word"].str.upper()
    for c in ("old20", "pld20"):
        df[c] = df[c].astype(str).str.replace(",", ".", regex=False).astype(float)
    df = df.dropna(subset=["word", "old20", "pld20"])
    return df

@st.cache_data(show_spinner="Sélection des 80 mots…")
def pick_stimuli() -> list[str]:
    df   = load_lexique(pathlib.Path(LEXIQUE_FILE))
    rng  = random.Random()
    chosen = set()

    def _pick(sub, n):
        pool = sub.loc[~sub.word.isin(chosen)]
        if len(pool) < n:
            st.error("Pas assez de mots uniques pour satisfaire les critères."); st.stop()
        sample = pool.sample(n, random_state=rng.randint(0, 1_000_000)).word.tolist()
        chosen.update(sample)
        return sample

    low_old  = _pick(df[df.old20  < 2.65], 20)
    high_old = _pick(df[df.old20  > 2.65], 20)
    low_pld  = _pick(df[df.pld20  < 2.00], 20)
    high_pld = _pick(df[df.pld20  > 2.00], 20)

    words = low_old + high_old + low_pld + high_pld
    rng.shuffle(words)
    return words

STIMULI = pick_stimuli()

# ------------------------------------------------------------------
# 2.  Paramètres temporels
# ------------------------------------------------------------------
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ------------------------------------------------------------------
# 3.  Interface Streamlit
# ------------------------------------------------------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE = "<style>#MainMenu,header,footer{visibility:hidden}.css-1d391kg{display:none;}</style>"

if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# --------------------------- PAGE INTRO ---------------------------
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.markdown("80 mots tirés aléatoirement dans **Lexique 3.83 / Feuil1**.")
    st.markdown("""
1. Fixez le centre.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Tapez le mot et validez par **Entrée**.  
""")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ------------------------ PAGE EXPÉRIENCE ------------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE, unsafe_allow_html=True)

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
 html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
           background:#fff;font-family:'Courier New',monospace;}}
 #scr{{font-size:60px;user-select:none;}}
 #ans{{display:none;font-size:48px;width:60%;text-align:center;}}
</style>
</head>
<body id="body" tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load', () => document.getElementById('body').focus());

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS};
const START = {START_MS};
const STEP  = {STEP_MS};

let idx = 0;
let results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

function runTrial() {{
    if (idx >= WORDS.length) {{ endExp(); return; }}
    const word = WORDS[idx];
    const mask = '#'.repeat(word.length);
    let stimDur = START;
    let maskDur = CYCLE - stimDur;
    let t0 = performance.now();
    let running = true;
    let to1 = null, to2 = null;

    function oneCycle() {{
        if (!running) return;
        scr.textContent = word;
        to1 = setTimeout(() => {{
            if (!running) return;
            scr.textContent = mask;
            to2 = setTimeout(() => {{
                if (running) {{
                    stimDur += STEP;
                    maskDur = Math.max(0, CYCLE - stimDur);
                    oneCycle();
                }}
            }}, maskDur);
        }}, stimDur);
    }}
    oneCycle();

    function onSpace(ev) {{
        if (ev.code === 'Space' && running) {{
            running = false;
            clearTimeout(to1);
            clearTimeout(to2);
            const rt = Math.round(performance.now() - t0);
            window.removeEventListener('keydown', onSpace);

            scr.textContent = '';
            ans.style.display = 'block';
            ans.value = '';
            ans.focus();

            ans.addEventListener('keydown', function onEnter(e) {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    results.push({{word: word, rt_ms: rt, response: ans.value.trim()}});
                    ans.removeEventListener('keydown', onEnter);
                    ans.style.display = 'none';
                    idx += 1;
                    runTrial();
                }}
            }});
        }}
    }}
    window.addEventListener('keydown', onSpace);
}}

function endExp() {{
    scr.style.fontSize = '40px';
    scr.textContent = 'Merci ! Fin de l\\'expérience.';

    const SEP = ';';
    const header = ['word','rt_ms','response'].join(SEP) + '\\n';
    const rows   = results.map(r => [r.word, r.rt_ms, r.response].join(SEP)).join('\\n');
    const blob   = new Blob([header + rows], {{type:'text/csv;charset=utf-8'}});
    const url    = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'results.csv';
    a.textContent = 'Télécharger les résultats (.csv)';
    a.style.fontSize = '32px';
    a.style.marginTop = '30px';
    document.body.appendChild(a);
}}

runTrial();
</script>
</body>
</html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
