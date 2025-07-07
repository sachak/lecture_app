# -*- coding: utf-8 -*-
"""
Interface Streamlit : lance compute_tirage.py (sous-processus) si besoin,
relit tirage.json toutes les 1 s via st.cache_data(ttl=1).
L’utilisateur peut commencer la familiarisation immédiatement.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit import components

# ─── chemins & fichiers ───────────────────────────────────────────
ROOT      = Path(__file__).parent
JSON_FILE = ROOT / "tirage.json"
WORKER    = ROOT / "compute_tirage.py"

# ─── rerun compatible versions ───────────────────────────────────
_rerun = st.rerun if hasattr(st,"rerun") else st.experimental_rerun

# ─── mini template HTML/JS ───────────────────────────────────────
HTML_TPL = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
const WORDS=__WORDS__,C=350,S=14,STEP=14,DL=__DL__;
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
    return HTML_TPL.replace("__WORDS__", json.dumps(words)).replace("__DL__", "true" if dl else "false")

# ─── config page ----------------------------------------------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>#MainMenu,header,footer{visibility:hidden;}</style>
""", unsafe_allow_html=True)

# ─── lance le worker une seule fois --------------------------------------
if "worker_started" not in st.session_state:
    if not JSON_FILE.exists():
        subprocess.Popen([sys.executable, str(WORKER)],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        st.session_state.worker_started=True
    else:
        st.session_state.worker_started=False

# ─── polling du fichier (cache ttl=1 s) -----------------------------------
@st.cache_data(ttl=1, show_spinner=False)
def read_tirage() -> pd.DataFrame|None:
    if not JSON_FILE.exists(): return None
    try:
        return pd.read_json(JSON_FILE)
    except ValueError:         # fichier encore incomplet
        return None

tirage_df = read_tirage()
ready     = tirage_df is not None

# ─── navigation -----------------------------------------------------------
if "page" not in st.session_state: st.session_state.page="intro"

if st.session_state.page=="intro":
    st.title("EXPERIENCE 3 – mots masqués")
    st.markdown("Cette expérience comporte d’abord **une courte familiarisation** puis le test principal.")
    if st.button("Commencer la familiarisation"): st.session_state.page="fam"; _rerun()

elif st.session_state.page=="fam":
    st.header("Familiarisation (2 mots)")
    st.info("Appuyez sur Espace dès que vous voyez le mot, tapez-le puis Entrée.")
    st.info("Recherche des stimuli du test … prête ? " + ("✅" if ready else "⏳"))
    components.v1.html(html(["PAIN","EAU"], dl=False), height=650, scrolling=False)
    st.divider()
    st.button("Passer au test principal",
              disabled=not ready,
              on_click=lambda: (st.session_state.update({"page":"exp"}), _rerun()))

else:  # page exp
    if not ready:
        st.warning("Les stimuli ne sont pas encore prêts, merci de patienter.")
        st.stop()

    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage"):
        st.dataframe(tirage_df.head())
    words = tirage_df.ortho.tolist()
    components.v1.html(html(words, dl=True), height=650, scrolling=False)
