# ─── exp3_frame.py ───────────────────────────────────────────────────────
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués  (version frame-accurate)
• Test de fréquence d’écran (rAF) + étiquette :
    27-33→30 Hz, 58-62→60, 73-77→75, 84-86→85,
    88-92→90, 98-102→100, 118-122→120, 141-146→144 Hz
• Boutons 60 Hz / 120 Hz / autre
• Croix de fixation 500 ms avant chaque mot
• Présentation synchronisée (requestAnimationFrame)
"""

from __future__ import annotations
import inspect, json, random
from pathlib import Path
from string import Template
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def do_rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    """
    <style>
    #MainMenu, header, footer{visibility:hidden;}
    button:disabled{opacity:.45!important;cursor:not-allowed!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────── constantes ────────────────────────────────
XLSX              = Path(__file__).with_name("Lexique.xlsx")
TAGS              = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG   = 5
MAX_TRY_TAG       = MAX_TRY_FULL = 1_000
rng               = random.Random()

NUM_BASE          = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS    = ["PAIN", "EAU"]

CYCLE_MS          = 350      # mot + masque
CROSS_MS          = 500      # croix 500 ms

MEAN_FACTOR_OLDPLD = .30
MEAN_DELTA         = dict(letters=.69, phons=.69)
SD_MULT            = dict(letters=2, phons=2, old20=.29, pld20=.29, freq=1.9)

# ────────────────────────── petits utilitaires ──────────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[ ,\xa0]", "", regex=True)
         .str.replace(",", ".", regex=False),
        errors="coerce",
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int: return -1 if "LOW" in tag else (1 if "HIGH" in tag else 0)

# ───────── mapping fréquence mesurée → étiquette lisible ────────────────
def label_hz(meas: float) -> int | None:
    mapping = [
        (30 , 27 , 33 ),
        (60 , 58 , 62 ),
        (75 , 73 , 77 ),
        (85 , 84 , 86 ),
        (90 , 88 , 92 ),
        (100, 98 , 102),
        (120, 118, 122),
        (144, 141, 146),
    ]
    for lbl, lo, hi in mapping:
        if lo <= meas <= hi:
            return lbl
    return None

# ────── 1. lecture de Lexique.xlsx ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_sheets() -> Dict[str, Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable"); st.stop()

    xls  = pd.ExcelFile(XLSX)
    shs  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(shs) != 4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4"); st.stop()

    feuilles, all_freq = {}, set()
    for sh in shs:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()
        freq_cols  = [c for c in df.columns if c.startswith("freq")]
        all_freq.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for c in NUM_BASE + freq_cols:
            df[c] = to_float(df[c])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df          = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()        for c in NUM_BASE}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in NUM_BASE + freq_cols}

        feuilles[sh] = dict(df=df, stats=stats, freq_cols=freq_cols)

    feuilles["all_freq_cols"] = sorted(all_freq)
    return feuilles

# ────── 2. tirage aléatoire des 80 mots (identique aux versions précédentes) ──
def masks(df, st_): return dict(
    LOW_OLD = df.old20 < st_["m_old20"],
    HIGH_OLD= df.old20 > st_["m_old20"],
    LOW_PLD = df.pld20 < st_["m_pld20"],
    HIGH_PLD= df.pld20 > st_["m_pld20"],
)

def sd_ok(sub, st_, fq):
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq)
    )

def mean_lp_ok(s, st_):
    return (
        abs(s.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
        abs(s.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"]
    )

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="HIGH_OLD" and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="LOW_PLD"  and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag=="HIGH_PLD" and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fq): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F  = load_sheets()
    ALL= F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        take={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            bloc=[]
            for sh in take:
                sub=pick_five(tag,sh,take[sh],F)
                if sub is None: ok=False; break
                bloc.append(sub); take[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            return df[["ortho"]+NUM_BASE+ALL+["source","group","old_cat","pld_cat"]]
    st.error("Impossible de générer la liste."); st.stop()

# ────── 3. gabarit HTML (croix, mot, masque – synchronisé) ───────────────
HTML_TPL = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
          display:flex;flex-direction:column;align-items:center;justify-content:center;
          font-family:'Courier New',monospace}
#scr{font-size:60px;color:#fff;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center;
     background:#fff;color:#000;border:none;padding:4px}
</style></head><body tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load",()=>document.body.focus());
const WORDS=$WORDS;
const START_F=$STARTF,STEP_F=$STEPF,CYCLE_F=$CYCLEF,CROSSF=$CROSSF;
let trial=0,results=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function nextTrial(){
 if(trial>=WORDS.length){fin();return;}
 const word=WORDS[trial],mask="#".repeat(word.length);let active=true;
 scr.textContent="+";let f=0;            // CROIX
 function crossLoop(){if(!active)return;
   if(++f>=CROSSF){startStimulus();}else{requestAnimationFrame(crossLoop);} }
 requestAnimationFrame(crossLoop);
 function startStimulus(){
   let showF=START_F,phase="show",g=0;const t0=performance.now();
   function stimLoop(){if(!active)return;
     if(phase==="show"){
       if(g===0) scr.textContent=word;
       if(++g>=showF){phase="mask";g=0;scr.textContent=mask;}
     }else{
       const hideF=Math.max(0,CYCLE_F-showF);
       if(++g>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F);phase="show";g=0;}
     }
     requestAnimationFrame(stimLoop);
   }requestAnimationFrame(stimLoop);
   function onSpace(e){
     if(e.code==="Space"&&active){
       active=false;window.removeEventListener("keydown",onSpace);
       const rt=Math.round(performance.now()-t0);
       scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
       ans.addEventListener("keydown",function onEnter(ev){
         if(ev.key==="Enter"){ev.preventDefault();
           results.push({word:word,rt_ms:rt,response:ans.value.trim()});
           ans.removeEventListener("keydown",onEnter);ans.style.display="none";
           trial++;nextTrial();}});}}
   window.addEventListener("keydown",onSpace);}
}
function fin(){scr.style.fontSize="40px";scr.textContent=$END_MSG;$DOWNLOAD}
$STARTER
</script></body></html>""")

def experiment_html(words: List[str], hz: int,
                    *, with_download=True, fullscreen=False) -> str:
    frame  = 1000 / hz
    cycle_f= round(CYCLE_MS / frame)
    cross_f= round(CROSS_MS / frame)
    scale  = hz // 60                # 1 pour 60 Hz ; 2 pour 120 Hz
    start_f= 1 * scale
    step_f = 1 * scale

    download_js = ""
    if with_download:
        download_js = r"""
const csv=["word;rt_ms;response",
           ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";
a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";
document.body.appendChild(a);""".replace("$", "$$")

    starter = "nextTrial();"
    if fullscreen:
        starter = r"""
scr.textContent="Appuyez sur la barre ESPACE pour commencer";
function first(e){if(e.code==="Space"){
  window.removeEventListener("keydown",first);
  document.documentElement.requestFullscreen?.();
  nextTrial();}}
window.addEventListener("keydown",first);"""

    return HTML_TPL.substitute(
        WORDS=json.dumps(list(words)),
        STARTF=start_f, STEPF=step_f, CYCLEF=cycle_f, CROSSF=cross_f,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download_js, STARTER=starter)

# ────── 4. composant de TEST de fréquence (affiche étiquette arrondie) ───
TEST_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
          display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:24px}
button{font-size:22px;padding:6px 26px;margin:4px}
</style></head><body>
<h2>Test de fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>
<script>
function label(h){
  if(h>=27 && h<=33)  return 30;
  if(h>=58 && h<=62)  return 60;
  if(h>=73 && h<=77)  return 75;
  if(h>=84 && h<=86)  return 85;
  if(h>=88 && h<=92)  return 90;
  if(h>=98 && h<=102) return 100;
  if(h>=118&& h<=122) return 120;
  if(h>=141&& h<=146) return 144;
  return h.toFixed(1);
}
function mesure(){
  const r=document.getElementById('res'),
        b=document.getElementById('go');
  b.disabled=true;r.textContent='Mesure…';
  let f=0,t0=performance.now();
  function loop(){
    f++;
    if(f<120){requestAnimationFrame(loop);}
    else{
      const hz=f*1000/(performance.now()-t0),
            lbl=label(hz);
      r.textContent='≈ '+lbl+' Hz';
      Streamlit.setComponentValue(hz.toFixed(1));   // valeur brute envoyée
      b.disabled=false;
    }}
  requestAnimationFrame(loop);
}
Streamlit.setComponentReady();
</script></body></html>"""

# ────── 5. état session ────────────────────────────────────────────────
defaults = dict(page="screen_test", tirage_ok=False, tirage_run=False,
                stimuli=[], tirage_df=pd.DataFrame(), exp_started=False,
                hz_val=None, hz_sel=None)
for k,v in defaults.items():
    st.session_state.setdefault(k,v)
p = st.session_state

def go(page: str): p.page = page; do_rerun()

# ────── 6. PAGES ────────────────────────────────────────────────────────
# 0. page test écran
if p.page == "screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")
    kw = dict(height=520, scrolling=False)
    if "key" in inspect.signature(components.html).parameters:
        kw["key"] = "hz"
    val = components.html(TEST_HTML, **kw)
    if isinstance(val, (int, float, str)):
        try: p.hz_val = float(val)
        except ValueError: pass
    if p.hz_val is not None:
        lbl = label_hz(p.hz_val)
        if lbl is None:
            st.write(f"Fréquence mesurée : **{p.hz_val:.1f} Hz**")
        else:
            st.write(f"Fréquence mesurée ≈ **{lbl} Hz**")
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Suivant 60 Hz ➜"):
            p.hz_sel = 60; go("intro")
    with c2:
        if st.button("Suivant 120 Hz ➜"):
            p.hz_sel = 120; go("intro")
    with c3:
        if st.button("Suivant autre Hz ➜"):
            go("incompatible")

# 1. page incompatible
elif p.page == "incompatible":
    st.error("Désolé, cette expérience nécessite un écran 60 Hz ou 120 Hz.")

# 2. introduction + tirage
elif p.page == "intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown(f"""
Écran sélectionné : **{p.hz_sel} Hz**

Chaque essai : croix centrale 500 ms → mot très bref → masque (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez le mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.  

Déroulement : 2 essais d’entraînement puis 80 essais de test.
""")

    if not p.tirage_run and not p.tirage_ok:
        p.tirage_run = True; do_rerun()
    elif p.tirage_run and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet(); mots = df["ortho"].tolist(); random.shuffle(mots)
            p.tirage_df, p.stimuli = df, mots
            p.tirage_ok, p.tirage_run = True, False
        st.success("Tirage terminé !")
    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")

# 3. familiarisation
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Croix 500 ms → mot → masque. Appuyer sur **ESPACE** dès que possible.")
    components.html(
        experiment_html(PRACTICE_WORDS, p.hz_sel, with_download=False, fullscreen=False),
        height=650, scrolling=False
    )
    st.divider()
    if st.button("Passer au test principal"):
        p.page, p.exp_started = "exp", False; do_rerun()

# 4. test principal
elif p.page == "exp":
    if not p.exp_started:
        st.header("Test principal : 80 mots")
        with st.expander("Aperçu (5 lignes) du tirage"):
            st.dataframe(p.tirage_df.head())
        if st.button("Commencer le test (plein écran)"):
            p.exp_started = True; do_rerun()
    else:
        components.html(
            experiment_html(p.stimuli, p.hz_sel, with_download=True, fullscreen=True),
            height=700, scrolling=False
        )

else:
    st.stop()
