# -*- coding: utf-8 -*-
"""
Expérience 3 — calcul des 80 mots dans un thread doté du ScriptRunContext.
Compatible Streamlit >= 1.18 (add_script_run_ctx) et >= 1.32 (st.rerun).
"""

from __future__ import annotations
import random, threading
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx


# ───────────────────────── configuration Streamlit ──────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("<style>#MainMenu,header,footer{visibility:hidden;}</style>",
            unsafe_allow_html=True)
rerun = st.rerun if hasattr(st, "rerun") else st.experimental_rerun


# ───────────────────────── fichiers & constantes ─────────────────────────
XLSX       = Path(__file__).with_name("Lexique.xlsx")
PRACTICE   = ["PAIN", "EAU"]

MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": .65, "phons": .65}
SD_MULTIPLIER      = {"letters": 2.0, "phons": 2.0,
                      "old20": 0.25, "pld20": 0.25, "freq": 1.8}
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
rng             = random.Random()


# ───────────────────────── fonction de tirage (sans Streamlit) ───────────
def build_sheet() -> pd.DataFrame:
    def to_float(s): return pd.to_numeric(
        s.astype(str).str.replace({" ":"","\xa0":""},regex=False)
         .str.replace(",",".",regex=False), errors="coerce")

    if not XLSX.exists():
        raise FileNotFoundError("Lexique.xlsx manquant.")
    xls = pd.ExcelFile(XLSX)
    sheets=[s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4:
        raise RuntimeError("Il faut 4 feuilles Feuil1…Feuil4.")

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
    def cat_code(tag:str)->int: return -1 if "LOW" in tag else 1
    def sd_ok(sub,s,fq):
        return (sub.nblettres.std(ddof=0)<=s["sd_nblettres"]*SD_MULTIPLIER["letters"] and
                sub.nbphons .std(ddof=0)<=s["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
                sub.old20   .std(ddof=0)<=s["sd_old20"]    *SD_MULTIPLIER["old20"]   and
                sub.pld20   .std(ddof=0)<=s["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
                all(sub[c].std(ddof=0)<=s[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fq))
    def mean_ok(sub,s):
        return (abs(sub.nblettres.mean()-s["m_nblettres"])<=MEAN_DELTA["letters"]*s["sd_nblettres"] and
                abs(sub.nbphons.mean() -s["m_nbphons"])   <=MEAN_DELTA["phons"]  *s["sd_nbphons"])
    def pick(tag,feuille,used,F):
        df,s,fq=F[feuille]["df"],F[feuille]["stats"],F[feuille]["freq_cols"]
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
                samp["source"]=feuille; samp["group"]=tag
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
            groups.append(pd.concat(part,ignore_index=True).sample(frac=1,random_state=rng.randint(0,1_000_000)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            order=["ortho"]+NUM_BASE+feuilles["all_freq_cols"]+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Tirage impossible")

# ───────────── thread : calcule puis écrit dans st.session_state ─────────
def start_thread_once():
    def worker():
        df = build_sheet()       # peut prendre plusieurs secondes
        st.session_state.tirage_df = df
        st.session_state.tirage_ready = True
        rerun()                  # relance la page UNE fois, quand c’est fini

    if "tirage_ready" not in st.session_state:
        st.session_state.tirage_ready = False
        th = threading.Thread(target=worker, daemon=True)
        # on attache le contexte pour pouvoir manipuler session_state + rerun
        add_script_run_ctx(th, get_script_run_ctx())
        th.start()

from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
start_thread_once()

# ───────────── petit HTML/JS pour l’expérience ───────────────────────────
HTML=r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const W=__WORDS__,DL=__DL__;let i=0,r=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function n(){if(i>=W.length){f();return;}const w=W[i],m="#".repeat(w.length);let sh=14,hd=336,tS,tH,ok=true,t0=performance.now();
(function l(){if(!ok)return;scr.textContent=w;tS=setTimeout(()=>{if(!ok)return;scr.textContent=m;
tH=setTimeout(()=>{if(ok){sh+=14;hd=Math.max(0,350-sh);l();}},hd);},sh);})();
function sp(e){if(e.code==="Space"&&ok){ok=false;clearTimeout(tS);clearTimeout(tH);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",sp);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function en(ev){if(ev.key==="Enter"){ev.preventDefault();
r.push({word:w,rt_ms:rt,response:ans.value.trim()});ans.removeEventListener("keydown",en);
ans.style.display="none";i++;n();}}ans.addEventListener("keydown",en);}}
window.addEventListener("keydown",sp);}function f(){scr.style.fontSize="40px";
scr.textContent=DL?"Merci !":"Fin entraînement";if(!DL)return;
const csv=["word;rt_ms;response",...r.map(o=>`${o.word};${o.rt_ms};${o.response}`)].join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";document.body.appendChild(a);}n();
</script></body></html>"""
def html(words,dl=True):return HTML.replace("__WORDS__",json.dumps(words)).replace("__DL__", "true" if dl else "false")

# ───────────── navigation ────────────────────────────────────────────────
if "page" not in st.session_state: st.session_state.page="intro"

if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.write("Familiarisation puis test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page="fam"; rerun()

elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    if st.session_state.tirage_ready: st.success("Stimuli prêts ✅")
    else:                             st.info("Recherche des stimuli en arrière-plan…")
    components.v1.html(html(PRACTICE,dl=False),height=650,scrolling=False)
    st.divider()
    st.button("Passer au test principal",
              disabled=not st.session_state.tirage_ready,
              on_click=lambda:(st.session_state.update({"page":"exp"}),rerun()))

else:  # test principal
    if not st.session_state.tirage_ready:
        st.warning("Stimuli pas prêts…"); st.stop()
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage"):
        st.dataframe(st.session_state.tirage_df.head())
    components.v1.html(html(st.session_state.tirage_df.ortho.tolist(),dl=True),
                       height=650,scrolling=False)
