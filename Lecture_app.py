# -*- coding: utf-8 -*-
"""
Expérience 3 – tirage des 80 mots dans un PROCESSUS séparé.
• Un seul fichier à déployer.
• Le processus de calcul écrit tirage.json ; l’IU le lit toutes les 1 s.
• L’utilisateur peut faire la familiarisation immédiatement.
"""

from __future__ import annotations
import json, multiprocessing as mp, random, sys, time
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit import components


##############################################################################
# 0.  CONFIG GLOBALE
##############################################################################
ROOT       = Path(__file__).parent
XLSX       = ROOT / "Lexique.xlsx"
JSON_FILE  = ROOT / "tirage.json"

PRACTICE   = ["PAIN", "EAU"]           # familiarisation
HTML_CYCLE = 350                       # ms
HTML_START = 14
HTML_STEP  = 14

# utilitaire « rerun » compatible versions
_rerun = st.rerun if hasattr(st, "rerun") else st.experimental_rerun

st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden;}</style>",
    unsafe_allow_html=True
)


##############################################################################
# 1.  PARAMÈTRES + OUTILS POUR LE CALCUL LOURD
##############################################################################
MEAN_FACTOR_OLDPLD = 0.40
MEAN_DELTA         = {"letters": 0.65, "phons": 0.65}
SD_MULTIPLIER      = {"letters": 2.0, "phons": 2.0,
                      "old20": 0.25, "pld20": 0.25, "freq": 1.8}
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]

def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace({" ":"", "\xa0":""}, regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce"
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:   # -1 LOW / +1 HIGH
    return -1 if "LOW" in tag else 1


##############################################################################
# 2.  FONCTION « HEAVY » (sera exécutée DANS UN PROCESSUS)
##############################################################################
def build_and_save_tirage(json_path: str) -> None:
    """
    Fonction CPU-lourde : génère la liste de 80 mots puis l’enregistre
    dans un JSON.  Aucune dépendance Streamlit ici.
    """
    XLSX = Path(__file__).with_name("Lexique.xlsx")
    if not XLSX.exists():
        raise FileNotFoundError("Lexique.xlsx manquant.")

    # ---- chargement Excel --------------------------------------------------
    xls   = pd.ExcelFile(XLSX)
    sheets= [s for s in xls.sheet_names if s.lower().startswith("feuil")]
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

    # ---- contraintes -------------------------------------------------------
    def masks(df:pd.DataFrame,s):
        return {"LOW_OLD": df.old20 < s["m_old20"]-s["sd_old20"],
                "HIGH_OLD":df.old20 > s["m_old20"]+s["sd_old20"],
                "LOW_PLD": df.pld20 < s["m_pld20"]-s["sd_pld20"],
                "HIGH_PLD":df.pld20 > s["m_pld20"]+s["sd_pld20"]}
    def sd_ok(sub,s,fqs):
        return (sub.nblettres.std(ddof=0)<=s["sd_nblettres"]*SD_MULTIPLIER["letters"] and
                sub.nbphons .std(ddof=0)<=s["sd_nbphons"]  *SD_MULTIPLIER["phons"]   and
                sub.old20   .std(ddof=0)<=s["sd_old20"]    *SD_MULTIPLIER["old20"]   and
                sub.pld20   .std(ddof=0)<=s["sd_pld20"]    *SD_MULTIPLIER["pld20"]   and
                all(sub[c].std(ddof=0)<=s[f"sd_{c}"]*SD_MULTIPLIER["freq"] for c in fqs))
    def mean_lp_ok(sub,s):
        return (abs(sub.nblettres.mean()-s["m_nblettres"])<=MEAN_DELTA["letters"]*s["sd_nblettres"] and
                abs(sub.nbphons.mean()  -s["m_nbphons"])  <=MEAN_DELTA["phons"]  *s["sd_nbphons"])
    def pick_five(tag,feuille,used,F):
        df,s,fqs = F[feuille]["df"],F[feuille]["stats"],F[feuille]["freq_cols"]
        pool=df.loc[masks(df,s)[tag] & ~df.ortho.isin(used)]
        if len(pool)<N_PER_FEUIL_TAG: return None
        for _ in range(MAX_TRY_TAG):
            samp=pool.sample(N_PER_FEUIL_TAG,random_state=rng.randint(0,1_000_000)).copy()
            if tag=="LOW_OLD" and samp.old20.mean()>=s["m_old20"]-MEAN_FACTOR_OLDPLD*s["sd_old20"]: continue
            if tag=="HIGH_OLD"and samp.old20.mean()<=s["m_old20"]+MEAN_FACTOR_OLDPLD*s["sd_old20"]: continue
            if tag=="LOW_PLD" and samp.pld20.mean()>=s["m_pld20"]-MEAN_FACTOR_OLDPLD*s["sd_pld20"]: continue
            if tag=="HIGH_PLD"and samp.pld20.mean()<=s["m_pld20"]+MEAN_FACTOR_OLDPLD*s["sd_pld20"]: continue
            if not mean_lp_ok(samp,s):continue
            if sd_ok(samp,s,fqs):
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
                sub=pick_five(tag,sh,taken[sh],feuilles)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(part,ignore_index=True)))
        if ok:
            df=pd.concat(groups,ignore_index=True)
            order=["ortho"]+NUM_BASE+feuilles["all_freq_cols"]+["source","group","old_cat","pld_cat"]
            df=df[order]
            df.to_json(json_path, orient="records", force_ascii=False)
            return
    raise RuntimeError("Tirage impossible.")


##############################################################################
# 3.  DÉMARRAGE DU PROCESSUS (une seule fois)
##############################################################################
if "proc" not in st.session_state:
    if not JSON_FILE.exists():                # rien à lire, on calcule
        ctx = mp.get_context("fork" if sys.platform != "win32" else "spawn")
        p   = ctx.Process(target=build_and_save_tirage, args=(str(JSON_FILE),))
        p.start()
        st.session_state.proc = p
    else:
        st.session_state.proc = None   # déjà prêt


##############################################################################
# 4.  LECTURE DU FICHIER (cache ttl = 1 s)
##############################################################################
@st.cache_data(ttl=1, show_spinner=False)
def read_tirage() -> pd.DataFrame|None:
    if not JSON_FILE.exists():
        return None
    try:
        return pd.read_json(JSON_FILE)
    except ValueError:         # fichier encore en cours d’écriture
        return None

tirage_df = read_tirage()
READY     = tirage_df is not None
ERROR     = False
if st.session_state.get("proc") and st.session_state.proc and not st.session_state.proc.is_alive():
    if not READY:
        ERROR = True                                      # le worker a échoué
        st.session_state.proc = None


##############################################################################
# 5.  TEMPLATE HTML / JS (chaine brute)
##############################################################################
HTML_TPL = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const WORDS=__WORDS__,C=__CYCLE__,S=__START__,STEP=__STEP__,DL=__DL__;
let i=0,r=[],scr=document.getElementById("scr"),ans=document.getElementById("ans");
function n(){if(i>=WORDS.length){e();return;}const w=WORDS[i],m="#".repeat(w.length);
let sh=S,hd=C-sh,tS,tH,ok=true,t0=performance.now();
(function l(){if(!ok)return;scr.textContent=w;
tS=setTimeout(()=>{if(!ok)return;scr.textContent=m;
tH=setTimeout(()=>{if(ok){sh+=STEP;hd=Math.max(0,C-sh);l();}},hd);},sh);})();
function sp(ev){if(ev.code==="Space"&&ok){ok=false;clearTimeout(tS);clearTimeout(tH);
const rt=Math.round(performance.now()-t0);window.removeEventListener("keydown",sp);
scr.textContent="";ans.style.display="block";ans.value="";ans.focus();
function en(e){if(e.key==="Enter"){e.preventDefault();
r.push({word:w,rt_ms:rt,response:ans.value.trim()});ans.removeEventListener("keydown",en);
ans.style.display="none";i++;n();}}ans.addEventListener("keydown",en);}}
window.addEventListener("keydown",sp);}function e(){
scr.style.fontSize="40px";scr.textContent=DL?"Merci !":"Fin de l’entraînement";
if(!DL)return;const csv=["word;rt_ms;response",
...r.map(o=>`${o.word};${o.rt_ms};${o.response}`)].join("\\n");
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";a.textContent="Télécharger les résultats";
a.style.fontSize="32px";a.style.marginTop="30px";document.body.appendChild(a);}n();
</script></body></html>"""
def html(words:list[str], dl=True):
    return (HTML_TPL.replace("__WORDS__", json.dumps(words))
                    .replace("__DL__", "true" if dl else "false")
                    .replace("__CYCLE__", str(HTML_CYCLE))
                    .replace("__START__", str(HTML_START))
                    .replace("__STEP__",  str(HTML_STEP)))


##############################################################################
# 6.  NAVIGATION STREAMLIT
##############################################################################
if "page" not in st.session_state:
    st.session_state.page = "intro"

# ---------------------------------------------------------------- intro --
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.write("Cette expérience comporte d’abord **une courte familiarisation** "
             "puis le test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        _rerun()

# ------------------------------------------------------------ familiarisation --
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.info("Appuyez sur **Espace** dès que vous voyez le mot, tapez-le puis Entrée.")

    if ERROR:
        st.error("Le tirage a échoué. Veuillez vérifier le fichier Excel.")
    elif READY:
        st.success("Stimuli du test prêts !")
    else:
        st.info("Recherche des stimuli du test… ⏳")

    components.v1.html(html(PRACTICE, dl=False), height=650, scrolling=False)

    st.divider()
    st.button("Passer au test principal",
              disabled=not READY or ERROR,
              on_click=lambda: (st.session_state.update({"page":"exp"}), _rerun()))

# -------------------------------------------------------------- test principal --
else:  # page exp
    if ERROR:
        st.error("Le tirage a échoué ; impossible de poursuivre."); st.stop()
    if not READY:
        st.warning("Les stimuli ne sont pas encore prêts…"); time.sleep(1); _rerun()

    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage"):
        st.dataframe(tirage_df.head())

    words = tirage_df.ortho.tolist()
    components.v1.html(html(words, dl=True), height=650, scrolling=False)
