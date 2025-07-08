# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Tâche de reconnaissance de mots masqués
(familiarisation + test 80 mots) – calibrée 60 Hz

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

# ────────────────────────── RERUN ───────────────────────────────────────────
do_rerun = lambda: (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ───────────────────────── CONFIG STREAMLIT ────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
  #MainMenu, header, footer {visibility:hidden;}
  .css-1d391kg{display:none;}  /* ancien spinner */
</style>""", unsafe_allow_html=True)

# =============================================================================
# PARAMÈTRES DU TIRAGE
# =============================================================================
MEAN_FACTOR_OLDPLD = 0.45
MEAN_DELTA         = {"letters": 0.68, "phons": 0.68}
SD_MULT            = {"letters": 2.0, "phons": 2.0,
                      "old20": 0.28, "pld20": 0.28, "freq": 1.9}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# =============================================================================
# 1. OUTILS TIRAGE (inchangés)
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace("[ ,\xa0]", "", regex=True)
                      .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int: return -1 if "LOW" in tag else 1

@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheets = [n for n in xls.sheet_names if n.lower().startswith("feuil")]
    if len(sheets) != 4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        freq = [c for c in df.columns if c.startswith("freq")]
        all_freq.update(freq)
        need = ["ortho","old20","pld20","nblettres","nbphons"] + freq
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for c in NUM_BASE + freq: df[c] = to_float(df[c])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()
                 for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0)
                  for c in ("old20","pld20","nblettres","nbphons")+tuple(freq)}
        feuilles[sh] = {"df":df, "stats":stats, "freq_cols":freq}

    feuilles["all_freq_cols"] = sorted(all_freq)
    return feuilles

def masks(df, st_):
    return {"LOW_OLD": df.old20 < st_["m_old20"]-st_["sd_old20"],
            "HIGH_OLD":df.old20 > st_["m_old20"]+st_["sd_old20"],
            "LOW_PLD": df.pld20 < st_["m_pld20"]-st_["sd_pld20"],
            "HIGH_PLD":df.pld20 > st_["m_pld20"]+st_["sd_pld20"]}

def sd_ok(sub, st_, fq_cols):
    return (sub.nblettres.std(ddof=0)<=st_["sd_nblettres"]*SD_MULT["letters"] and
            sub.nbphons.std(ddof=0)  <=st_["sd_nbphons"]  *SD_MULT["phons"]  and
            sub.old20.std(ddof=0)    <=st_["sd_old20"]    *SD_MULT["old20"]  and
            sub.pld20.std(ddof=0)    <=st_["sd_pld20"]    *SD_MULT["pld20"] and
            all(sub[c].std(ddof=0)<=st_[f"sd_{c}"]*SD_MULT["freq"] for c in fq_cols))

def mean_lp_ok(sub, st_):
    return (abs(sub.nblettres.mean()-st_["m_nblettres"])<=MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()  -st_["m_nbphons"])  <=MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fqs     = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df,st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(1000):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="HIGH_OLD" and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="LOW_PLD"  and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if tag=="HIGH_PLD" and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if not mean_lp_ok(samp,st_) or not sd_ok(samp,st_,fqs): continue
        samp["source"],samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F = load_sheets(); all_freq = F["all_freq_cols"]
    for _ in range(1000):
        taken = {sh:set() for sh in F if sh!="all_freq_cols"}
        blocs, ok = [], True
        for tag in TAGS:
            part=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            blocs.append(shuffled(pd.concat(part, ignore_index=True)))
        if ok:
            df = pd.concat(blocs, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq + \
                    ["source","group","old_cat","pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste."); st.stop()

# =============================================================================
# 2. TEMPLATE HTML / JS (plein-écran, fond noir, sortie FS à la fin)
# =============================================================================
CROSS_FR, SHOW_START, STEP_FR, CYCLE_FR = 30, 1, 1, 20   # frames 60 Hz

HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace;
background:#000;color:#fff}
#scr{font-size:60px;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center;color:#000}
</style></head>
<body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const WORDS = $WORDS;

/* --- force plein-écran sur la page Streamlit principale --------------- */
function goFS(){
  const doc = parent.document;
  if(!doc.fullscreenElement && doc.documentElement.requestFullscreen){
      doc.documentElement.requestFullscreen().catch(()=>{});
  }
}
parent.document.addEventListener('click',  goFS,{once:true});
parent.document.addEventListener('keydown',goFS,{once:true});

/* --- mesure fréquence -------------------------------------------------- */
function fpsAvg(n=120){
  return new Promise(ok=>{
    const a=[]; function s(t){a.push(t);
      a.length<n?requestAnimationFrame(s):
      ok(1000/((a.slice(1).reduce((p,c,i)=>p+c-a[i],a[0]))/(n-1))); }
    requestAnimationFrame(s);
  });
}

/* --- start / block ----------------------------------------------------- */
fpsAvg().then(fps=>{
  if(fps<55||fps>65){
    document.body.innerHTML=
     `<div style='text-align:center;font-size:32px;max-width:80%'>
        Fréquence détectée : <b>$${fps.toFixed(1)} Hz</b><br/>
        Veuillez utiliser / régler un écran 60 Hz.</div>`;
    return;
  }
  run();
});

function run(){
 let trial=0,results=[];
 const scr=document.getElementById('scr'),
       ans=document.getElementById('ans');

 function next(){
   if(trial>=WORDS.length){fin();return;}
   let f=0; scr.textContent='+';
   const cross=()=>++f<$CROSS_FR?requestAnimationFrame(cross)
                                :stim(WORDS[trial]);
   requestAnimationFrame(cross);
 }

 function stim(word){
   const mask='#'.repeat(word.length);
   let show=$SHOW_START,fr=0,active=true,t0=performance.now();
   const loop=()=>{
     if(!active)return;
     scr.textContent = fr<show ? word : fr<$CYCLE_FR ? mask : scr.textContent;
     if(++fr==$CYCLE_FR){show+=$STEP_FR;fr=0;}
     requestAnimationFrame(loop);
   };requestAnimationFrame(loop);

   const onSp=e=>{
     if(e.code==='Space'&&active){
       active=false;parent.document.removeEventListener('keydown',onSp);
       const rt=Math.round(performance.now()-t0);
       scr.textContent=''; ans.style.display='block'; ans.value=''; ans.focus();
       ans.addEventListener('keydown',function onEnt(ev){
         if(ev.key==='Enter'){
           ev.preventDefault();
           results.push({word,rt_ms:rt,response:ans.value.trim()});
           ans.removeEventListener('keydown',onEnt);
           ans.style.display='none'; trial++; next();
         }});
     }};
   parent.document.addEventListener('keydown',onSp);
 }

 function fin(){
   try{parent.document.exitFullscreen();}catch(e){}
   scr.style.fontSize='40px'; scr.textContent=$END_MSG; $DOWNLOAD
 }
 next();
}
</script></body></html>
""")

def experiment_html(words, *, with_download=True):
    download_js=""
    if with_download:
        download_js=r"""
const csv=["word;rt_ms;response",
           ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";
a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";
document.body.appendChild(a);"""
    download_js = download_js.replace("$","$$")

    return HTML_TPL.substitute(
        WORDS=json.dumps(words),
        CROSS_FR=CROSS_FR, CYCLE_FR=CYCLE_FR,
        STEP_FR=STEP_FR,  SHOW_START=SHOW_START,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download_js
    )

# =============================================================================
# 3. NAVIGATION STREAMLIT
# =============================================================================
if "page" not in st.session_state:            st.session_state.page="intro"
if "tirage_en_cours" not in st.session_state: st.session_state.tirage_en_cours=False
if "tirage_ok"      not in st.session_state:  st.session_state.tirage_ok=False

# ─────────────────────────── INTRO ─────────────────────────────────────────
if st.session_state.page=="intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")

    # composant invisible qui déclenche le plein-écran dès la 1re action
    components.v1.html("""
      <script>
        (function(){
           function fs(){
             const doc=document;
             if(!doc.fullscreenElement && doc.documentElement.requestFullscreen){
                doc.documentElement.requestFullscreen().catch(()=>{});
             }
           }
           document.addEventListener('click',fs,{once:true});
           document.addEventListener('keydown',fs,{once:true});
        })();
      </script>
    """, height=0, width=0)

    st.markdown("""
**Expérience standardisée pour un moniteur 60 Hz**  
(Le premier clic passe la page en plein-écran.)

**Principe** – Des mots sont présentés ≈ 17 ms puis masqués.  
**Tâche**    – Fixez la croix, appuyez sur **Espace** dès que le mot est reconnu,  
               tapez-le puis validez avec **Entrée**.

**Déroulement**  
1. Familiarisation : 2 mots  
2. Test principal  : 80 mots
""")

    # tirage automatique
    if not st.session_state.tirage_en_cours and not st.session_state.tirage_ok:
        st.session_state.tirage_en_cours=True; do_rerun()

    if st.session_state.tirage_en_cours and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            tirage_df=build_sheet()
            mots=tirage_df["ortho"].tolist(); random.shuffle(mots)
            st.session_state.tirage_df=tirage_df
            st.session_state.stimuli=mots
            st.session_state.tirage_en_cours=False
            st.session_state.tirage_ok=True
        st.success("Tirage terminé !")

    if st.session_state.tirage_ok:
        if st.button("Commencer la familiarisation"):
            st.session_state.page="fam"; do_rerun()

# ─────────────────────── FAMILIARISATION ────────────────────────────────
elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Fixez la croix, appuyez sur **Espace** quand le mot apparaît, "
                "tapez-le puis **Entrée**.")
    components.v1.html(
        experiment_html(PRACTICE_WORDS, with_download=False),
        height=650, scrolling=False
    )
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page="exp"; do_rerun()

# ─────────────────────── TEST PRINCIPAL ────────────────────────────────
elif st.session_state.page=="exp":
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu des statistiques du tirage"):
        st.dataframe(st.session_state.tirage_df.head())
    components.v1.html(
        experiment_html(st.session_state.stimuli, with_download=True),
        height=650, scrolling=False
    )
