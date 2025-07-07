# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – tirage des 80 mots dans un processus séparé
Compatible Streamlit ≥ 1.32 (st.rerun)
"""

from __future__ import annotations
import json, random, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import pandas as pd
import streamlit as st
from streamlit import components

# ---------------- utilitaire rerun (toutes versions) ---------------- #
_rerun = st.rerun if hasattr(st, "rerun") else st.experimental_rerun

# ---------------- paramètres généraux ---------------- #
XLSX = Path(__file__).with_name("Lexique.xlsx")
PRACTICE_WORDS = ["PAIN", "EAU"]
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA   = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER = {"letters": 2.0, "phons": 2.0, "old20": 0.25,
                 "pld20": 0.25, "freq": 1.8}
N_PER_FEUIL_TAG = 5
TAGS = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG  = 1_000
MAX_TRY_FULL = 1_000
rng = random.Random()
NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]

# ---------------- petite mise en page Streamlit ---------------- #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
 #MainMenu, header, footer {visibility: hidden;}
 .css-1d391kg{display:none;}
</style>""", unsafe_allow_html=True)

# ---------------- outils généraux ---------------- #
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

def cat_code(tag: str) -> int:
    return -1 if "LOW" in tag else 1

# ---------------- lecture du classeur (cache) ---------------- #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"{XLSX.name} introuvable."); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)

        need = ["ortho","old20","pld20","nblettres","nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for col in NUM_BASE + freq_cols: df[col] = to_float(df[col])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20","pld20","nblettres","nbphons") + tuple(freq_cols)}
        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

# ---------------- fonctions de tirage ---------------- #
def masks(df: pd.DataFrame, st_: dict) -> dict[str, pd.Series]:
    return {"LOW_OLD": df.old20 < st_["m_old20"] - st_["sd_old20"],
            "HIGH_OLD":df.old20 > st_["m_old20"] + st_["sd_old20"],
            "LOW_PLD": df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
            "HIGH_PLD":df.pld20 > st_["m_pld20"] + st_["sd_pld20"]}

def sd_ok(sub: pd.DataFrame, st_: dict, fqs:list[str]) -> bool:
    return (sub.nblettres.std(ddof=0)<=st_["sd_nblettres"]*SD_MULTIPLIER["letters"] and
            sub.nbphons .std(ddof=0)<=st_["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
            sub.old20   .std(ddof=0)<=st_["sd_old20"]    *SD_MULTIPLIER["old20"]   and
            sub.pld20   .std(ddof=0)<=st_["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
            all(sub[c].std(ddof=0)<=st_[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fqs))

def mean_lp_ok(sub: pd.DataFrame, st_: dict) -> bool:
    return (abs(sub.nblettres.mean()-st_["m_nblettres"])<=MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()  -st_["m_nbphons"])   <=MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag:str, feuille:str, used:set[str], F) -> pd.DataFrame|None:
    df, st_, fqs = F[feuille]["df"], F[feuille]["stats"], F[feuille]["freq_cols"]
    pool = df.loc[masks(df,st_)[tag] & ~df.ortho.isin(used)]
    if len(pool)<N_PER_FEUIL_TAG: return None
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
        taken={sh:set() for sh in F if sh!="all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            parts=[]
            for sh in taken:
                sub=pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            order=["ortho"]+NUM_BASE+freqs+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Impossible de générer la liste (contraintes trop strictes).")

# ---------------- HTML/JS (chaîne brute) ---------------- #
_HTML=r"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const WORDS=__WORDS__,C=__CYCLE__,S=__START__,STEP=__STEP__,DL=__DL__;
let i=0,r=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function n(){if(i>=WORDS.length){e();return;}const w=WORDS[i],m="#".repeat(w.length);
let sh=S,hd=C-sh,a,t0=performance.now(),ok=true;(function l(){if(!ok)return;scr.textContent=w;
a=setTimeout(()=>{if(!ok)return;scr.textContent=m;setTimeout(()=>{if(ok){sh+=STEP;
hd=Math.max(0,C-sh);l();}},hd);},sh);})();
function sp(e){if(e.code==="Space"&&ok){ok=false;clearTimeout(a);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",sp);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function en(ev){if(ev.key==="Enter"){ev.preventDefault();
r.push({word:w,rt_ms:rt,response:ans.value.trim()});ans.removeEventListener("keydown",en);
ans.style.display="none";i++;n();}}ans.addEventListener("keydown",en);}}
window.addEventListener("keydown",sp);}function e(){scr.style.fontSize="40px";
scr.textContent=DL?"Merci !":"Fin de l’entraînement";if(!DL)return;
const csv=["word;rt_ms;response",...r.map(o=>`${o.word};${o.rt_ms};${o.response}`)].join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";document.body.appendChild(a);}n();
</script></body></html>"""
def html(words:list[str], dl=True, cycle=350, start=14, step=14):
    return (_HTML.replace("__WORDS__",json.dumps(words))
                 .replace("__CYCLE__",str(cycle))
                 .replace("__START__",str(start))
                 .replace("__STEP__", str(step))
                 .replace("__DL__",   "true" if dl else "false"))

# ---------------- lancement du calcul dans un PROCESSUS ---------------- #
if "future" not in st.session_state:
    exec_ = ProcessPoolExecutor(max_workers=1)
    st.session_state.future = exec_.submit(build_sheet)
    st.session_state.executor = exec_
    st.session_state.ready   = False
    st.session_state.error   = ""

# à chaque exécution on vérifie si le calcul est terminé
if not st.session_state.ready and st.session_state.future.done():
    try:
        df = st.session_state.future.result()
    except Exception as exc:
        st.session_state.error = str(exc)
    else:
        st.session_state.tirage_df = df
        lst = df.ortho.tolist(); random.shuffle(lst)
        st.session_state.stimuli = lst
        st.session_state.ready = True
    _rerun()

# ---------------- navigation Streamlit ---------------- #
if "page" not in st.session_state: st.session_state.page="intro"

# intro
if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** puis le test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page="fam"; _rerun()

# familiarisation
elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    if st.session_state.ready:
        st.success("Stimuli du test prêts !")
    else:
        st.info("Préparation des stimuli du test… (vous pouvez quand même vous entraîner)")
    components.v1.html(html(PRACTICE_WORDS, dl=False), height=650, scrolling=False)
    st.divider()
    if st.button("Passer au test principal"):
        if st.session_state.ready and not st.session_state.error:
            st.session_state.page="exp"; _rerun()
        else:
            st.warning("Les stimuli ne sont pas encore prêts, merci de patienter.")

# test principal
else:  # exp
    if st.session_state.error:
        st.error(f"Erreur : {st.session_state.error}"); st.stop()
    if not st.session_state.ready:
        st.warning("Les stimuli ne sont pas encore prêts…"); st.stop()

    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage"):
        st.dataframe(st.session_state.tirage_df.head())
    components.v1.html(html(st.session_state.stimuli, dl=True), height=650, scrolling=False)
