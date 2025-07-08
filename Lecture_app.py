# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test 80 mots, synchronisation rAF / 60 Hz)
Exécution : streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ──────────────────── utilitaire de rerun ──────────────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ───────────────────── config Streamlit ────────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ───────────────────── états session ───────────────────────────────────────
defaults = dict(page="screen_test", hz_ok=False,
                tirage_ok=False, tirage_running=False)
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ──────────────────── paramètres tirage (inchangés) ────────────────────────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = {"letters": .68, "phons": .68}
SD_MULT            = {"letters": 2, "phons": 2,
                      "old20": .28, "pld20": .28, "freq": 1.9}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# ───────────────────── fonctions tirage (identiques) ───────────────────────
def to_float(s):  # … idem versions précédentes …
    return pd.to_numeric(
        s.astype(str).str.replace(" ", "", regex=False)
         .str.replace("\u00a0","", regex=False)
         .str.replace(",", ".", regex=False), errors="coerce")

def shuffled(df): return df.sample(frac=1, random_state=rng.randint(0,1_000_000)).reset_index(drop=True)
def cat_code(tag): return -1 if "LOW" in tag else 1

@st.cache_data(show_spinner=False)
def load_sheets():
    # (corps identique : lecture des 4 feuilles + stats)       ###
    #          ••• voir version précédente •••                 ###
    ...

def build_sheet():
    # (corps identique : sélection des 80 mots)                ###
    ...

# ───────────────────── HTML – test 60 Hz ───────────────────────────────────
TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:30px 0}
button{font-size:24px;padding:8px 28px}
</style></head><body>
<h2>Test de fréquence d’écran (cible : 60 Hz)</h2>
<p>Cliquez sur « Démarrer » pour mesurer votre fréquence.</p>
<div id="res">--</div>
<button id="start">Démarrer</button>
<script>
const res = document.getElementById("res");
document.getElementById("start").onclick = () => {
  document.getElementById("start").disabled = true;
  let t = [], n = 150;
  const step = k => {
    t.push(k);
    if (t.length < n) { requestAnimationFrame(step); }
    else {
      const deltas = t.slice(2).map((v,i)=>v-t[i+1]);
      const hz = 1000 / (deltas.reduce((a,b)=>a+b,0) / deltas.length);
      res.textContent = `≈ ${hz.toFixed(1)} Hz`;
      const ok = hz > 58 && hz < 62;
      res.style.color = ok ? "lime" : "red";
      document.getElementById("start").disabled = false;
      if (ok) Streamlit.setComponentValue("ok");   // ← renvoi vers Python
    }
  };
  requestAnimationFrame(step);
};
</script></body></html>"""

# ───────────────────── HTML – expérience (rAF) ────────────────────────────
EXP_HTML = Template(r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;display:flex;flex-direction:column;
align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;color:#fff;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center}
</style></head><body tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load",()=>document.body.focus());
const WORDS=$WORDS,CYCLE_F=$CYCLE_F,START_F=$START_F,STEP_F=$STEP_F;

let trial=0,results=[];
const scr=document.getElementById("scr");
const ans=document.getElementById("ans");

function waitF(n,cb){let i=0;function s(){i++>=n?cb():requestAnimationFrame(s)}requestAnimationFrame(s)}
function present(){
 if(trial>=WORDS.length){fin();return;}
 const w=WORDS[trial],mask="#".repeat(w.length);
 let show=START_F,hide=CYCLE_F-show;
 const t0=performance.now();let active=true;
 function cycle(){if(!active)return;
  scr.textContent=w;
  waitF(show,()=>{if(!active)return;
    scr.textContent=mask;
    waitF(hide,()=>{if(active){show+=STEP_F;hide=Math.max(0,CYCLE_F-show);cycle();}});});
 }
 cycle();
 function onSp(e){
  if(e.code==="Space"&&active){
    active=false;
    const rt=Math.round(performance.now()-t0);
    window.removeEventListener("keydown",onSp);
    scr.textContent="";
    ans.style.display="block";ans.value="";ans.focus();
    ans.addEventListener("keydown",function onEn(ev){
      if(ev.key==="Enter"){
        ev.preventDefault();
        results.push({word:w,rt_ms:rt,response:ans.value.trim()});
        ans.removeEventListener("keydown",onEn);
        ans.style.display="none";
        trial++;present();
      }});}}
 }
 window.addEventListener("keydown",onSp);}
function fin(){scr.style.fontSize="40px";scr.textContent=$END_MSG;$DOWNLOAD}
$STARTER
</script></body></html>""")

def experiment_html(words, *, cycle_frames=21, start_frames=1, step_frames=1,
                    with_download=True, fullscreen=False):
    download = ""
    if with_download:
        download = r"""
const csv=["word;rt_ms;response",...results.map(r=>`${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download="results.csv";
a.textContent="Télécharger les résultats";
a.style.fontSize="32px";
a.style.marginTop="30px";
document.body.appendChild(a);"""
    download = download.replace("$","$$")
    if fullscreen:
        starter = r"""
scr.textContent="Appuyez sur ESPACE pour commencer";
function first(e){if(e.code==="Space"){
  window.removeEventListener("keydown",first);
  document.documentElement.requestFullscreen?.();present();}}
window.addEventListener("keydown",first);"""
    else:
        starter = "present();"
    return EXP_HTML.substitute(
        WORDS=json.dumps(words),
        CYCLE_F=cycle_frames,
        START_F=start_frames,
        STEP_F=step_frames,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download,
        STARTER=starter)

# ──────────────────────── pages Streamlit ──────────────────────────────────
if st.session_state.page == "screen_test":
    st.write("### Vérification de l’écran (60 Hz requis)")
    hz_value = components.html(TEST60_HTML, height=600, scrolling=False)
    if hz_value == "ok": st.session_state.hz_ok = True
    if st.button("Passer à la présentation ➜", disabled=not st.session_state.hz_ok):
        st.session_state.page = "intro"; do_rerun()

elif st.session_state.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")
    st.markdown("""
Des mots apparaîtront très brièvement puis seront masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.

1. Entraînement (2 mots)  2. Test principal (80 mots)
""")
    if not st.session_state.tirage_running and not st.session_state.tirage_ok:
        st.session_state.tirage_running=True; do_rerun()
    if st.session_state.tirage_running and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet()
            mots = df["ortho"].tolist(); random.shuffle(mots)
            st.session_state.stimuli = mots
            st.session_state.tirage_ok=True
            st.session_state.tirage_running=False
        st.success("Tirage terminé !")
    if st.session_state.tirage_ok:
        if st.button("Commencer la familiarisation"):
            st.session_state.page = "fam"; do_rerun()

elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** dès que le mot apparaît, saisissez-le puis **Entrée**.")
    components.html(experiment_html(PRACTICE_WORDS, with_download=False),
                    height=650, scrolling=False)
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"; do_rerun()

elif st.session_state.page == "exp":
    components.html(experiment_html(st.session_state.stimuli,
                                    with_download=True, fullscreen=True),
                    height=700, scrolling=False)
