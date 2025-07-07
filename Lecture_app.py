# exp3_thread_fragment.py  (un seul fichier Streamlit)
from __future__ import annotations
import threading, random, time, json
import pandas as pd
from pathlib import Path

import streamlit as st
from streamlit import components
from streamlit.runtime.scriptrunner import (
    add_script_run_ctx, get_script_run_ctx,
)

# ────────── paramètres « Expérience 3 » (votre code existant) ────────────
XLSX = Path(__file__).with_name("Lexique.xlsx")
PRACTICE = ["PAIN", "EAU"]
rng = random.Random()

# -----------  placez ici VOTRE fonction build_sheet() complète -----------
def build_sheet() -> pd.DataFrame:
    # … votre code (tirage des 80 mots) …
    time.sleep(4)                       # → remplacez par le vrai calcul
    df = pd.DataFrame({"ortho":[f"W{i}" for i in range(80)]})
    return df
# -------------------------------------------------------------------------

# ────────── configuration Streamlit ──────────────────────────────────────
st.set_page_config("Expérience 3", layout="wide")
rerun = st.rerun if hasattr(st,"rerun") else st.experimental_rerun
st.markdown("<style>#MainMenu,header,footer{visibility:hidden;}</style>",
            unsafe_allow_html=True)

# ────────── thread de tirage (aucune UI, mais accès session_state) ───────
def launch_thread_once():
    if "tirage_ready" in st.session_state:          # déjà lancé ?
        return

    st.session_state.tirage_ready = False
    st.session_state.tirage_error = ""

    def worker():
        try:
            df = build_sheet()
        except Exception as e:
            st.session_state.tirage_error = str(e)
        else:
            st.session_state.tirage_df   = df
            lst = df.ortho.tolist(); random.shuffle(lst)
            st.session_state.stimuli     = lst
            st.session_state.tirage_ready = True
        rerun()                              # relance UNE fois

    th = threading.Thread(target=worker, daemon=True)
    add_script_run_ctx(th, get_script_run_ctx())
    th.start()

launch_thread_once()

# ────────── petit composant HTML pour l’expérience ───────────────────────
HTML = r"""
<!DOCTYPE html><html><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0"><div id="scr"></div><input id="ans"/>
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
def html(words,dl=True):
    return HTML.replace("__WORDS__",json.dumps(words)).replace("__DL__", "true" if dl else "false")

# ────────── fragment qui gère le bouton pendant le calcul ────────────────
@st.experimental_fragment
def familiarisation():
    st.header("Familiarisation (2 mots)")
    if st.session_state.tirage_ready:
        st.success("Stimuli du test prêts !")
    elif st.session_state.tirage_error:
        st.error(st.session_state.tirage_error)
    else:
        st.info("Recherche des stimuli en arrière-plan…")

    components.v1.html(html(PRACTICE,dl=False), height=650, scrolling=False)

    st.divider()
    st.button("Passer au test principal",
              disabled=not st.session_state.tirage_ready,
              on_click=lambda:(st.session_state.update({"page":"exp"}), rerun()))

# ────────── navigation principale ────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "intro"

if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 — mots masqués")
    st.write("Familiarisation puis test principal.")
    if st.button("Commencer la familiarisation"):
        st.session_state.page = "fam"
        rerun()

elif st.session_state.page == "fam":
    familiarisation()          # le fragment se met à jour tout seul

else:  # page « exp »
    if not st.session_state.tirage_ready:
        st.warning("Les stimuli ne sont pas encore prêts…")
        st.stop()
    st.header("Test principal (80 mots)")
    with st.expander("Aperçu du tirage "):
        st.dataframe(st.session_state.tirage_df.head())
    components.v1.html(html(st.session_state.stimuli, dl=True),
                       height=650, scrolling=False)
