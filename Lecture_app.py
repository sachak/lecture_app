# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots tirés dans Lexique 3.83 (CSV UTF-8)
  • 20 OLD20  < 2,65   • 20 OLD20 ≥ 2,65
  • 20 PLD20  < 2,00   • 20 PLD20 ≥ 2,00
Chaque mot est unique. Protocole mot / masque #####.
CSV final « ; » (Excel FR).
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ────────────────── 0. CONFIG PAGE  (doit être tout en haut) ──────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE_CSS = """
<style>
#MainMenu,header,footer{visibility:hidden;}
.css-1d391kg{display:none;}   /* barre latérale Streamlit */
</style>
"""

# ────────────────── 1. CHARGEMENT DU LEXIQUE ──────────────────
LEXIQUE_FILE = "Lexique383.csv"     # CSV UTF-8, séparateur « ; »

def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Fichier {path} introuvable."); st.stop()

    try:
        df = pd.read_csv(
            path,
            sep=";",              # séparateur Excel FR
            decimal=",",          # virgule décimale
            encoding="utf-8",     # encodage unique
            dtype=str,
            engine="python",
            on_bad_lines="skip"
        )
    except UnicodeDecodeError:
        st.error(
            "Le fichier n'est pas en UTF-8. "
            "Ouvrez-le dans Excel ou LibreOffice et enregistrez-le "
            "en CSV UTF-8 avant de relancer.")
        st.stop()

    # Renommage souple des colonnes
    rename = {}
    for col in df.columns:
        low = col.lower()
        if any(k in low for k in ("étiquettes", "etiquettes", "ortho", "word")):
            rename[col] = "word"
        elif "old20" in low:
            rename[col] = "old20"
        elif "pld20" in low:
            rename[col] = "pld20"
    df = df.rename(columns=rename)

    need = {"word", "old20", "pld20"}
    if not need.issubset(df.columns):
        st.error(f"Colonnes manquantes : {need}. "
                 "Vérifiez l’en-tête du CSV."); st.stop()

    # Nettoyage / conversion
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
        picked = pool.sample(n, random_state=rng.randint(0, 1_000_000)).word.tolist()
        chosen.update(picked)
        return picked

    low_old  = sample(df[df.old20  < 2.65], 20)
    high_old = sample(df[df.old20 >= 2.65], 20)
    low_pld  = sample(df[df.pld20  < 2.00], 20)
    high_pld = sample(df[df.pld20 >= 2.00], 20)

    stim = low_old + high_old + low_pld + high_pld
    rng.shuffle(stim)
    return stim

STIMULI = pick_stimuli()

# ────────────────── 2. PARAMÈTRES TEMPORELS ──────────────────
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ────────────────── 3. INTERFACE STREAMLIT ──────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# -------------------------- INTRO ---------------------------
if st.session_state.stage == "intro":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.write("80 mots tirés aléatoirement dans Lexique 3.83 (CSV UTF-8).")
    st.markdown("""
1. Fixez le centre de l’écran.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Tapez le mot puis validez avec **Entrée**.  
""")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ------------------------ EXPÉRIENCE ------------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)

    html = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body {{
   height:100%; margin:0; display:flex; align-items:center; justify-content:center;
   background:#ffffff; font-family:'Courier New',monospace;
 }}
 #scr {{ font-size:60px; user-select:none; }}
 #ans {{ display:none; font-size:48px; width:60%; text-align:center; }}
</style>
</head>
<body id="body" tabindex="0">
  <div id="scr"></div>
  <input id="ans" autocomplete="off" />
<script>
/* focus immédiat dans l'iframe */
window.addEventListener('load', ()=>document.getElementById('body').focus());

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

let idx = 0, results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

function runTrial() {{
  if (idx >= WORDS.length) {{ end(); return; }}
  const word = WORDS[idx];
  const mask = '#'.repeat(word.length);

  let sd = START, md = CYCLE - sd, t0 = performance.now(), active = true;
  let to1 = null, to2 = null;

  function loop() {{
    if (!active) return;
    scr.textContent = word;
    to1 = setTimeout(()=>{{
      if (!active) return;
      scr.textContent = mask;
      to2 = setTimeout(()=>{{ if (active) {{ sd += STEP; md = Math.max(0,CYCLE-sd); loop(); }} }}, md);
    }}, sd);
  }}
  loop();

  function onSpace(e) {{
    if (e.code === 'Space' && active) {{
      active = false;
      clearTimeout(to1); clearTimeout(to2);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener('keydown', onSpace);

      scr.textContent = '';
      ans.style.display = 'block';
      ans.value = '';
      ans.focus();

      ans.addEventListener('keydown', function onEnter(ev) {{
        if (ev.key === 'Enter') {{
          ev.preventDefault();
          results.push({{word:word, rt_ms:rt, response:ans.value.trim()}});
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

function end() {{
  scr.style.fontSize = '40px';
  scr.textContent = 'Merci ! Fin de l’expérience.';

  const SEP=';';
  const csv = ['word','rt_ms','response'].join(SEP)+'\\n'+
              results.map(r=>[r.word,r.rt_ms,r.response].join(SEP)).join('\\n');
  const blob = new Blob([csv],{{type:'text/csv;charset=utf-8'}});
  const url  = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url; a.download = 'results.csv';
  a.textContent = 'Télécharger les résultats (.csv)';
  a.style.fontSize = '32px'; a.style.marginTop = '30px';
  document.body.appendChild(a);
}}

runTrial();
</script>
</body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
