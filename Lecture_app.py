# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – tirage des 80 mots en arrière-plan
Exécution :  streamlit run exp3_async.py
"""
from __future__ import annotations

# ───────────────────────────── IMPORTS ──────────────────────────────── #
import json, random, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from streamlit import components


# ───────────────────── 0. CONFIGURATION STREAMLIT ───────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
 #MainMenu, header, footer {visibility: hidden;}
 .css-1d391kg{display:none;}
</style>""", unsafe_allow_html=True)


# ───────────────────── 1. CONSTANTES / PARAMÈTRES ───────────────────── #
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA   = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER = {"letters": 2.0, "phons": 2.0,
                 "old20": 0.25, "pld20": 0.25, "freq": 1.8}

XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000

rng             = random.Random()
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]          # phase de familiarisation


# ───────────────────── 2. OUTILS GÉNÉRIQUES ─────────────────────────── #
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


# ───────────────────── 3. CHARGEMENT D’EXCEL ─────────────────────────── #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheet_names:
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

        stats = {f"m_{c}": df[c].mean() for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20", "pld20", "nblettres", "nbphons") + tuple(freq_cols)}

        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles


# ───────────────────── 4. TIRAGE DES 80 MOTS ─────────────────────────── #
def masks(df: pd.DataFrame, st_: dict) -> dict[str, pd.Series]:
    return {"LOW_OLD": df.old20 < st_["m_old20"] - st_["sd_old20"],
            "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
            "LOW_PLD": df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
            "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"]}


def sd_ok(sub: pd.DataFrame, st_: dict, fqs: list[str]) -> bool:
    return (sub.nblettres.std(ddof=0) <= st_["sd_nblettres"]*SD_MULTIPLIER["letters"] and
            sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
            sub.old20.std(ddof=0)     <= st_["sd_old20"]    *SD_MULTIPLIER["old20"]   and
            sub.pld20.std(ddof=0)     <= st_["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
            all(sub[c].std(ddof=0) <= st_[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fqs))


def mean_lp_ok(sub: pd.DataFrame, st_: dict) -> bool:
    return (abs(sub.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"])


def pick_five(tag: str, feuille: str, used: set[str], FEUILLES) -> pd.DataFrame | None:
    df, st_, fqs = FEUILLES[feuille]["df"], FEUILLES[feuille]["stats"], FEUILLES[feuille]["freq_cols"]
    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        if tag=="LOW_OLD" and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="HIGH_OLD"and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="LOW_PLD" and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if tag=="HIGH_PLD"and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue

        if not mean_lp_ok(samp, st_): continue
        if sd_ok(samp, st_, fqs):
            samp["source"]=feuille
            samp["group"]=tag
            samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
            samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
            return samp
    return None


def build_sheet() -> pd.DataFrame:
    """Fonction lourde : génère la liste complète – AUCUNE dépendance Streamlit."""
    FEUILLES = load_sheets()
    all_freq_cols = FEUILLES["all_freq_cols"]

    for _ in range(MAX_TRY_FULL):
        taken = {sh:set() for sh in FEUILLES if sh!="all_freq_cols"}
        groups, ok = [], True

        for tag in TAGS:
            parts=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], FEUILLES)
                if sub is None: ok=False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"]+NUM_BASE+all_freq_cols+["source","group","old_cat","pld_cat"]
            return df[order]

    raise RuntimeError("Impossible de générer la liste (contraintes trop strictes).")


# ───────────────────── 5. LANCEMENT EN ARRIÈRE-PLAN ───────────────────── #
if "tirage_future" not in st.session_state:
    # on démarre la tâche une seule fois
    executor = ThreadPoolExecutor(max_workers=1)
    st.session_state.tirage_future = executor.submit(build_sheet)
    st.session_state.executor      = executor
    st.session_state.tirage_done   = False
    st.session_state.tirage_error  = ""

# À chaque exécution du script Streamlit on vérifie si la tâche est terminée
if not st.session_state.tirage_done and st.session_state.tirage_future.done():
    try:
        df = st.session_state.tirage_future.result()    # récupère le résultat ou lève une exception
    except Exception as exc:
        st.session_state.tirage_error = str(exc)
    else:
        st.session_state.tirage_df = df
        words = df.ortho.tolist(); random.shuffle(words)
        st.session_state.stimuli   = words
    st.session_state.tirage_done = True
    st.experimental_rerun()       # rafraîchit immédiatement l’interface


# ───────────────────── 6. GÉNÉRATION HTML / JS ────────────────────────── #
def experiment_html(words: list[str], *, with_download=True,
                    cycle_ms=350, start_ms=14, step_ms=14) -> str:
    download_js = ""; end_message="Merci !" if with_download else "Fin de l’entraînement"
    if with_download:
        download_js = """
    const csv = ["word;rt_ms;response",
                 ...results.map(r => `${{r.word}};${{r.rt_ms}};${{r.response}}`)].join("\\n");
    const a = document.createElement("a");
    a.href   = URL.createObjectURL(new Blob([csv], {{type:"text/csv"}}));
    a.download = "results.csv";
    a.textContent = "Télécharger les résultats";
    a.style.fontSize = "32px";
    a.style.marginTop = "30px";
    document.body.appendChild(a);
    """
    return f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{{height:100%;margin:0;display:flex;flex-direction:column;align-items:center;
justify-content:center;font-family:'Courier New',monospace}}
#scr{{font-size:60px;user-select:none}} #ans{{display:none;font-size:48px;width:60%;text-align:center}}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>window.addEventListener("load",()=>document.body.focus());
const WORDS={json.dumps(words)},CYCLE={cycle_ms},START={start_ms},STEP={step_ms};
let trial=0,results=[];const scr=document.getElementById("scr"),ans=document.getElementById("ans");
function nextTrial(){{if(trial>=WORDS.length){{endExperiment();return}}const w=WORDS[trial],
mask="#".repeat(w.length);let showDur=START,hideDur=CYCLE-showDur,tShow,tHide;
const t0=performance.now();let active=true;(function loop(){{if(!active)return;
scr.textContent=w;tShow=setTimeout(()=>{{if(!active)return;scr.textContent=mask;
tHide=setTimeout(()=>{{if(active){{showDur+=STEP;hideDur=Math.max(0,CYCLE-showDur);loop()}}}},hideDur)}},showDur) }})();
function onSpace(e){{if(e.code==="Space"&&active){{active=false;clearTimeout(tShow);clearTimeout(tHide);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",onSpace);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function onEnter(ev){{if(ev.key==="Enter"){{ev.preventDefault();
results.push({{word:w,rt_ms:rt,response:ans.value.trim()}});ans.removeEventListener("keydown",onEnter);
ans.style.display="none";trial+=1;nextTrial();}}}}ans.addEventListener("keydown",onEnter);}}}}
window.addEventListener("keydown",onSpace);}function endExperiment(){{scr.style.fontSize="40px";
scr.textContent="{end_message}";{download_js}}nextTrial();</script></body></html>"""


# ───────────────────── 7. NAVIGATION ──────────────────────────────────── #
if "page" not in st.session_state:
    st.session_state.page = "intro"


# ─── PAGE INTRO ─── #
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** puis le test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"; st.rerun()


# ─── PAGE FAMILIARISATION ─── #
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **Espace** dès que vous voyez apparaître le mot, "
                "puis tapez ce que vous avez lu et validez avec **Entrée**.")

    placeholder = st.empty()
    if st.session_state.tirage_done:
        if st.session_state.tirage_error:
            placeholder.error(f"Erreur lors du tirage : {st.session_state.tirage_error}")
        else:
            placeholder.success("Stimuli du test prêts !")
    else:
        placeholder.info("Préparation des stimuli du test en arrière-plan…")

    components.v1.html(experiment_html(PRACTICE_WORDS, with_download=False),
                       height=650, scrolling=False)
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"; st.rerun()


# ─── PAGE TEST PRINCIPAL ─── #
else:   # page == "exp"
    st.header("Test principal (80 mots)")

    if not st.session_state.tirage_done:
        st.warning("Les stimuli sont encore en cours de génération… Merci de patienter.")
        time.sleep(1)          # petite attente puis rafraîchissement automatique
        st.experimental_rerun()

    if st.session_state.tirage_error:
        st.error(f"Impossible de poursuivre : {st.session_state.tirage_error}")
        st.stop()

    tirage_df = st.session_state.tirage_df
    STIMULI   = st.session_state.stimuli

    with st.expander("Statistiques du tirage (aperçu)"):
        st.dataframe(tirage_df.head())

    components.v1.html(experiment_html(STIMULI, with_download=True),
                       height=650, scrolling=False)
