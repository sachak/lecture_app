# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
80 mots, fond noir plein-écran, stimuli blancs.

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template

import pandas as pd
import streamlit as st
from streamlit import components

# ─────────── PARAMÈTRES DU TIRAGE ───────────────────────────────────────────
MEAN_FACTOR_OLDPLD = 0.45
MEAN_DELTA         = {"letters": 0.68, "phons": 0.68}
SD_MULT            = {"letters": 2.0, "phons": 2.0,
                      "old20": 0.28, "pld20": 0.28, "freq": 1.9}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

# ─────────── OUTILS ─────────────────────────────────────────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(" ",  "", regex=False)
         .str.replace("\xa0","", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:     # -1 = LOW ; 1 = HIGH
    return -1 if "LOW" in tag else 1

# ─────────── CHARGEMENT EXCEL + TIRAGE DES 80 MOTS ─────────────────────────
@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls          = pd.ExcelFile(XLSX)
    sheet_names  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheet_names:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df          = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols)}
        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

def masks(df, st_):
    return {"LOW_OLD":  df.old20 < st_["m_old20"] - st_["sd_old20"],
            "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
            "LOW_PLD":  df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
            "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"]}

def sd_ok(sub, st_, fq_cols):
    return (sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
            sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
            sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
            sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
            all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq_cols))

def mean_lp_ok(sub, st_):
    return (abs(sub.nblettres.mean() - st_["m_nblettres"]) <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
            abs(sub.nbphons.mean()   - st_["m_nbphons"])   <= MEAN_DELTA["phons"]   * st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_  = F[feuille]["df"], F[feuille]["stats"]
    fqs      = F[feuille]["freq_cols"]
    pool     = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 1_000_000)).copy()
        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fqs): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F = load_sheets(); all_freq_cols = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken = {sh: set() for sh in F if sh != "all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            parts = []
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok = False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source", "group",
                                                            "old_cat", "pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste (contraintes trop strictes)."); st.stop()

# ─────────── Gabarit HTML / JS (plein écran noir) ──────────────────────────
HTML_TPL = Template(r"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{
  height:100%;width:100%;margin:0;padding:0;overflow:hidden;
  background:#000;color:#fff;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-family:'Courier New',monospace;
}
#scr{font-size:7vw;user-select:none;color:#fff;text-align:center;}
#ans{
  display:none;font-size:5vw;width:60%;text-align:center;
  background:#000;color:#fff;border:none;border-bottom:3px solid #fff;
  outline:none;caret-color:#fff;
}
#intro{
  position:fixed;inset:0;background:#000;color:#fff;z-index:10;
  display:flex;align-items:center;justify-content:center;
  font-size:5vw;text-align:center;
}
</style>
</head>

<body tabindex="0">
<div id="intro">Appuyez sur la barre Espace pour commencer</div>
<div id="scr"></div>
<input id="ans" autocomplete="off"/>

<script>
const WORDS = $WORDS;
const CYCLE = $CYCLE;
const START = $START;
const STEP  = $STEP;

let trial = 0;
const results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");
const intro = document.getElementById("intro");

/* ——— démarrage + plein-écran ——— */
function launch(){
  intro.style.display="none";
  if(document.documentElement.requestFullscreen){
      document.documentElement.requestFullscreen().catch(()=>{});
  }
  nextTrial();
}
window.addEventListener("keydown", function start(e){
  if(e.code==="Space"){
    e.preventDefault();
    window.removeEventListener("keydown", start);
    launch();
  }
});

/* ——— boucle expérimentale ——— */
function nextTrial(){
  if(trial >= WORDS.length){ endExperiment(); return; }

  const w    = WORDS[trial];
  const mask = "#".repeat(w.length);
  let showDur = START, hideDur = CYCLE - showDur;
  let tShow, tHide, active = true, t0 = performance.now();

  (function loop(){
    if(!active) return;
    scr.textContent = w;
    tShow = setTimeout(()=>{
      if(!active) return;
      scr.textContent = mask;
      tHide = setTimeout(()=>{
        if(active){
          showDur += STEP;
          hideDur  = Math.max(0, CYCLE - showDur);
          loop();
        }
      }, hideDur);
    }, showDur);
  })();

  function onSpace(e){
    if(e.code === "Space" && active){
      active = false;
      clearTimeout(tShow); clearTimeout(tHide);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener("keydown", onSpace);

      scr.textContent = "";
      ans.style.display = "block"; ans.value = ""; ans.focus();

      ans.addEventListener("keydown", function onEnter(ev){
        if(ev.key === "Enter"){
          ev.preventDefault();
          results.push({word:w, rt_ms:rt, response:ans.value.trim()});
          ans.removeEventListener("keydown", onEnter);
          ans.style.display = "none";
          trial += 1; nextTrial();
        }
      });
    }
  }
  window.addEventListener("keydown", onSpace);
}

/* ——— fin de l’expérience ——— */
function endExperiment(){
  scr.style.fontSize="5vw";
  scr.textContent = "Merci !";
  const csv = ["word;rt_ms;response",
               ...results.map(r=>`$$${r.word};$$${r.rt_ms};$$${r.response}`)].join("\\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  a.download = "results.csv";
  a.textContent = "Télécharger les résultats";
  a.style.fontSize="32px";
  a.style.marginTop="30px";
  document.body.appendChild(a);
}
</script>
</body>
</html>
""")

def experiment_html(words, cycle_ms=350, start_ms=14, step_ms=14):
    """Construit la page HTML/JS pour la phase de test."""
    return HTML_TPL.substitute(
        WORDS=json.dumps(words),
        CYCLE=cycle_ms,
        START=start_ms,
        STEP=step_ms
    )

# ─────────── Interface Streamlit minimale ──────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide",
                   initial_sidebar_state="collapsed")

# on masque tout le chrome Streamlit pour ne conserver que notre composant
st.markdown(
    """
    <style>
        body, .stApp {background:#000 !important; color:#fff !important;}
        #MainMenu, header, footer {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Chargement des stimuli…")

with st.spinner("Tirage aléatoire des 80 mots…"):
    tirage_df = build_sheet()
    words = tirage_df["ortho"].tolist()
    random.shuffle(words)

components.v1.html(
    experiment_html(words),
    height=800,   # hauteur arbitraire : le composant passe ensuite en plein écran
    scrolling=False
)
