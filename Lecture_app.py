# -*- coding: utf-8 -*-
"""
EXPERIENCE 3 – tirage des 80 mots en arrière-plan (thread + add_script_run_ctx)
Compatible Streamlit >= 1.32 (st.rerun)
"""
from __future__ import annotations
import json, random, threading, time
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components
from streamlit.runtime.scriptrunner import add_script_run_ctx


# ────────────────────── utilitaire rerun (toutes versions) ───────────────── #
_rerun = st.rerun if hasattr(st, "rerun") else st.experimental_rerun


# ───────────────────────────── PARAMÈTRES ──────────────────────────────── #
XLSX            = Path(__file__).with_name("Lexique.xlsx")
PRACTICE_WORDS  = ["PAIN", "EAU"]

MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER      = {"letters": 2.0, "phons": 2.0, "old20": 0.25,
                      "pld20": 0.25, "freq":   1.8}

N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000

rng             = random.Random()
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]


# ──────────────────────── CONFIG STREAMLIT ─────────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
      #MainMenu, header, footer {visibility: hidden;}
      .css-1d391kg{display:none;}          /* ancien spinner Streamlit */
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────  OUTILS  ────────────────────────────────── #
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

def cat_code(tag: str) -> int:      # −1 (LOW) / +1 (HIGH)
    return -1 if "LOW" in tag else 1


# ─────────────────── CHARGEMENT DU CLASSEUR (cache) ────────────────────── #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheets:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()

        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20","pld20","nblettres","nbphons") + tuple(freq_cols)}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles


# ───────────────────────── TIRAGE DES 80 MOTS ──────────────────────────── #
def masks(df: pd.DataFrame, st_: dict) -> dict[str, pd.Series]:
    return {"LOW_OLD":  df.old20 < st_["m_old20"] - st_["sd_old20"],
            "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
            "LOW_PLD":  df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
            "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"]}

def sd_ok(sub: pd.DataFrame, st_: dict, fqs: list[str]) -> bool:
    return (sub.nblettres.std(ddof=0) <= st_["sd_nblettres"]*SD_MULTIPLIER["letters"] and
            sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
            sub.old20.std(ddof=0)     <= st_["sd_old20"]    *SD_MULTIPLIER["old20"]   and
            sub.pld20.std(ddof=0)     <= st_["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
            all(sub[c].std(ddof=0) <= st_[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fqs))

def mean_lp_ok(sub: pd.DataFrame, st_: dict) -> bool:
    return (abs(sub.nblettres.mean()-st_["m_nblettres"])<=MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()-st_["m_nbphons"])    <=MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag:str, feuille:str, used:set[str], F) -> pd.DataFrame|None:
    df, st_, fqs = F[feuille]["df"], F[feuille]["stats"], F[feuille]["freq_cols"]
    pool = df.loc[masks(df,st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD" and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="HIGH_OLD"and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="LOW_PLD" and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if tag=="HIGH_PLD"and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if not mean_lp_ok(samp, st_): continue
        if sd_ok(samp, st_, fqs):
            samp["source"]=feuille; samp["group"]=tag
            samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
            return samp
    return None

def build_sheet() -> pd.DataFrame:
    F = load_sheets(); freqs = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            parts=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            order=["ortho"]+NUM_BASE+freqs+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Impossible de générer la liste (contraintes trop strictes).")


# ──────────────── TIRAGE EN ARRIÈRE-PLAN (THREAD) ──────────────────────── #
def launch_thread():
    def worker():
        try:
            df = build_sheet()
        except Exception as exc:
            st.session_state.tirage_error = str(exc)
        else:
            st.session_state.tirage_df = df
            lst = df.ortho.tolist(); random.shuffle(lst)
            st.session_state.stimuli = lst
        st.session_state.tirage_done = True
        _rerun()

    th = threading.Thread(target=worker, daemon=True)
    add_script_run_ctx(th)     # indispensable
    th.start()
    st.session_state.tirage_thread = th

if "tirage_done" not in st.session_state:
    st.session_state.tirage_done  = False
    st.session_state.tirage_error = ""
    launch_thread()


# ─────────────────────── TEMPLATE HTML / JS ───────────────────────────── #
_HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8" />
<style>
html,body{
  height:100%;margin:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
const WORDS = __WORDS__;
const CYCLE = __CYCLE__;
const START = __START__;
const STEP  = __STEP__;
const WITH_DOWNLOAD = __DL__;

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

function nextTrial(){
  if(trial >= WORDS.length){
    endExperiment(); return;
  }
  const w = WORDS[trial];
  const mask = "#".repeat(w.length);

  let showDur = START,
      hideDur = CYCLE - showDur,
      tShow, tHide;
  const t0 = performance.now();
  let active = true;

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
      ans.style.display="block"; ans.value=""; ans.focus();

      function onEnter(ev){
        if(ev.key === "Enter"){
          ev.preventDefault();
          results.push({word:w, rt_ms:rt, response:ans.value.trim()});
          ans.removeEventListener("keydown", onEnter);
          ans.style.display="none";
          trial += 1; nextTrial();
        }
      }
      ans.addEventListener("keydown", onEnter);
    }
  }
  window.addEventListener("keydown", onSpace);
}

function endExperiment(){
  scr.style.fontSize="40px";
  scr.textContent = WITH_DOWNLOAD ? "Merci !" : "Fin de l’entraînement";
  if(!WITH_DOWNLOAD) return;

  const csv = ["word;rt_ms;response",
               ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type:"text/csv"}));
  a.download = "results.csv";
  a.textContent = "Télécharger les résultats";
  a.style.fontSize = "32px"; a.style.marginTop = "30px";
  document.body.appendChild(a);
}

nextTrial();
</script>
</body>
</html>
"""

def make_html(words:list[str], *, with_download=True,
              cycle_ms=350, start_ms=14, step_ms=14) -> str:
    html = (_HTML_TEMPLATE
            .replace("__WORDS__", json.dumps(words))
            .replace("__CYCLE__", str(cycle_ms))
            .replace("__START__", str(start_ms))
            .replace("__STEP__",  str(step_ms))
            .replace("__DL__", "true" if with_download else "false"))
    return html


# ─────────────────────────── NAVIGATION UI ────────────────────────────── #
if "page" not in st.session_state:
    st.session_state.page = "intro"


# ─ intro ─
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** puis le test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"; _rerun()

# ─ familiarisation ─
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **Espace** dès que vous voyez apparaître le mot, "
                "puis tapez ce que vous avez lu et validez avec **Entrée**.")

    info = st.empty()
    if st.session_state.tirage_done:
        if st.session_state.tirage_error:
            info.error(f"Erreur lors du tirage : {st.session_state.tirage_error}")
        else:
            info.success("Stimuli du test prêts !")
    else:
        info.info("Préparation des stimuli du test en arrière-plan…")

    components.v1.html(make_html(PRACTICE_WORDS, with_download=False),
                       height=650, scrolling=False)

    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"; _rerun()

# ─ test principal ─
else:   # page == "exp"
    st.header("Test principal (80 mots)")

    if not st.session_state.tirage_done:
        st.warning("Les stimuli sont encore en cours de génération… Merci de patienter.")
        time.sleep(1); _rerun()

    if st.session_state.tirage_error:
        st.error(f"Impossible de poursuivre : {st.session_state.tirage_error}")
        st.stop()

    tirage_df = st.session_state.tirage_df
    STIMULI   = st.session_state.stimuli

    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())

    components.v1.html(make_html(STIMULI, with_download=True),
                       height=650, scrolling=False)
