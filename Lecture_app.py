# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – mots masqués, tirage de 4 × 20 mots en tâche de fond.

1. La page d’accueil apparaît immédiatement.
2. Le tirage (« build_sheet ») tourne dans un thread.
3. Quand le calcul se termine, le script principal recharge l’interface.
"""

from __future__ import annotations
import json, random, threading, queue
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ──────────────────────────── FONCTION UTILITAIRE rerun ───────────────────── #
def _do_rerun():
    """Appelle st.rerun() ou st.experimental_rerun() selon la version."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ───────────────────────────── PARAMÈTRES GÉNÉRAUX ────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>#MainMenu, header, footer {visibility: hidden;}</style>
    """,
    unsafe_allow_html=True,
)

# (paramètres de build_sheet – identiques au script précédent)
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA = {"letters": 0.70, "phons": 0.70}
SD_MULTIPLIER = {"letters": 2.0, "phons": 2.0, "old20": 0.25, "pld20": 0.25, "freq": 10.0}

XLSX = Path(__file__).with_name("Lexique.xlsx")
TAGS = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG, MAX_TRY_TAG, MAX_TRY_FULL = 5, 1_000, 1_000
NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]
rng = random.Random()

# ──────────────────────────── OUTILS GENERIQUES ───────────────────────────── #
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag): return -1 if "LOW" in tag else 1

# ────────────────────────── CHARGEMENT DES FEUILLES ───────────────────────── #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"❌ Fichier « {XLSX.name} » introuvable.")
        st.stop()

    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("❌ 4 feuilles Feuil1 … Feuil4 sont requises.")
        st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheet_names:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()
        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}")
            st.stop()

        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0)
                  for c in ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols)}
        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

# ───────────────────────────── BUILD_SHEET ────────────────────────────────── #
def masks(df: pd.DataFrame, st_) -> dict[str, pd.Series]:
    return {
        "LOW_OLD": df.old20 < st_["m_old20"] - st_["sd_old20"],
        "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
        "LOW_PLD": df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
        "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"],
    }

def sd_ok(sub, st_, fqs):
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULTIPLIER["letters"]
        and sub.nbphons.std(ddof=0) <= st_["sd_nbphons"] * SD_MULTIPLIER["phons"]
        and sub.old20.std(ddof=0) <= st_["sd_old20"] * SD_MULTIPLIER["old20"]
        and sub.pld20.std(ddof=0) <= st_["sd_pld20"] * SD_MULTIPLIER["pld20"]
        and all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULTIPLIER["freq"] for c in fqs)
    )

def mean_lp_ok(sub, st_):
    return (
        abs(sub.nblettres.mean() - st_["m_nblettres"]) <= MEAN_DELTA["letters"] * st_["sd_nblettres"]
        and abs(sub.nbphons.mean() - st_["m_nbphons"]) <= MEAN_DELTA["phons"] * st_["sd_nbphons"]
    )

def pick_five(tag, feuille, used, FEUILLES):
    df, st_, fqs = FEUILLES[feuille]["df"], FEUILLES[feuille]["stats"], FEUILLES[feuille]["freq_cols"]
    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 1_000_000)).copy()
        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fqs):
            continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    FEUILLES = load_sheets()
    all_freq_cols = FEUILLES["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken = {sh: set() for sh in FEUILLES if sh != "all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            parts = []
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], FEUILLES)
                if sub is None:
                    ok = False
                    break
                parts.append(sub)
                taken[sh].update(sub.ortho)
            if not ok:
                break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source", "group", "old_cat", "pld_cat"]
            return df[order]
    raise RuntimeError("Impossible de générer la liste – relâchez les contraintes.")

# ───────────────────────── THREAD DE CALCUL + QUEUE ───────────────────────── #
def _worker(out_q: "queue.Queue"):
    """Calcule la liste et la place dans la queue (aucun appel Streamlit)."""
    try:
        df = build_sheet()
        out_q.put(("ok", df))
    except Exception as exc:
        out_q.put(("err", str(exc)))

# ───────────────────────────── ETAT SESSION ───────────────────────────────── #
for k, v in (
    ("builder_started", False),
    ("stimuli_ok", False),
    ("err_msg", ""),
    ("tirage_df", None),
    ("result_q", queue.Queue()),
):
    st.session_state.setdefault(k, v)

def launch_background_build():
    if not st.session_state.builder_started:
        st.session_state.builder_started = True
        threading.Thread(target=_worker, args=(st.session_state.result_q,), daemon=True).start()

def check_queue():
    """Récupère le résultat du thread, puis relance l’interface si besoin."""
    q = st.session_state.result_q
    changed = False
    while not q.empty():
        status, payload = q.get_nowait()
        if status == "ok":
            st.session_state.tirage_df = payload
            st.session_state.STIMULI = payload["ortho"].tolist()
            st.session_state.stimuli_ok = True
        else:
            st.session_state.err_msg = payload
            st.session_state.stimuli_ok = False
        changed = True
    if changed:
        _do_rerun()  # relance dans le thread principal

check_queue()             # appelé à chaque exécution
if "page" not in st.session_state:
    st.session_state.page = "intro"

# ───────────────────────────── INTERFACE UI ──────────────────────────────── #
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ------------------------------ PAGE INTRO --------------------------------- #
if st.session_state.page == "intro":
    launch_background_build()

    st.title("EXPERIENCE 3 – mots masqués (tirage contraint)")
    if st.session_state.err_msg:
        st.error(st.session_state.err_msg)
        st.stop()

    if st.session_state.stimuli_ok:
        st.success("✓ Liste de mots prête.")
        with st.expander("Aperçu du tirage"):
            st.dataframe(st.session_state.tirage_df)
        if st.button("Démarrer l’expérience"):
            st.session_state.page = "exp"
            _do_rerun()
    else:
        st.info("Recherche des mots en arrière-plan…")
        st.progress(0)
        st.button("Démarrer l’expérience", disabled=True)

# ------------------------------ PAGE EXP ----------------------------------- #
else:  # page 'exp'
    if not st.session_state.stimuli_ok:
        st.stop()
    STIMULI = st.session_state.STIMULI

    html = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace;}}
#scr{{font-size:60px;user-select:none;}}
#ans{{display:none;font-size:48px;width:60%;text-align:center;}}
</style></head><body tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const WORDS={json.dumps(STIMULI)},CYCLE={CYCLE_MS},START={START_MS},STEP={STEP_MS};
let trial=0,results=[];const scr=document.getElementById("scr"),ans=document.getElementById("ans");
function nextTrial(){{
 if(trial>=WORDS.length){{endExperiment();return;}}
 const w=WORDS[trial],mask="#".repeat(w.length);
 let show=START,hide=CYCLE-show,t0=performance.now(),active=true,tS,tH;
 (function loop(){{if(!active)return;
      scr.textContent=w;
      tS=setTimeout(()=>{{if(!active)return;
          scr.textContent=mask;
          tH=setTimeout(()=>{{if(active){{show+=STEP;hide=Math.max(0,CYCLE-show);loop();}}}},hide);
      }},show);}})();
 function onSpace(e){{if(e.code==="Space"&&active){{active=false;clearTimeout(tS);clearTimeout(tH);
      const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",onSpace);
      scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
      ans.addEventListener("keydown",function onEnter(ev){{if(ev.key==="Enter"){{ev.preventDefault();
           results.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
           ans.removeEventListener("keydown",onEnter);ans.style.display="none";trial++;nextTrial();}}}});}}}}
 window.addEventListener("keydown",onSpace);}
function endExperiment(){{
  scr.style.fontSize="40px";scr.textContent="Merci !";
  const csv=["word;rt_ms;response",...results.map(r=>`${{r.word}};${{r.rt_ms}};${{r.response}}`)].join("\\n");
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{{type:"text/csv"}}));
  a.download="results.csv";a.textContent="Télécharger les résultats";
  a.style.fontSize="32px";a.style.marginTop="30px";document.body.appendChild(a);}}
nextTrial();
</script></body></html>"""
    components.v1.html(html, height=650, scrolling=False)
