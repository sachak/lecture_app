@@ -1,121 +1,136 @@
# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – 80 mots tirés dans Lexique 3.83 (CSV UTF-8)
  • 20 OLD20  < 2,65   • 20 OLD20 ≥ 2,65
  • 20 PLD20  < 2,00   • 20 PLD20 ≥ 2,00
Chaque mot est unique. Protocole mot / masque #####.
CSV final « ; » (Excel FR).
EXPÉRIENCE 3  – 80 mots tirés dans Lexique 3.83 (CSV UTF-8)

Groupes (20 mots chacun, sans doublon)              Contraintes médianes
-----------------------------------------------------------------------
1. OLD20  < 1.11                                   freqlemfilms2 ∈ [0.44 ; 2.94]
2. OLD20  > 3.79                                   nblettres     ∈ [8.5 ; 9.5]
3. PLD20  < 0.70                                   nbphons       ∈ [6.5 ; 7.5]
4. PLD20  > 3.20

Protocole : mot / masque ##### (+14 ms sur le mot à chaque cycle).
CSV final séparé par « ; ».
"""

import json, random, pathlib, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ────────────────── 0. CONFIG PAGE  (doit être tout en haut) ──────────────────
# ───────────────── 0. CONFIG PAGE – à appeler AVANT tout st.* ────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE_CSS = """
<style>
#MainMenu,header,footer{visibility:hidden;}
.css-1d391kg{display:none;}   /* barre latérale Streamlit */
.css-1d391kg{display:none;}
</style>
"""

# ────────────────── 1. CHARGEMENT DU LEXIQUE ──────────────────
LEXIQUE_FILE = "Lexique383.csv"     # CSV UTF-8, séparateur « ; »
# ───────────────── 1. CHARGER LE LEXIQUE ─────────────────────────────────────
LEXIQUE_FILE = "Lexique383.csv"     # CSV UTF-8 « ; » , décimales « , »

def load_lexique(path: pathlib.Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Fichier {path} introuvable."); st.stop()

    # lecture UTF-8
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
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8",
                         dtype=str, engine="python", on_bad_lines="skip")
    except UnicodeDecodeError:
        st.error(
            "Le fichier n'est pas en UTF-8. "
            "Ouvrez-le dans Excel ou LibreOffice et enregistrez-le "
            "en CSV UTF-8 avant de relancer.")
        st.stop()

    # Renommage souple des colonnes
    rename = {}
        st.error("Le CSV n'est pas en UTF-8. Ré-enregistrez-le puis relancez."); st.stop()

    # harmonisation des noms --------------------------------------------------
    mapping = {}
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
            mapping[col] = "word"
        elif "old20" in low:      mapping[col] = "old20"
        elif "pld20" in low:      mapping[col] = "pld20"
        elif "freqlemfilms2" in low: mapping[col] = "freq"
        elif "nblettres" in low:  mapping[col] = "letters"
        elif "nbphons" in low:    mapping[col] = "phons"
    df = df.rename(columns=mapping)

    required = {"word", "old20", "pld20", "freq", "letters", "phons"}
    if not required.issubset(df.columns):
        st.error(f"Colonnes manquantes : {required - set(df.columns)}"); st.stop()

    # mise au propre ----------------------------------------------------------
    df["word"] = df["word"].str.upper()
    for c in ("old20", "pld20"):
        df[c] = (df[c].astype(str)
                        .str.replace(",", ".", regex=False)
                        .astype(float))
    df = df.dropna(subset=["word", "old20", "pld20"])
    for col in ["old20", "pld20", "freq", "letters", "phons"]:
        df[col] = (df[col].astype(str)
                            .str.replace(",", ".", regex=False)
                            .astype(float))
    df = df.dropna(subset=list(required))
    return df

# ───────────────── 2. CRITÈRES DE SÉLECTION ────────────────────────────────
GROUPS = {
    "LOW_OLD":  lambda d: d.old20  < 1.11,
    "HIGH_OLD": lambda d: d.old20  > 3.79,
    "LOW_PLD":  lambda d: d.pld20  < 0.70,
    "HIGH_PLD": lambda d: d.pld20  > 3.20,
}
MEDIAN_OK = {
    "freq":   (0.44, 2.94),
    "letters":(8.5, 9.5),
    "phons":  (6.5, 7.5),
}

def medians_within(df: pd.DataFrame) -> bool:
    return all(mn <= df[col].median() <= mx for col,(mn,mx) in MEDIAN_OK.items())

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
    chosen: set[str] = set()
    final_list: list[str] = []

    for gname, cond in GROUPS.items():
        pool = df.loc[cond(df) & ~df.word.isin(chosen)].copy()
        if len(pool) < 20:
            st.error(f"Pas assez de mots pour {gname} après exclusion des doublons."); st.stop()

        # tirage itératif jusqu'à satisfaire les médianes
        max_tries = 20000
        for _ in range(max_tries):
            sample = pool.sample(20, random_state=rng.randint(0, 1_000_000))
            if medians_within(sample):
                final_list.extend(sample.word.tolist())
                chosen.update(sample.word)
                break
        else:
            st.error(f"Impossible de trouver 20 mots pour {gname} respectant les médianes."); st.stop()

    rng.shuffle(final_list)
    return final_list

STIMULI = pick_stimuli()

# ────────────────── 2. PARAMÈTRES TEMPORELS ──────────────────
# ───────────────── 3. PARAMÈTRES TEMPORELS ────────────────────────────────
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ────────────────── 3. INTERFACE STREAMLIT ──────────────────
# ───────────────── 4. INTERFACE STREAMLIT ────────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# -------------------------- INTRO ---------------------------
# ------------------------- PAGE INTRO -------------------------------------
if st.session_state.stage == "intro":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")
    st.write("80 mots tirés aléatoirement dans Lexique 3.83 (CSV UTF-8).")
    st.write("80 mots tirés aléatoirement (OLD20 / PLD20 ± contraintes médianes).")
    st.markdown("""
1. Fixez le centre de l’écran.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Tapez le mot puis validez avec **Entrée**.  
3. Tapez le mot et validez par **Entrée**.  
""")
    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ------------------------ EXPÉRIENCE ------------------------
# ------------------------- PAGE EXPÉRIENCE --------------------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)

@@ -124,91 +139,74 @@ def sample(sub, n):
<style>
 html,body {{
   height:100%; margin:0; display:flex; align-items:center; justify-content:center;
   background:#ffffff; font-family:'Courier New',monospace;
   background:#fff; font-family:'Courier New',monospace;
 }}
 #scr {{ font-size:60px; user-select:none; }}
 #ans {{ display:none; font-size:48px; width:60%; text-align:center; }}
</style>
</head>
 #scr {{font-size:60px; user-select:none;}}
 #ans {{display:none;font-size:48px;width:60%;text-align:center;}}
</style></head>
<body id="body" tabindex="0">
  <div id="scr"></div>
  <input id="ans" autocomplete="off" />
  <input id="ans" autocomplete="off"/>
<script>
/* focus immédiat dans l'iframe */
window.addEventListener('load', ()=>document.getElementById('body').focus());
window.addEventListener('load',()=>document.getElementById('body').focus());

const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

let idx = 0, results = [];
let idx = 0, res = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

function runTrial() {{
  if (idx >= WORDS.length) {{ end(); return; }}
  const word = WORDS[idx];
  const mask = '#'.repeat(word.length);

  let sd = START, md = CYCLE - sd, t0 = performance.now(), active = true;
  let to1 = null, to2 = null;
  if(idx >= WORDS.length) {{ end(); return; }}
  const w = WORDS[idx];
  const mask = '#'.repeat(w.length);
  let sd = START, md = CYCLE - sd, t0 = performance.now(), go=true, t1=null, t2=null;

  function loop() {{
    if (!active) return;
    scr.textContent = word;
    to1 = setTimeout(()=>{{
      if (!active) return;
    if(!go) return;
    scr.textContent = w;
    t1 = setTimeout(()=>{{ if(!go) return;
      scr.textContent = mask;
      to2 = setTimeout(()=>{{ if (active) {{ sd += STEP; md = Math.max(0,CYCLE-sd); loop(); }} }}, md);
      t2 = setTimeout(()=>{{ if(go) {{ sd += STEP; md = Math.max(0,CYCLE-sd); loop(); }} }}, md);
    }}, sd);
  }}
  loop();
  }} loop();

  function onSpace(e) {{
    if (e.code === 'Space' && active) {{
      active = false;
      clearTimeout(to1); clearTimeout(to2);
    if(e.code === 'Space' && go) {{
      go = false; clearTimeout(t1); clearTimeout(t2);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener('keydown', onSpace);

      scr.textContent = '';
      ans.style.display = 'block';
      ans.value = '';
      ans.focus();
      ans.style.display = 'block'; ans.value = ''; ans.focus();

      ans.addEventListener('keydown', function onEnter(ev) {{
        if (ev.key === 'Enter') {{
        if(ev.key === 'Enter') {{
          ev.preventDefault();
          results.push({{word:word, rt_ms:rt, response:ans.value.trim()}});
          res.push({{word:w, rt_ms:rt, response:ans.value.trim()}});
          ans.removeEventListener('keydown', onEnter);
          ans.style.display = 'none';
          idx += 1;
          runTrial();
          ans.style.display = 'none'; idx += 1; runTrial();
        }}
      }});
    }}
  }}
  window.addEventListener('keydown', onSpace);
  }} window.addEventListener('keydown', onSpace);
}}

function end() {{
  scr.style.fontSize = '40px';
  scr.textContent = 'Merci ! Fin de l’expérience.';

  const SEP=';';
  const csv = ['word','rt_ms','response'].join(SEP)+'\\n'+
              results.map(r=>[r.word,r.rt_ms,r.response].join(SEP)).join('\\n');
  const blob = new Blob([csv],{{type:'text/csv;charset=utf-8'}});
  const url  = URL.createObjectURL(blob);

  const csv = ['word','rt_ms','response'].join(SEP)+'\\n' +
              res.map(r=>[r.word,r.rt_ms,r.response].join(SEP)).join('\\n');
  const a = document.createElement('a');
  a.href = url; a.download = 'results.csv';
  a.textContent = 'Télécharger les résultats (.csv)';
  a.href = URL.createObjectURL(new Blob([csv],{{type:'text/csv;charset=utf-8'}}));
  a.download = 'results.csv'; a.textContent = 'Télécharger les résultats (.csv)';
  a.style.fontSize = '32px'; a.style.marginTop = '30px';
  document.body.appendChild(a);
}}

runTrial();
</script>
</body></html>
</script></body></html>
"""
    components.html(html, height=650, width=1100, scrolling=False)
