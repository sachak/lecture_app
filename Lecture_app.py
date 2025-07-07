# exp3.py  ────────────────────────────────────────────────────────────────
from __future__ import annotations
import json, random, threading, time, os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ─────────────  dossiers / fichiers  ─────────────────────────────────────
ROOT       = Path(__file__).parent
XLSX       = ROOT / "Lexique.xlsx"
JSON_FILE  = ROOT / "tirage.json"          # résul­tat écrit par le thread

# ─────────────  paramètres tirage  (identiques à vos specs)  ────────────
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": .65, "phons": .65}
SD_MULTIPLIER      = {"letters":2.0,"phons":2.0,"old20":0.25,"pld20":0.25,"freq":1.8}
N_PER_FEUIL_TAG    = 5
TAGS               = ("LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD")
MAX_TRY_TAG        = 1_000
MAX_TRY_FULL       = 1_000
NUM_BASE           = ["nblettres","nbphons","old20","pld20"]
rng                = random.Random()

PRACTICE = ["PAIN","EAU"]                  # phase d’entraînement

# ─────────────  config Streamlit  ────────────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden;}</style>",
            unsafe_allow_html=True)
_rerun = st.rerun if hasattr(st,"rerun") else st.experimental_rerun


# ═════════════════════════════ 1.  FONCTION LOURDE (aucun Streamlit) ═════════════
def build_sheet() -> pd.DataFrame:
    """Génère la liste des 80 mots suivant vos contraintes."""
    if not XLSX.exists():
        raise FileNotFoundError("Lexique.xlsx manquant")

    xls = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4:
        raise RuntimeError("Il faut 4 feuilles Feuil1 … Feuil4")

    def to_float(s): return pd.to_numeric(
        s.astype(str).str.replace({" ":"","\xa0":""},regex=False).str.replace(",",".",regex=False),
        errors="coerce")

    feuilles, all_fcols = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns=df.columns.str.strip().str.lower()
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

    def masks(df,s):return {"LOW_OLD":df.old20<s["m_old20"]-s["sd_old20"],
                            "HIGH_OLD":df.old20>s["m_old20"]+s["sd_old20"],
                            "LOW_PLD":df.pld20<s["m_pld20"]-s["sd_pld20"],
                            "HIGH_PLD":df.pld20>s["m_pld20"]+s["sd_pld20"]}
    def sd_ok(sub,s,fq):
        return (sub.nblettres.std(ddof=0)<=s["sd_nblettres"]*SD_MULTIPLIER["letters"] and
                sub.nbphons .std(ddof=0)<=s["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
                sub.old20   .std(ddof=0)<=s["sd_old20"]    *SD_MULTIPLIER["old20"]   and
                sub.pld20   .std(ddof=0)<=s["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
                all(sub[c].std(ddof=0)<=s[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fq))
    def mean_ok(sub,s):
        return (abs(sub.nblettres.mean()-s["m_nblettres"])<=MEAN_DELTA["letters"]*s["sd_nblettres"] and
                abs(sub.nbphons.mean() -s["m_nbphons"])   <=MEAN_DELTA["phons"]  *s["sd_nbphons"])
    def pick(tag,feu,used,F):
        df,s,fq=F[feu]["df"],F[feu]["stats"],F[feu]["freq_cols"]
        pool=df.loc[masks(df,s)[tag] & ~df.ortho.isin(used)]
        if len(pool)<N_PER_FEUIL_TAG:return None
        for _ in range(MAX_TRY_TAG):
            samp=pool.sample(N_PER_FEUIL_TAG,random_state=rng.randint(0,1_000_000)).copy()
            if tag=="LOW_OLD" and samp.old20.mean()>=s["m_old20"]-MEAN_FACTOR_OLDPLD*s["sd_old20"]:continue
            if tag=="HIGH_OLD"and samp.old20.mean()<=s["m_old20"]+MEAN_FACTOR_OLDPLD*s["sd_old20"]:continue
            if tag=="LOW_PLD" and samp.pld20.mean()>=s["m_pld20"]-MEAN_FACTOR_OLDPLD*s["sd_pld20"]:continue
            if tag=="HIGH_PLD"and samp.pld20.mean()<=s["m_pld20"]+MEAN_FACTOR_OLDPLD*s["sd_pld20"]:continue
            if not mean_ok(samp,s):continue
            if sd_ok(samp,s,fq):
                samp["source"]=feu;samp["group"]=tag
                samp["old_cat"]=-1 if "LOW" in tag and "OLD" in tag else 1 if "HIGH" in tag and "OLD" in tag else 0
                samp["pld_cat"]=-1 if "LOW" in tag and "PLD" in tag else 1 if "HIGH" in tag and "PLD" in tag else 0
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

def thread_job():
    try:
        df=build_sheet()
        tmp=JSON_FILE.with_suffix(".tmp")
        df.to_json(tmp,orient="records",force_ascii=False)
        tmp.replace(JSON_FILE)          # écriture atomique
    except Exception as e:
        JSON_FILE.write_text(json.dumps({"error":str(e)},ensure_ascii=False))

# démarre le thread une seule fois
if not JSON_FILE.exists() and "bg_thread" not in st.session_state:
    th=threading.Thread(target=thread_job,daemon=True)
    th.start()
    st.session_state.bg_thread=th

# ───────────── 2.  fragment : lit le JSON toutes les 0,5 s  ──────────────
@st.experimental_fragment(ttl=0.5)
def poll_json() -> tuple[bool,bool,pd.DataFrame|str|None]:
    if not JSON_FILE.exists(): return False,False,None
    try:
        data=pd.read_json(JSON_FILE)
        return True,False,data
    except ValueError:
        return False,False,None
    except Exception:
        try:
            err=json.loads(JSON_FILE.read_text())["error"]
        except Exception as e:
            err=str(e)
        return False,True,err

READY, ERROR, DATA = poll_json()

# ───────────── 3.  template HTML minimal ────────────────────────────────
HTML_TPL=r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const W=__WORDS__,C=350,S=14,STEP=14,DL=__DL__;
let i=0,r=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function n(){if(i>=W.length){f();return;}const w=W[i],m="#".repeat(w.length);
let sh=S,hd=C-sh,tS,tH,ok=true,t0=performance.now();
(function l(){if(!ok)return;scr.textContent=w;tS=setTimeout(()=>{if(!ok)return;scr.textContent=m;
tH=setTimeout(()=>{if(ok){sh+=STEP;hd=Math.max(0,C-sh);l();}},hd);},sh);})();
function sp(e){if(e.code==="Space"&&ok){ok=false;clearTimeout(tS);clearTimeout(tH);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",sp);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function en(ev){if(ev.key==="Enter"){ev.preventDefault();
r.push({word:w,rt_ms:rt,response:ans.value.trim()});ans.removeEventListener("keydown",en);
ans.style.display="none";i++;n();}}ans.addEventListener("keydown",en);}}
window.addEventListener("keydown",sp);}function f(){scr.style.fontSize="40px";
scr.textContent=DL?"Merci !":"Fin de l’entraînement";if(!DL)return;
const csv=["word;rt_ms;response",...r.map(o=>`${o.word};${o.rt_ms};${o.response}`)].join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";document.body.appendChild(a);}n();
</script></body></html>"""
def html(words:list[str], dl=True):return (HTML_TPL
    .replace("__WORDS__",json.dumps(words))
    .replace("__DL__",   "true" if dl else "false"))

# ───────────── 4.  navigation Streamlit  ────────────────────────────────
if "page" not in st.session_state: st.session_state.page="intro"

if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.write("Familiarisation → test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page="fam"; _rerun()

elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    if ERROR:  st.error(DATA)
    elif READY:st.success("Stimuli prêts !")
    else:      st.info("Recherche des stimuli…")
    components.v1.html(html(PRACTICE,dl=False),height=650,scrolling=False)
    st.divider()
    st.button("Passer au test principal",disabled=not READY,
              on_click=lambda:(st.session_state.update({"page":"exp"}),_rerun()))

else:  # page exp
    if ERROR: st.error(DATA); st.stop()
    if not READY: st.warning("Stimuli pas prêts…"); time.sleep(0.5); _rerun()
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu"):
        st.dataframe(DATA.head())
    components.v1.html(html(DATA.ortho.tolist(),dl=True),height=650,scrolling=False)
