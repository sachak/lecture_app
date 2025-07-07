# exp3_app.py  ─────────────────────────────────────────────────────────────
from __future__ import annotations
import json, random, threading, time
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit import components

# ────────────────────── fichiers et chemins ──────────────────────────────
ROOT      = Path(__file__).parent
XLSX      = ROOT / "Lexique.xlsx"
JSON_FILE = ROOT / "tirage.json"      # résultat produit par le thread

# ────────────────────── paramètres tirage (mêmes qu’avant) ───────────────
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA   = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER = {"letters": 2.0, "phons": 2.0,
                 "old20": 0.25, "pld20": 0.25, "freq": 1.8}
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()
NUM_BASE        = ["nblettres","nbphons","old20","pld20"]
PRACTICE_WORDS  = ["PAIN","EAU"]

# ────────────────────── Streamlit setup ───────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden;}</style>",
            unsafe_allow_html=True)
_rerun = st.rerun if hasattr(st,"rerun") else st.experimental_rerun

# ────────────────────── utilitaires « lourds » (aucun Streamlit) ─────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace({" ":"", "\xa0":""}, regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0,1_000_000)).reset_index(drop=True)

def cat_code(tag:str)->int: return -1 if "LOW" in tag else 1

def build_sheet() -> pd.DataFrame:
    if not XLSX.exists():
        raise FileNotFoundError("Lexique.xlsx manquant.")
    xls=pd.ExcelFile(XLSX)
    sheets=[s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4:
        raise RuntimeError("Il faut 4 feuilles Feuil1…Feuil4.")
    feuilles,all_f=set(),set(); feuilles={}
    all_fcols=set()
    for sh in sheets:
        df=xls.parse(sh); df.columns=df.columns.str.strip().str.lower()
        fcols=[c for c in df.columns if c.startswith("freq")]
        all_fcols.update(fcols)
        need=["ortho","old20","pld20","nblettres","nbphons"]+fcols
        if any(c not in df.columns for c in need):
            raise RuntimeError(f"Colonnes manquantes dans {sh}")
        for col in NUM_BASE+fcols: df[col]=to_float(df[col])
        df["ortho"]=df["ortho"].astype(str).str.upper()
        df=df.dropna(subset=need).reset_index(drop=True)
        stats={f"m_{c}":df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats|={f"sd_{c}":df[c].std(ddof=0) for c in
                ("old20","pld20","nblettres","nbphons")+tuple(fcols)}
        feuilles[sh]={"df":df,"stats":stats,"freq_cols":fcols}
    feuilles["all_freq_cols"]=sorted(all_fcols)

    def masks(df,s):return{"LOW_OLD":df.old20<s["m_old20"]-s["sd_old20"],
                           "HIGH_OLD":df.old20>s["m_old20"]+s["sd_old20"],
                           "LOW_PLD":df.pld20<s["m_pld20"]-s["sd_pld20"],
                           "HIGH_PLD":df.pld20>s["m_pld20"]+s["sd_pld20"]}
    def sd_ok(sub,s,fq):return(
        sub.nblettres.std(ddof=0)<=s["sd_nblettres"]*SD_MULTIPLIER["letters"] and
        sub.nbphons .std(ddof=0)<=s["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
        sub.old20   .std(ddof=0)<=s["sd_old20"]    *SD_MULTIPLIER["old20"]   and
        sub.pld20   .std(ddof=0)<=s["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
        all(sub[c].std(ddof=0)<=s[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fq))
    def mean_lp_ok(sub,s):return(
        abs(sub.nblettres.mean()-s["m_nblettres"])<=MEAN_DELTA["letters"]*s["sd_nblettres"] and
        abs(sub.nbphons.mean() -s["m_nbphons"])   <=MEAN_DELTA["phons"]  *s["sd_nbphons"])
    def pick(tag,feu,used,F):
        df,s,fq = F[feu]["df"],F[feu]["stats"],F[feu]["freq_cols"]
        pool=df.loc[masks(df,s)[tag] & ~df.ortho.isin(used)]
        if len(pool)<N_PER_FEUIL_TAG:return None
        for _ in range(MAX_TRY_TAG):
            samp=pool.sample(N_PER_FEUIL_TAG,random_state=rng.randint(0,1_000_000)).copy()
            if tag=="LOW_OLD" and samp.old20.mean()>=s["m_old20"]-MEAN_FACTOR_OLDPLD*s["sd_old20"]:continue
            if tag=="HIGH_OLD"and samp.old20.mean()<=s["m_old20"]+MEAN_FACTOR_OLDPLD*s["sd_old20"]:continue
            if tag=="LOW_PLD" and samp.pld20.mean()>=s["m_pld20"]-MEAN_FACTOR_OLDPLD*s["sd_pld20"]:continue
            if tag=="HIGH_PLD"and samp.pld20.mean()<=s["m_pld20"]+MEAN_FACTOR_OLDPLD*s["sd_pld20"]:continue
            if not mean_lp_ok(samp,s):continue
            if sd_ok(samp,s,fq):
                samp["source"]=feu;samp["group"]=tag
                samp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
                samp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
                return samp
        return None

    for _ in range(MAX_TRY_FULL):
        taken={sh:set() for sh in feuilles if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            part=[]
            for sh in taken:
                sub=pick(tag,sh,taken[sh],feuilles)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(part,ignore_index=True)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            order=["ortho"]+NUM_BASE+feuilles["all_freq_cols"]+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Tirage impossible.")

def worker():
    try:
        df=build_sheet()
        tmp=JSON_FILE.with_suffix(".tmp")
        df.to_json(tmp, orient="records", force_ascii=False)
        tmp.replace(JSON_FILE)           # écriture atomique
    except Exception as e:
        JSON_FILE.write_text(json.dumps({"error":str(e)}, ensure_ascii=False))

# ────────────────────── lance le thread une seule fois ───────────────────
if not JSON_FILE.exists() and "thread" not in st.session_state:
    t=threading.Thread(target=worker, daemon=True)
    t.start()
    st.session_state.thread=t

# ────────────────────── fonction de lecture (polling 1 s) ────────────────
@st.cache_data(ttl=1, show_spinner=False)
def read_json() -> tuple[bool,str|pd.DataFrame]:
    if not JSON_FILE.exists(): return False,""
    try:
        data=pd.read_json(JSON_FILE)
        if isinstance(data, pd.DataFrame): return True,data
    except ValueError:            # fichier incomplet
        return False,""
    # cas d’erreur écrite par worker
    try:
        err=json.loads(JSON_FILE.read_text())
        return False,err.get("error","Erreur inconnue.")
    except Exception:
        return False,"Erreur inconnue."
ready_or_error, payload = read_json()
READY = isinstance(payload, pd.DataFrame)
ERROR = not READY and isinstance(payload, str) and payload!=""

# ────────────────────── mini page HTML/JS ────────────────────────────────
HTML_TPL=r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const W=__WORDS__,C=350,S=14,STEP=14,DL=__DL__;let i=0,r=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function n(){if(i>=W.length){e();return;}const w=W[i],m="#".repeat(w.length);let sh=S,hd=C-sh,tS,tH,ok=true,t0=performance.now();
(function l(){if(!ok)return;scr.textContent=w;tS=setTimeout(()=>{if(!ok)return;scr.textContent=m;
tH=setTimeout(()=>{if(ok){sh+=STEP;hd=Math.max(0,C-sh);l();}},hd);},sh);})();
function sp(ev){if(ev.code==="Space"&&ok){ok=false;clearTimeout(tS);clearTimeout(tH);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",sp);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function en(e){if(e.key==="Enter"){e.preventDefault();
r.push({word:w,rt_ms:rt,response:ans.value.trim()});ans.removeEventListener("keydown",en);
ans.style.display="none";i++;n();}}ans.addEventListener("keydown",en);}}
window.addEventListener("keydown",sp);}function e(){scr.style.fontSize="40px";
scr.textContent=DL?"Merci !":"Fin de l’entraînement";if(!DL)return;
const csv=["word;rt_ms;response",...r.map(o=>`${o.word};${o.rt_ms};${o.response}`)].join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";a.style.fontSize="32px";
a.style.marginTop="30px";document.body.appendChild(a);}n();</script></body></html>"""
def html(words,dl=True):return HTML_TPL.replace("__WORDS__",json.dumps(words)).replace("__DL__", "true" if dl else "false")

# ────────────────────── navigation Streamlit ─────────────────────────────
if "page" not in st.session_state: st.session_state.page="intro"

if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.write("Familiarisation → test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page="fam"; _rerun()

elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    if READY: st.success("Stimuli du test prêts !")
    elif ERROR: st.error(payload)
    else: st.info("Recherche des stimuli en arrière-plan…")
    components.v1.html(html(PRACTICE_WORDS,dl=False),height=650,scrolling=False)
    st.divider()
    st.button("Passer au test principal",
              disabled=not READY,
              on_click=lambda:(st.session_state.update({"page":"exp"}),_rerun()))

else:  # test principal
    if ERROR: st.error(payload); st.stop()
    if not READY: st.warning("Stimuli pas encore prêts…"); time.sleep(1); _rerun()
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage"):
        st.dataframe(payload.head())
    components.v1.html(html(payload.ortho.tolist(),dl=True),height=650,scrolling=False)
