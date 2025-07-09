# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Tâche de reconnaissance de mots masqués
(familiarisation 2 mots + test principal 80 mots)

Exécution :   streamlit run exp3.py
Dépendance :  Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations

import json, random
from pathlib import Path
from string import Template

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ────────────────────────── OUTIL RERUN STREAMLIT ──────────────────────────
def do_rerun() -> None:
    """Forcer un rerun quelle que soit la version de Streamlit."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ────────────────────────── CONFIGURATION GLOBALE ──────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .css-1d391kg {display: none;}  /* ancien spinner */
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# 1. PARAMÈTRES DU TIRAGE
# =============================================================================
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
PRACTICE_WORDS  = ["PAIN", "EAU"]

MANDATORY_COLS  = ["ortho", "old20", "pld20"]           # indispensables
OPTIONAL_COLS   = ["letters", "phons", "freqfilms2", "freqwikis2"]

# =============================================================================
# 2. OUTILS DIVERS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    """Convertit une série en float, en gérant les virgules éventuelles."""
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame mélangé (index remis)."""
    return df.sample(frac=1, random_state=random.randint(0, 2**32 - 1)).reset_index(drop=True)

# =============================================================================
# 3. CHARGEMENT EXCEL + TIRAGE DES 80 MOTS
# =============================================================================
@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, pd.DataFrame]:
    """Charge les 4 feuilles ‘Feuil*’ en étant tolérant sur les colonnes."""
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls          = pd.ExcelFile(XLSX)
    sheet_names  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Le classeur doit contenir exactement 4 feuilles Feuil1…Feuil4.")
        st.stop()

    sheets = {}
    for name in sheet_names:
        df = pd.read_excel(xls, sheet_name=name)
        df.columns = df.columns.str.lower()

        # Vérification des colonnes indispensables
        missing = [c for c in MANDATORY_COLS if c not in df.columns]
        if missing:
            st.error(
                f"Feuille « {name} » : colonne(s) manquante(s) {missing}. "
                "Merci de compléter votre fichier Excel."
            )
            st.stop()

        # Conversion numérique
        for col in MANDATORY_COLS + OPTIONAL_COLS:
            if col in df.columns:
                df[col] = to_float(df[col])

        # Création des catégories LOW / HIGH sur la médiane
        df["old_cat"] = np.where(df["old20"] <= df["old20"].median(), "LOW_OLD", "HIGH_OLD")
        df["pld_cat"] = np.where(df["pld20"] <= df["pld20"].median(), "LOW_PLD", "HIGH_PLD")
        df["group"]   = name
        df["source"]  = name

        keep = (
            MANDATORY_COLS +
            [c for c in OPTIONAL_COLS if c in df.columns] +
            ["source", "group", "old_cat", "pld_cat"]
        )
        sheets[name] = df[keep].dropna(subset=["ortho"])

    return sheets

@st.cache_data(show_spinner=False)
def build_sheet() -> pd.DataFrame:
    """Construit la liste finale de 80 mots (5 mots × 4 feuilles × 4 catégories)."""
    sheets = load_sheets()
    for _ in range(1_000):                          # 1000 tentatives max
        parts = []
        ok = True
        for tag in TAGS:
            for name, df in sheets.items():
                subset = df[df["old_cat" if "OLD" in tag else "pld_cat"] == tag]
                if len(subset) < N_PER_FEUIL_TAG:
                    ok = False; break
                parts.append(subset.sample(N_PER_FEUIL_TAG))
            if not ok:
                break
        if ok:
            return shuffled(pd.concat(parts, ignore_index=True))

    st.error("Impossible de générer la liste (contraintes trop strictes)."); st.stop()

# =============================================================================
# 4. TEMPLATE HTML / JS (calibré 60 Hz)
# =============================================================================
HTML_TPL = Template(r"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<style>
html,body{margin:0;height:100%;display:flex;align-items:center;justify-content:center}
body{background:#000;color:#FFF;font-family:Arial,Helvetica,sans-serif;font-size:48px}
#ans{display:none;font-size:32px;margin-top:20px;width:300px;text-align:center}
</style>
</head>
<body>
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
/* ============= paramètres injectés par Streamlit ============= */
const WORDS     = $WORDS;
const CYCLE_MS  = $CYCLE_MS;
const START_MS  = $START_MS;
const STEP_MS   = $STEP_MS;
const CROSS_MS  = $CROSS_MS;
/* =============================================================== */

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

/* ---------- 1. Mesure de la fréquence écran (~60 Hz) ---------- */
function estimateFPS(samples=120){
  return new Promise(ok=>{
    let t=[];
    function step(ts){
      t.push(ts);
      if(t.length<samples) requestAnimationFrame(step);
      else{
        const d=t.slice(1).map((v,i)=>v-t[i]);
        const avg=d.reduce((a,b)=>a+b,0)/d.length;
        ok(1000/avg);
      }
    }
    requestAnimationFrame(step);
  });
}

/* ------------------ 2. Lancement général ---------------------- */
function init(){
  estimateFPS().then(fps=>{
    if(fps>55 && fps<65){ startExperiment(); }
    else{
      document.body.innerHTML =
      `<div style="text-align:center;font-size:32px;max-width:80%">
         <p><strong>Fréquence détectée : ${fps.toFixed(1)} Hz</strong></p>
         <p>Cette expérience nécessite un écran réglé à 60 Hz.</p>
         <p>Veuillez ajuster la fréquence puis relancez la page.</p>
       </div>`;
    }
  });
}

/* ------------------------ 3. Expérience ----------------------- */
function nextTrial(){
  if(trial>=WORDS.length){ return endExperiment(); }

  /* Croix de fixation */
  scr.textContent="+";
  setTimeout(()=>runWordTrial(WORDS[trial]), CROSS_MS);
}

function runWordTrial(word){
  const mask="#".repeat(word.length);
  let showDur=START_MS;
  let hideDur=CYCLE_MS-showDur;
  let active=true;
  const t0=performance.now();

  function loop(){
    if(!active) return;
    scr.textContent=word;
    setTimeout(()=>{
      scr.textContent=mask;
      setTimeout(()=>{
        showDur += STEP_MS;
        hideDur = Math.max(0, CYCLE_MS - showDur);
        loop();
      }, hideDur);
    }, showDur);
  }
  loop();

  function onSpace(e){
    if(e.code==="Space" && active){
      active=false;
      window.removeEventListener("keydown",onSpace);
      const rt=Math.round(performance.now()-t0);
      scr.textContent="";
      ans.style.display="block"; ans.value=""; ans.focus();

      ans.addEventListener("keydown",function onEnter(ev){
        if(ev.key==="Enter"){
          ev.preventDefault();
          results.push({word,rt_ms:rt,response:ans.value.trim()});
          ans.removeEventListener("keydown",onEnter);
          ans.style.display="none";
          trial++; nextTrial();
        }
      });
    }
  }
  window.addEventListener("keydown",onSpace);
}

/* ---------------------- 4. Fin d’expérience ------------------- */
function endExperiment(){
  scr.style.fontSize="40px";
  scr.textContent="Merci !";

  const csv=["word;rt_ms;response",
             ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  a.download="results.csv";
  a.textContent="Télécharger les résultats";
  a.style.fontSize="32px";
  a.style.marginTop="30px";
  document.body.appendChild(a);
}

function startExperiment(){ nextTrial(); }
init();
</script>
</body>
</html>
""")

def experiment_html(words: list[str],
                    cross_ms: int = 500,
                    cycle_ms: int = 333,
                    start_ms: int = 17,
                    step_ms: int = 17) -> str:
    """Fabrique la page HTML/JS de l’expérience."""
    return HTML_TPL.substitute(
        WORDS=json.dumps(words),
        CYCLE_MS=cycle_ms,
        START_MS=start_ms,
        STEP_MS=step_ms,
        CROSS_MS=cross_ms
    )

# =============================================================================
# 5. NAVIGATION STREAMLIT
# =============================================================================
if "page" not in st.session_state:        st.session_state.page = "intro"
if "tirage_en_cours" not in st.session_state: st.session_state.tirage_en_cours = False
if "tirage_ok"      not in st.session_state: st.session_state.tirage_ok      = False

# ───────────────────────── PAGE INTRO ──────────────────────────────────────
if st.session_state.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")

    st.markdown(
        """
**Important**  
Cette expérience est **strictement calibrée pour un moniteur 60 Hz**.  
Un test automatique vérifiera la fréquence avant de commencer.

**Principe**  
Des mots apparaîtront très brièvement (≈ 17 ms, soit 1 trame) puis seront
masqués par une suite de dièses.

**Votre tâche**  
• Fixez la croix **+** au centre.  
• Dès que vous reconnaissez le mot, appuyez sur **Espace**.  
• Tapez ensuite le mot et validez avec **Entrée**.

**Déroulement**  
1. Familiarisation (2 mots)  
2. Test principal (80 mots)
        """
    )

    # Tirage automatique la première fois
    if not st.session_state.tirage_en_cours and not st.session_state.tirage_ok:
        st.session_state.tirage_en_cours = True
        do_rerun()

    # Tirage (spinner)
    if st.session_state.tirage_en_cours and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            tirage_df = build_sheet()
            mots = tirage_df["ortho"].str.upper().tolist()
            random.shuffle(mots)
            st.session_state.tirage_df       = tirage_df
            st.session_state.stimuli         = mots
            st.session_state.tirage_en_cours = False
            st.session_state.tirage_ok       = True
        st.success("Tirage terminé !")

    if st.session_state.tirage_ok and st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        do_rerun()

# ──────────────────────── PAGE FAMILIARISATION ────────────────────────────
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Fixez la croix, appuyez sur **Espace** quand le mot apparaît, "
                "puis tapez le mot lu et validez avec **Entrée**.")

    components.v1.html(
        experiment_html(PRACTICE_WORDS),
        height=650, scrolling=False
    )
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"
        do_rerun()

# ────────────────────────── PAGE TEST PRINCIPAL ───────────────────────────
elif st.session_state.page == "exp":
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu des 5 premières lignes du tirage"):
        st.dataframe(st.session_state.tirage_df.head())

    components.v1.html(
        experiment_html(st.session_state.stimuli),
        height=650, scrolling=False
    )
