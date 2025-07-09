# ─── exp3_frame.py ───────────────────────────────────────────────────────
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
• 60 / 120 Hz
• Responsive (TV, PC, tablette, smartphone)
• Mobile : tap + clavier virtuel QWERTZ (sans suggestions)
• PWA : ajout à l’écran d’accueil = plein-écran natif
"""
from __future__ import annotations
import inspect, json, random, time
from pathlib import Path
from string import Template
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ────────────────────── Streamlit helpers ───────────────────────────────
def do_rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ─────────────────────────── constantes ─────────────────────────────────
XLSX            = Path(__file__).with_name("Lexique.xlsx")
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG = 5
MAX_TRY_TAG     = MAX_TRY_FULL = 1_000
rng             = random.Random()

NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]

CYCLE_MS        = 350     # mot + masque
CROSS_MS        = 500     # croix fixation

MEAN_FACTOR_OLDPLD = .35
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

# ────────────────────────── utilitaires ---------------------------------
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(r"[ ,\xa0]", "", regex=True).str.replace(",", "."),
        errors="coerce",
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag:str)->int: return -1 if "LOW" in tag else (1 if "HIGH" in tag else 0)
def nearest_hz(x:float)->int: return min([60,75,90,120,144], key=lambda v:abs(v-x))

# ───── 1. lecture Excel ─────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_sheets()->Dict[str,Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable"); st.stop()
    xls  = pd.ExcelFile(XLSX)
    shs  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(shs)!=4: st.error("Il faut exactement 4 feuilles Feuil1…Feuil4"); st.stop()

    feuilles, all_freq = {}, set()
    for sh in shs:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()
        freq = [c for c in df.columns if c.startswith("freq")]
        all_freq.update(freq)
        need = ["ortho","old20","pld20","nblettres","nbphons"]+freq
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()
        for c in NUM_BASE+freq: df[c]=to_float(df[c])
        df["ortho"]=df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)
        stats = {f"m_{c}":df[c].mean() for c in NUM_BASE}
        stats|={f"sd_{c}":df[c].std(ddof=0) for c in NUM_BASE+freq}
        feuilles[sh]=dict(df=df,stats=stats,freq_cols=freq)
    feuilles["all_freq_cols"]=sorted(all_freq)
    return feuilles

# ───── 2. tirage 80 mots ────────────────────────────────────────────────
def masks(df, st_): return dict(
    LOW_OLD = df.old20 < st_["m_old20"],
    HIGH_OLD= df.old20 > st_["m_old20"],
    LOW_PLD = df.pld20 < st_["m_pld20"],
    HIGH_PLD= df.pld20 > st_["m_pld20"],
)

def sd_ok(sub, st_, fq):
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"]*SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]  *SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]    *SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]    *SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0)<=st_[f"sd_{c}"]*SD_MULT["freq"] for c in fq)
    )

def mean_lp_ok(s,st_):
    return (
        abs(s.nblettres.mean()-st_["m_nblettres"])<=MEAN_DELTA["letters"]*st_["sd_nblettres"] and
        abs(s.nbphons.mean()  -st_["m_nbphons"])  <=MEAN_DELTA["phons"]  *st_["sd_nbphons"]
    )

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]; fq=F[feuille]["freq_cols"]
    pool = df.loc[masks(df,st_)[tag] & ~df.ortho.isin(used)]
    if len(pool)<N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="HIGH_OLD" and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="LOW_PLD"  and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag=="HIGH_PLD" and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp,st_) or not sd_ok(samp,st_,fq): continue
        samp["source"],samp["group"]=feuille,tag
        samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet()->pd.DataFrame:
    F=load_sheets(); all_freq=F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        take={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            bloc=[]
            for sh in take:
                sub=pick_five(tag,sh,take[sh],F)
                if sub is None: ok=False; break
                bloc.append(sub); take[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc,ignore_index=True)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            return df[["ortho"]+NUM_BASE+all_freq+["source","group","old_cat","pld_cat"]]
    st.error("Impossible de générer la liste."); st.stop()

# ───── 3. template HTML PWA + clavier virtuel ───────────────────────────
HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>
<meta name="theme-color" content="#000000"/>
<link rel="manifest" id="pwa-manifest">
<style>
html,body{margin:0;width:100vw;height:100vh;background:#000;color:#fff;
          display:flex;flex-direction:column;align-items:center;justify-content:center;
          font-family:'Courier New',monospace;overflow:hidden;touch-action:manipulation}
#container{display:flex;flex-direction:column;align-items:center;justify-content:center}
#scr{font-size:7vw;line-height:1.15;max-width:90vw;text-align:center;
     user-select:none;color:#fff;text-shadow:0 2px 6px #222}
#ans{display:none;font-size:5vw;min-font-size:22px;width:70vw;max-width:92vw;
     text-align:center;background:#fff;color:#000;border:none;padding:1.1vw .6vw;
     margin-top:2vh;border-radius:.5vw;box-shadow:0 2px 8px #3335;outline:none}
#vk{display:none;flex-direction:column;align-items:center;margin-top:2vh}
.krow{display:flex;justify-content:center;margin:.2vh 0}
.key{user-select:none;border:none;margin:0 .8vw;border-radius:.8vw;
     background:#333;color:#fff;font-weight:600;font-size:6vw;min-width:8vw;padding:.6vh 0}
.key:active{background:#555}
@media (min-width:500px){.key{font-size:28px}}
@media (max-width:700px){#scr{font-size:14vw}#ans{font-size:8vw}}
@media (max-width:470px){#scr{font-size:18vw}#ans{font-size:11vw}}
@media (min-width:1600px) and (min-height:900px){#scr{font-size:4vw}#ans{font-size:2.5vw}}
</style></head><body tabindex="0">
<div id="container">
  <div id="scr"></div>
  <input id="ans" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"/>
  <div id="vk"></div>
</div>
<script>
/* ---------- PWA manifest + SW --------------------------------------- */
(function(){
  const manifest={
    name:"Expérience 3",short_name:"Exp3",start_url:".",display:"standalone",
    background_color:"#000000",theme_color:"#000000",icons:[]
  };
  const blob=new Blob([JSON.stringify(manifest)],{type:"application/json"});
  document.getElementById('pwa-manifest').href=URL.createObjectURL(blob);
  if('serviceWorker' in navigator){
    const sw="self.addEventListener('fetch',e=>{});";
    navigator.serviceWorker.register(URL.createObjectURL(new Blob([sw],{type:"text/js"})));
  }
})();
/* ---------- outils JS ----------------------------------------------- */
function gid(x){return document.getElementById(x);}
function resizeAll(){
  let w=innerWidth,h=innerHeight,base=Math.min(w,h);
  gid('scr').style.fontSize=Math.max(Math.round(base*0.08),26)+'px';
  gid('ans').style.fontSize=Math.max(Math.round(base*0.054),20)+'px';
  gid('ans').style.width=Math.min(w*0.7,650)+'px';
}
addEventListener('resize',resizeAll);
addEventListener('orientationchange',resizeAll);
addEventListener('load',()=>{setTimeout(resizeAll,60);});

/* ------ paramètres Python ------------------------------------------- */
const WORDS=$WORDS,START_F=$STARTF,STEP_F=$STEPF,CYCLE_F=$CYCLEF,CROSS_F=$CROSSF;
const TOUCH_TRIG=$ENABLE_TOUCH;
/* -------------------------------------------------------------------- */
const IS_TOUCH=('ontouchstart'in window)||(navigator.maxTouchPoints>0);
let trial=0,results=[],scr=gid('scr'),ans=gid('ans'),vk=gid('vk');
let finishAnswer=()=>{};

/* ---------- clavier virtuel ----------------------------------------- */
function buildVK(){
  if(vk.firstChild)return;
  const rows=["QWERTZUIOP","ASDFGHJKL","YXCVBNMÉÈÇÏ","←↵"];
  rows.forEach(r=>{
    const div=document.createElement('div');div.className='krow';
    [...r].forEach(c=>{const b=document.createElement('button');b.className='key';b.textContent=c;div.appendChild(b);});
    vk.appendChild(div);
  });
  vk.addEventListener('pointerdown',e=>{
    const t=e.target;if(!t.classList.contains('key'))return;
    e.preventDefault();
    const k=t.textContent;
    if(k==="←")ans.value=ans.value.slice(0,-1);
    else if(k==="↵")finishAnswer();
    else ans.value+=k;
  },{passive:false});
}

/* ---------- séquence d’un essai ------------------------------------- */
function nextTrial(){
  if(trial>=WORDS.length){fin();return;}
  const w=WORDS[trial],mask="#".repeat(w.length);let active=true;
  scr.textContent="+";let frame=0;
  const crossLoop=()=>{if(!active)return;
    if(++frame>=CROSS_F)startStimulus();else requestAnimationFrame(crossLoop);}
  requestAnimationFrame(crossLoop);

  function startStimulus(){
    let showF=START_F,phase="show",f2=0;const t0=performance.now();
    function stimLoop(){
      if(!active)return;
      if(phase==="show"){
        if(f2===0)scr.textContent=w;
        if(++f2>=showF){phase="mask";f2=0;scr.textContent=mask;}
      }else{
        const hideF=Math.max(0,CYCLE_F-showF);
        if(++f2>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F);phase="show";f2=0;}
      }
      requestAnimationFrame(stimLoop);
    }
    requestAnimationFrame(stimLoop);

    function onTrig(e){
      if(e instanceof KeyboardEvent && e.code!=="Space")return;
      if(e instanceof PointerEvent)e.preventDefault();
      if(!active)return;
      active=false;removeEventListener('keydown',onTrig);
      if(TOUCH_TRIG)removeEventListener('pointerdown',onTrig);
      promptAnswer(Math.round(performance.now()-t0));
    }
    addEventListener('keydown',onTrig);
    if(TOUCH_TRIG)addEventListener('pointerdown',onTrig,{passive:false});
  }

  function promptAnswer(rt){
    scr.textContent="";ans.value="";ans.style.display="block";
    if(IS_TOUCH){ans.readOnly=true;buildVK();vk.style.display="flex";}
    else{ans.readOnly=false;setTimeout(()=>ans.focus(),40);}
    resizeAll();
    function keyEnter(ev){if(ev.key==="Enter"){ev.preventDefault();finishAnswer();}}
    addEventListener('keydown',keyEnter);
    finishAnswer=function(){
      removeEventListener('keydown',keyEnter);
      ans.style.display="none";vk.style.display="none";
      results.push({word:w,rt_ms:rt,response:ans.value.trim()});
      trial++;nextTrial();
    };
  }
}
/* ---------- fin ------------------------------------------------------ */
function fin(){
  scr.style.fontSize="min(6vw,48px)";
  scr.textContent=$END_MSG;$DOWNLOAD;resizeAll();
}
/* ---------- démarrage ----------------------------------------------- */
function isStandalone(){return window.matchMedia('(display-mode: standalone)').matches||navigator.standalone;}
scr.textContent="Touchez l’écran ou appuyez sur ESPACE pour commencer";
function first(e){
  if((e instanceof KeyboardEvent && e.code==="Space")||(e instanceof PointerEvent)){
    removeEventListener('keydown',first);removeEventListener('pointerdown',first);
    if(!isStandalone() && !IS_TOUCH){document.documentElement.requestFullscreen?.();}
    nextTrial();
  }}
addEventListener('keydown',first);
addEventListener('pointerdown',first,{passive:false});
</script></body></html>""")

# ───── 3-bis. fonction de construction HTML -----------------------------
def experiment_html(words:List[str],hz:int,*,with_download=True,touch_trigger=True)->str:
    frame  =1000/hz
    cycle_f=int(round(CYCLE_MS/frame))
    cross_f=int(round(CROSS_MS/frame))
    scale  =hz//60
    start_f=step_f=1*scale

    dl_js=""
    if with_download:
        dl_js=r"""
const csv=["word;rt_ms;response",
...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="min(6vw,32px)";a.style.marginTop="30px";
document.body.appendChild(a);""".replace("$","$$")

    return HTML_TPL.substitute(
        WORDS=json.dumps(list(words)),
        STARTF=start_f,STEPF=step_f,CYCLEF=cycle_f,CROSSF=cross_f,
        END_MSG=json.dumps("Merci !"),
        DOWNLOAD=dl_js,ENABLE_TOUCH=("true" if touch_trigger else "false")
    )

# ───── 4. composant test fréquence (identique) --------------------------
TEST_HTML = r""" <same as précédent> """

# ───── 5-6. état session & navigation Streamlit (identiques) ------------
# (reprendre sans aucune modification la fin du script précédent,
#  de defaults jusqu’à st.stop())
