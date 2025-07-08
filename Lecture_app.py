# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Tâche de reconnaissance de mots masqués
(familiarisation + test 80 mots, timing à la frame / 60 Hz)

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components   # ← import correct

# ────────────────────────── OUTIL RERUN ────────────────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ───────────────────────── CONFIG STREAMLIT ────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
.css-1d391kg {display:none;}                      /* ancien spinner            */
button:disabled{opacity:0.45 !important;cursor:not-allowed !important;}
</style>""", unsafe_allow_html=True)

# =============================================================================
# 0. ÉTATS PERSISTANTS
# =============================================================================
default_states = dict(page="screen_test", hz_ok=False,
                      tirage_ok=False, tirage_running=False)
for k, v in default_states.items():
    st.session_state.setdefault(k, v)

# =============================================================================
# 1. PARAMÈTRES DU TIRAGE
# =============================================================================
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = {"letters": .68, "phons": .68}
SD_MULT            = {"letters": 2, "phons": 2,
                      "old20": .28, "pld20": .28, "freq": 1.9}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# =============================================================================
# 2. OUTILS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str)
                           .str.replace(" ",  "", regex=False)
                           .str.replace("\u00a0","", regex=False)
                           .str.replace(",", ".", regex=False),
                         errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:   # -1 = LOW ; +1 = HIGH
    return -1 if "LOW" in tag else 1

# =============================================================================
# 3. CHARGEMENT EXCEL + TIRAGE DES 80 MOTS
# =============================================================================
@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
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

        for c in NUM_BASE + freq_cols:
            df[c] = to_float(df[c])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()        for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in ("old20","pld20","nblettres","nbphons") + tuple(freq_cols)}
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
    return (abs(sub.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fqs     = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fqs): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F = load_sheets(); all_freq_cols = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken = {sh:set() for sh in F if sh!="all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            parts=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source","group","old_cat","pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste (contraintes trop strictes)."); st.stop()

# =============================================================================
# 4A. HTML – TEST 60 Hz (sans bouton Continuer)
# =============================================================================
TEST60_HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
          display:flex;flex-direction:column;align-items:center;justify-content:center;
          font-family:Arial,Helvetica,sans-serif;text-align:center}
#res{font-size:48px;margin:30px 0}
button{font-size:24px;padding:8px 28px}
</style>
</head>
<body>
<h2>Test de fréquence d’écran<br/>(cible&nbsp;: 60&nbsp;Hz)</h2>
<p>Cliquez sur «&nbsp;Démarrer&nbsp;».<br>Le programme mesure la fréquence de votre moniteur.</p>
<div id="res">--</div>
<button id="start">Démarrer</button>
<script>
const res=document.getElementById("res");
document.getElementById("start").onclick=()=>{
  document.getElementById("start").disabled=true;
  let t=[], n=150;
  const step=k=>{
    t.push(k); if(t.length<n){ requestAnimationFrame(step); }
    else{
      let d=[]; for(let i=2;i<t.length;i++) d.push(t[i]-t[i-1]);
      const mean=d.reduce((a,b)=>a+b,0)/d.length;
      const hz  =1000/mean;
      res.textContent=`≈ ${hz.toFixed(1)} Hz`;
      const ok=hz>58&&hz<62;
      res.style.color=ok?"lime":"red";
      document.getElementById("start").disabled=false;
      if(ok){ Streamlit.setComponentValue("ok"); }
    }
  };
  requestAnimationFrame(step);
};
</script>
</body>
</html>
"""

# =============================================================================
# 4B. HTML – EXPÉRIENCE (requestAnimationFrame)
# =============================================================================
EXP_HTML = Template(r"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;display:flex;flex-direction:column;
          align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;color:#fff;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load",()=>document.body.focus());
const WORDS   = $WORDS;
const CYCLE_F = $CYCLE_F;
const START_F = $START_F;
const STEP_F  = $STEP_F;

let trial=0;
let results=[];
const scr=document.getElementById("scr");
const ans=document.getElementById("ans");

function waitFrames(n,cb){
  let c=0; function step(){ if(c++>=n){ cb(); } else{ requestAnimationFrame(step);} }
  requestAnimationFrame(step);
}
function present(){
  if(trial>=WORDS.length){ fin(); return; }
  const w=WORDS[trial], mask="#".repeat(w.length);
  let showF=START_F, hideF=CYCLE_F-showF;
  const t0=performance.now(); let active=true;
  function cycle(){
    if(!active) return;
    scr.textContent=w;
    waitFrames(showF,()=>{ if(!active)return;
      scr.textContent=mask;
      waitFrames(hideF,()=>{ if(active){
        showF+=STEP_F; hideF=Math.max(0,CYCLE_F-showF); cycle();
      }});
    });
  }
  cycle();
  function onSpace(e){
    if(e.code==="Space"&&active){
      active=false;
      const rt=Math.round(performance.now()-t0);
      window.removeEventListener("keydown",onSpace);
      scr.textContent="";
      ans.style.display="block"; ans.value=""; ans.focus();
      ans.addEventListener("keydown",function onEnter(ev){
        if(ev.key==="Enter"){
          ev.preventDefault();
          results.push({word:w,rt_ms:rt,response:ans.value.trim()});
          ans.removeEventListener("keydown",onEnter);
          ans.style.display="none";
          trial++; present();
        }
      });
    }
  }
  window.addEventListener("keydown",onSpace);
}
function fin(){
  scr.style.fontSize="40px"; scr.textContent=$END_MSG;
  $DOWNLOAD
}
$STARTER
</script>
</body>
</html>
""")

# =============================================================================
# 4C. CONSTRUCTEURS HTML
# =============================================================================
def calibration_html() -> str:
    return TEST60_HTML

def experiment_html(words, *, cycle_frames=21, start_frames=1, step_frames=1,
                    with_download=True, fullscreen=False):
    # téléchargement --------------------------------------------------------
    download_js = ""
    if with_download:
        download_js = r"""
const csv=["word;rt_ms;response",
           ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";
a.textContent="Télécharger les résultats";
a.style.fontSize="32px";
a.style.marginTop="30px";
document.body.appendChild(a);"""
    download_js = download_js.replace("$", "$$")

    # démarrage -------------------------------------------------------------
    if fullscreen:
        starter_js = r"""
scr.textContent="Appuyez sur la barre ESPACE pour commencer";
function first(e){ if(e.code==="Space"){
  window.removeEventListener("keydown",first);
  document.documentElement.requestFullscreen?.(); present();
}}
window.addEventListener("keydown",first);"""
    else:
        starter_js = "present();"

    return EXP_HTML.substitute(
        WORDS=json.dumps(words),
        CYCLE_F=cycle_frames,
        START_F=start_frames,
        STEP_F=step_frames,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download_js,
        STARTER=starter_js
    )

# =============================================================================
# 5.  PAGES STREAMLIT
# =============================================================================
# ─────────── PAGE 0 : TEST 60 Hz ────────────────────────────────────────────
if st.session_state.page == "screen_test":
    st.write("### Vérification de l’écran (60 Hz requis)")
    # le composant renvoie "ok" quand la fréquence est comprise entre 58 et 62 Hz
    hz_value = components.html(calibration_html(), height=600, scrolling=False, key="calib")
    if hz_value == "ok":
        st.session_state.hz_ok = True
    st.button("Passer à la présentation ➜",
              disabled=not st.session_state.hz_ok,
              on_click=lambda: (st.session_state.update(page="intro"), do_rerun()))

# ─────────── PAGE 1 : INTRO & TIRAGE ────────────────────────────────────────
elif st.session_state.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")
    st.markdown("""
Des mots seront brièvement présentés puis masqués (suite de “#”).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.

1. Entraînement (2 mots)  2. Test principal (80 mots)
""")
    if not st.session_state.tirage_running and not st.session_state.tirage_ok:
        st.session_state.tirage_running = True; do_rerun()
    if st.session_state.tirage_running and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet()
            mots = df["ortho"].tolist(); random.shuffle(mots)
            st.session_state.stimuli = mots
            st.session_state.tirage_ok = True
            st.session_state.tirage_running = False
        st.success("Tirage terminé !")
    if st.session_state.tirage_ok:
        st.button("Commencer la familiarisation",
                  on_click=lambda: (st.session_state.update(page="fam"), do_rerun()))

# ─────────── PAGE 2 : FAMILIARISATION ──────────────────────────────────────
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** dès que le mot apparaît, saisissez-le puis **Entrée**.")
    components.html(
        experiment_html(PRACTICE_WORDS, with_download=False),
        height=650, scrolling=False, key="fam_html")
    st.divider()
    st.button("Passer au test principal",
              on_click=lambda: (st.session_state.update(page="exp"), do_rerun()))

# ─────────── PAGE 3 : TEST PRINCIPAL ───────────────────────────────────────
elif st.session_state.page == "exp":
    components.html(
        experiment_html(st.session_state.stimuli,
                        with_download=True, fullscreen=True),
        height=700, scrolling=False, key="exp_html")
