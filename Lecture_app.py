# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test principal ; écrans 60 / 120 Hz)

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import inspect, json, random, sys
from pathlib import Path
from string import Template
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ────────────────────────── OUTIL RERUN ───────────────────────────────────
def do_rerun() -> None:
    st.session_state["_rerun_flag"] = True
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ───────────────────────── CONFIG GLOBALE ─────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 0. CONSTANTES
# =============================================================================
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = {"letters": .68, "phons": .68}
SD_MULT            = {"letters": 2, "phons": 2,
                      "old20": .28, "pld20": .28, "freq": 1.9}

XLSX               = Path(__file__).with_name("Lexique.xlsx")
TAGS               = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG    = 5            # 5 mots × 4 feuilles × 4 tags = 80
MAX_TRY_TAG        = MAX_TRY_FULL = 1_000
rng                = random.Random()

NUM_BASE           = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS     = ["PAIN", "EAU"]

# =============================================================================
# 1. OUTILS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(" ",  "", regex=False)
         .str.replace("\xa0","", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:            # -1 LOW ; +1 HIGH ; 0 autre
    return -1 if "LOW" in tag else (1 if "HIGH" in tag else 0)

# =============================================================================
# 2. CHARGEMENT DES FEUILLES (exactement comme votre script)
# =============================================================================
@st.cache_data(show_spinner=False)
def load_sheets() -> Dict[str, Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()

    xls          = pd.ExcelFile(XLSX)
    sheet_names  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4."); st.stop()

    feuilles: Dict[str, Dict] = {}
    all_freq_cols: set[str]   = set()

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
        df          = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()        for c in NUM_BASE}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in NUM_BASE + freq_cols}

        feuilles[sh] = {"df": df,
                        "stats": stats,
                        "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

# =============================================================================
# 3. FONCTIONS DE TIRAGE
# =============================================================================
def masks(df: pd.DataFrame, st_: Dict) -> Dict[str, pd.Series]:
    return {
        "LOW_OLD" : df.old20 < st_["m_old20"],
        "HIGH_OLD": df.old20 > st_["m_old20"],
        "LOW_PLD" : df.pld20 < st_["m_pld20"],
        "HIGH_PLD": df.pld20 > st_["m_pld20"],
    }

def sd_ok(sub: pd.DataFrame, st_: Dict, fq_cols: List[str]) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq_cols)
    )

def mean_lp_ok(sub: pd.DataFrame, st_: Dict) -> bool:
    return (
        abs(sub.nblettres.mean() - st_["m_nblettres"]) <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(sub.nbphons.mean()   - st_["m_nbphons"])   <= MEAN_DELTA["phons"]   * st_["sd_nbphons"]
    )

def pick_five(tag: str, feuille: str, used: set[str], F: Dict) -> pd.DataFrame | None:
    df, st_  = F[feuille]["df"],   F[feuille]["stats"]
    fq_cols  = F[feuille]["freq_cols"]
    pool     = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]

    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fq_cols):
            continue

        samp["source"]   = feuille
        samp["group"]    = tag
        samp["old_cat"]  = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"]  = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None


def build_sheet() -> pd.DataFrame:
    F             = load_sheets()
    all_freq_cols = F["all_freq_cols"]

    for _ in range(MAX_TRY_FULL):
        taken  = {sh:set() for sh in F if sh != "all_freq_cols"}
        groups = []; ok=True

        for tag in TAGS:
            bloc=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                bloc.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + \
                    ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    st.error("Impossible de générer la liste (contraintes trop strictes).")
    st.stop()

# =============================================================================
# 4. GÉNÉRATION HTML / JS DE LA TÂCHE
# =============================================================================
HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load",()=>document.body.focus());
$FULLSCREEN
const WORDS=$WORDS,CYCLE=$CYCLE,START=$START,STEP=$STEP;
let trial=0,results=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function nextTrial(){if(trial>=WORDS.length){fin();return;}
 const w=WORDS[trial],mask="#".repeat(w.length);let show=START,hide=CYCLE-show,t0=performance.now(),active=true,tS,tH;
 (function loop(){if(!active)return;
   scr.textContent=w;
   tS=setTimeout(()=>{if(!active)return;
     scr.textContent=mask;
     tH=setTimeout(()=>{if(active){show+=STEP;hide=Math.max(0,CYCLE-show);loop();}},hide);
   },show);
 })();
 function onSpace(e){if(e.code==="Space"&&active){
   active=false;clearTimeout(tS);clearTimeout(tH);
   const rt=Math.round(performance.now()-t0);
   window.removeEventListener("keydown",onSpace);
   scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
   ans.addEventListener("keydown",function onEnter(ev){
     if(ev.key==="Enter"){ev.preventDefault();
       results.push({word:w,rt_ms:rt,response:ans.value.trim()});
       ans.removeEventListener("keydown",onEnter);ans.style.display="none";
       trial++;nextTrial();}});}}
 window.addEventListener("keydown",onSpace);}
function fin(){scr.style.fontSize="40px";scr.textContent=$END_MSG;$DOWNLOAD}
$STARTER
</script></body></html>
""")

def experiment_html(words: List[str], *, with_download=True,
                    cycle_ms=350, start_ms=14, step_ms=14, fullscreen=False) -> str:
    download_js = ""
    if with_download:
        download_js = r"""
const csv=["word;rt_ms;response",
           ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";
document.body.appendChild(a);""".replace("$","$$")

    starter = "nextTrial();"
    fullscreen_js = ""
    if fullscreen:
        starter = r"""
scr.textContent="Appuyez sur la barre ESPACE pour commencer";
function first(e){if(e.code==="Space"){window.removeEventListener("keydown",first);
document.documentElement.requestFullscreen?.();nextTrial();}}
window.addEventListener("keydown",first);"""

    return HTML_TPL.substitute(
        WORDS=json.dumps(list(words)),
        CYCLE=cycle_ms, START=start_ms, STEP=step_ms,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download_js, FULLSCREEN=fullscreen_js, STARTER=starter)

# =============================================================================
# 5. VARIABLES DE SESSION
# =============================================================================
for k,v in {"page":"screen_test","tirage_ok":False,"tirage_run":False,
            "stimuli":[], "tirage_df":pd.DataFrame(),"exp_started":False,
            "hz_val":None}.items():
    st.session_state.setdefault(k,v)
p = st.session_state

# =============================================================================
# 6. COMPOSANT TEST DE FRÉQUENCE ÉCRAN
# =============================================================================
TEST_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;background:#000;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:24px 0}button{font-size:22px;padding:6px 26px;margin:4px}</style></head><body>
<h2>Test de fréquence</h2><div id="res">--</div><button id="go" onclick="mesure()">Démarrer</button>
<script>
function mesure(){const r=document.getElementById('res'),b=document.getElementById('go');
b.disabled=true;r.textContent='Mesure…';let f=0,t0=performance.now();
function loop(){f++;if(f<120){requestAnimationFrame(loop);}else{
const hz=f*1000/(performance.now()-t0);r.textContent='≈ '+hz.toFixed(1)+' Hz';
Streamlit.setComponentValue(hz.toFixed(1));b.disabled=false;}}requestAnimationFrame(loop);}
Streamlit.setComponentReady();
</script></body></html>"""

def nearest_hz(x:float)->int:
    return min([60,75,90,120,144], key=lambda v:abs(v-x))

def go(page:str): p.page=page; do_rerun()

# =============================================================================
# 7. PAGES STREAMLIT
# =============================================================================
# 0. — Test écran
if p.page=="screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")
    kwargs=dict(height=520,scrolling=False)
    if "key" in inspect.signature(components.html).parameters:
        kwargs["key"]="hz_test"
    val=components.html(TEST_HTML, **kwargs)
    if isinstance(val,(int,float,str)):
        try:p.hz_val=float(val)
        except ValueError:pass
    if p.hz_val is not None:
        st.write(f"Fréquence détectée ≈ **{nearest_hz(p.hz_val)} Hz**")
    st.divider()
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("Suivant 60 Hz ➜"):  go("intro")
    with c2:
        if st.button("Suivant 120 Hz ➜"): go("intro")
    with c3:
        if st.button("Suivant Autre Hz ➜"):go("incompatible")

# 1. — Présentation + tirage
elif p.page=="intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown("""
Des mots sont présentés très brièvement puis masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.  

Déroulement : 2 essais d’entraînement puis 80 essais de test.
""")
    if not p.tirage_run and not p.tirage_ok:
        p.tirage_run=True; do_rerun()
    elif p.tirage_run and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df=build_sheet(); mots=df["ortho"].tolist(); random.shuffle(mots)
            p.tirage_df=df; p.stimuli=mots
            p.tirage_ok=True; p.tirage_run=False
        st.success("Tirage terminé !")
    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")

# 1-bis — incompatible
elif p.page=="incompatible":
    st.error("Désolé, cette expérience nécessite un écran 60 Hz ou 120 Hz.")

# 2. — Familiarisation
elif p.page=="fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** dès qu’un mot apparaît, tapez-le puis **Entrée**.")
    components.html(experiment_html(PRACTICE_WORDS, with_download=False),
                    height=650, scrolling=False)
    st.divider()
    if st.button("Passer au test principal"):
        p.page="exp"; p.exp_started=False; do_rerun()

# 3. — Test principal
elif p.page=="exp":
    if not p.exp_started:
        st.header("Test principal : 80 mots")
        with st.expander("Aperçu du tirage (5 lignes)"):
            st.dataframe(p.tirage_df.head())
        if st.button("Commencer le test (plein écran)"):
            p.exp_started=True; do_rerun()
    else:
        components.html(experiment_html(p.stimuli, with_download=True, fullscreen=True),
                        height=700, scrolling=False)

else:
    st.stop()
