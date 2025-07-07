from __future__ import annotations
import json, random, concurrent.futures
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ────────── Config visuel ────────────────────────────────────────────── #
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
.css-1d391kg{display:none;}
</style>""", unsafe_allow_html=True)

# ────────── Paramètres ───────────────────────────────────────────────── #
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER      = {"letters": 2.0,"phons": 2.0,
                      "old20": 0.25,"pld20": 0.25,"freq": 1.8}

XLSX            = Path(__file__).with_name("Lexique.xlsx")
TAGS            = ("LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD")
N_PER_FEUIL_TAG = 5
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE        = ["nblettres","nbphons","old20","pld20"]
PRACTICE_WORDS  = ["PAIN","EAU"]

# ────────── Fonctions utilitaires ────────────────────────────────────── #
def to_float(s: pd.Series)->pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(" ","").str.replace("\xa0","").str.replace(",","."),
                         errors="coerce")
def shuffled(df): return df.sample(frac=1,
                                   random_state=rng.randint(0,1_000_000)).reset_index(drop=True)
def cat_code(tag): return -1 if "LOW" in tag else 1

# ────────── Chargement Excel (cache) ─────────────────────────────────── #
@st.cache_data(show_spinner="Chargement du classeur Excel…")
def load_sheets():
    if not XLSX.exists(): st.error(f"{XLSX.name} absent."); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheets=[s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets)!=4: st.error("Il faut 4 feuilles Feuil1…Feuil4."); st.stop()

    feuilles,all_freq={},set()
    for sh in sheets:
        df=xls.parse(sh); df.columns=df.columns.str.strip().str.lower()
        freq=[c for c in df.columns if c.startswith("freq")]; all_freq.update(freq)
        need=["ortho","old20","pld20","nblettres","nbphons"]+freq
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()
        for c in NUM_BASE+freq: df[c]=to_float(df[c])
        df["ortho"]=df["ortho"].astype(str).str.upper()
        df=df.dropna(subset=need).reset_index(drop=True)

        stats={f"m_{c}":df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats|={f"sd_{c}":df[c].std(ddof=0) for c in ("old20","pld20","nblettres","nbphons")+tuple(freq)}
        feuilles[sh]={"df":df,"stats":stats,"freq_cols":freq}
    feuilles["all_freq_cols"]=sorted(all_freq)
    return feuilles

# ────────── Algorithme de tirage (aucun appel Streamlit) ─────────────── #
def masks(df,st_):
    return {"LOW_OLD":df.old20<st_["m_old20"]-st_["sd_old20"],
            "HIGH_OLD":df.old20>st_["m_old20"]+st_["sd_old20"],
            "LOW_PLD":df.pld20<st_["m_pld20"]-st_["sd_pld20"],
            "HIGH_PLD":df.pld20>st_["m_pld20"]+st_["sd_pld20"]}
def sd_ok(sub,st_,fq):
    return (sub.nblettres.std(ddof=0)<=st_["sd_nblettres"]*SD_MULTIPLIER["letters"] and
            sub.nbphons.std(ddof=0)<=st_["sd_nbphons"]*SD_MULTIPLIER["phons"] and
            sub.old20.std(ddof=0)<=st_["sd_old20"]*SD_MULTIPLIER["old20"] and
            sub.pld20.std(ddof=0)<=st_["sd_pld20"]*SD_MULTIPLIER["pld20"] and
            all(sub[c].std(ddof=0)<=st_[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fq))
def mean_lp_ok(sub,st_):
    return (abs(sub.nblettres.mean()-st_["m_nblettres"])<=MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()-st_["m_nbphons"])  <=MEAN_DELTA["phons"]  *st_["sd_nbphons"])
def pick_five(tag,feuille,used,F):
    df,st_,fq=F[feuille]["df"],F[feuille]["stats"],F[feuille]["freq_cols"]
    pool=df.loc[masks(df,st_)[tag] & ~df.ortho.isin(used)]
    if len(pool)<N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        sp=pool.sample(N_PER_FEUIL_TAG,random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD" and sp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="HIGH_OLD"and sp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]: continue
        if tag=="LOW_PLD" and sp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if tag=="HIGH_PLD"and sp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]: continue
        if not mean_lp_ok(sp,st_) or not sd_ok(sp,st_,fq): continue
        sp["source"],sp["group"]=feuille,tag
        sp["old_cat"]=cat_code(tag) if "OLD" in tag else 0
        sp["pld_cat"]=cat_code(tag) if "PLD" in tag else 0
        return sp
    return None
def build_sheet(F):
    cols=F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken={sh:set() for sh in F if sh!="all_freq_cols"}
        groups,ok=[],True
        for tag in TAGS:
            part=[]
            for sh in taken:
                sub=pick_five(tag,sh,taken[sh],F)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(part,ignore_index=True)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            order=["ortho"]+NUM_BASE+cols+["source","group","old_cat","pld_cat"]
            return df[order]
    raise RuntimeError("Impossible de générer la liste.")

# ────────── Executor & future ─────────────────────────────────────────── #
if "executor" not in st.session_state:
    st.session_state.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def launch_future():
    if "future" in st.session_state: return
    st.session_state.sheets = load_sheets()
    st.session_state.future = st.session_state.executor.submit(build_sheet,
                                                               st.session_state.sheets)
def future_ready():
    return "future" in st.session_state and st.session_state.future.done()
def collect():
    df=st.session_state.future.result()
    words=df["ortho"].tolist(); random.shuffle(words)
    st.session_state.tirage_df=df; st.session_state.stimuli=words
    del st.session_state.future

# ────────── HTML (keyup) ──────────────────────────────────────────────── #
def html(words,dl,start_ms,cycle=350,step=14):
    fin="Merci !" if dl else "Fin de l’entraînement"
    download=""
    if dl:
        download="""const csv=["word;rt_ms;response",
          ...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\\n");
          const a=document.createElement('a');
          a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
          a.download='results.csv';a.textContent='Télécharger les résultats';
          a.style.fontSize='32px';a.style.marginTop='30px';document.body.appendChild(a);"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>
html,body{{height:100%;margin:0;display:flex;flex-direction:column;align-items:center;justify-content:center;
font-family:'Courier New',monospace;}}#scr{{font-size:60px;user-select:none;}}
#ans{{display:none;font-size:48px;width:60%;text-align:center;}}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.body.focus());
const WORDS={json.dumps(words)},CYCLE={cycle},START={start_ms},STEP={step};
let i=0,res=[],scr=document.getElementById('scr'),ans=document.getElementById('ans');
function next(){{if(i>=WORDS.length){{fin();return;}}
 const w=WORDS[i],mask='#'.repeat(w.length);let sd=START,hd=CYCLE-sd,ts,th,t0=performance.now(),act=!0;
 (function loop(){{if(!act)return;scr.textContent=w;
  ts=setTimeout(()=>{{if(!act)return;scr.textContent=mask;
    th=setTimeout(()=>{{if(act){{sd+=STEP;hd=Math.max(0,CYCLE-sd);loop();}}}},hd);
  }},sd);}})();
 window.addEventListener('keydown',function sp(e){{if(e.code==='Space'&&act){{act=!1;
   clearTimeout(ts);clearTimeout(th);const rt=Math.round(performance.now()-t0);
   window.removeEventListener('keydown',sp);scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
   ans.addEventListener('keyup',function en(ev){{if(ev.key==='Enter'){{ev.preventDefault();
     res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
     ans.removeEventListener('keyup',en);ans.style.display='none';i++;next();}}}});
 }}}},{{once:!0}});}}
function fin(){{scr.style.fontSize='40px';scr.textContent='{fin}';{download}}}
next();
</script></body></html>"""

# ────────── Navigation ────────────────────────────────────────────────── #
if "page" not in st.session_state: st.session_state.page="intro"
launch_future()

# rafraîchissement JS uniquement sur la page 'fam' tant que tirage pas prêt
if st.session_state.page=="fam" and not future_ready():
    st.markdown('<script>setTimeout(()=>window.location.reload(),500);</script>',
                unsafe_allow_html=True)

if future_ready() and "tirage_df" not in st.session_state:
    collect()

# INTRO ------------------------------------------------------------------ #
if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Vous ferez d’abord **une très courte familiarisation** (2 mots), "
                "puis le test principal (80 mots).")
    if st.button("Commencer la familiarisation"):
        st.session_state.page="fam"; st.experimental_rerun()

# FAMILIARISATION -------------------------------------------------------- #
elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    components.v1.html(html(PRACTICE_WORDS,False,250),height=650,scrolling=False)
    st.divider()
    ready="tirage_df" in st.session_state
    st.button("Passer au test principal",disabled=not ready,
        on_click=lambda:(setattr(st.session_state,"page","exp"), st.experimental_rerun()) )

# TEST PRINCIPAL --------------------------------------------------------- #
elif st.session_state.page=="exp":
    if "tirage_df" not in st.session_state:
        st.warning("Les mots ne sont pas encore prêts…"); st.stop()
    df,stimuli=st.session_state.tirage_df, st.session_state.stimuli
    st.header("Test principal (80 mots)")
    with st.expander("Statistiques du tirage (aperçu)"): st.dataframe(df.head())
    components.v1.html(html(stimuli,True,14),height=650,scrolling=False)
