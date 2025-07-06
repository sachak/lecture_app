# -*- coding: utf-8 -*-
# =============================================================
#  Lecture_app.py   —   Expérience Streamlit
# =============================================================
# Intro  ➜  3 essais d’entraînement  ➜  80 mots réels
# Les 80 mots sont tirés en arrière-plan pendant l’intro + entraînement.
# =============================================================
import json, random, threading, time, pandas as pd, numpy as np
import streamlit as st
import streamlit.components.v1 as components
from get_stimuli import get_stimuli      # ← ton module de tirage

# ------------ 0. CONFIG VISUEL --------------------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}</style>",
    unsafe_allow_html=True
)

# ------------ 1. PETIT LEXIQUE (juste pour choisir 3 mots d’essai) -----
CSV_FILE = "Lexique383.csv"           # doit être présent

@st.cache_data(show_spinner="Chargement du lexique…")
def load_lexique():
    df = pd.read_csv(CSV_FILE, sep=";", decimal=".", encoding="utf-8",
                     dtype=str, engine="python", on_bad_lines="skip")
    df = df.rename(columns=lambda c: c.lower())
    df = df.rename(columns={"ortho": "word"})
    df.word = df.word.str.upper()
    return df[["word"]].dropna()

LEX = load_lexique()

# ------------ 2. TIRAGE DES 80 MOTS EN TÂCHE DE FOND -------------------
def _launch_selection():
    try:
        st.session_state["stimuli"] = get_stimuli()
        st.session_state["stimuli_ready"] = True
    except Exception as e:
        st.session_state["stimuli_error"] = str(e)
        st.session_state["stimuli_ready"] = False

if "stimuli_ready" not in st.session_state:
    st.session_state["stimuli_ready"] = False
    st.session_state["stimuli_error"] = None
    threading.Thread(target=_launch_selection, daemon=True).start()

# ------------ 3. MOTS D’ENTRAÎNEMENT (3 mots de 3 lettres) ------------
TRAIN_WORDS = random.sample(
    [w for w in LEX.word if len(w) == 3], k=3)

# ------------ 4. ÉTAT DE SESSION --------------------------------------
if "page" not in st.session_state:
    st.session_state.page  = "intro"
    st.session_state.index = 0            # pour l’entraînement

# ======================================================================
#  PAGE 1 : INTRO
# ======================================================================
if st.session_state.page == "intro":
    st.title("EXPERIENCE 3 — instructions")
    st.markdown("""
    Vous allez voir : dièses « ###### » puis des mots.  
    Appuyez sur [Espace] dès que le mot apparaît, puis retapez-le et
    validez avec [Entrée].  
    Nous commençons par **3 essais d’entraînement**.
    """)
    if st.button("Je suis prêt·e"):
        st.session_state.page = "train"
        st.experimental_rerun()

# ======================================================================
#  PAGE 2 : ENTRAÎNEMENT (3 essais)
# ======================================================================
elif st.session_state.page == "train":
    i = st.session_state.index
    if i >= len(TRAIN_WORDS):                       # terminé
        st.session_state.page = "wait_real"
        st.experimental_rerun()
    else:
        st.subheader(f"Essai d’entraînement {i+1} / {len(TRAIN_WORDS)}")
        st.write("Mot cible :", TRAIN_WORDS[i])
        if st.button("Valider (fictif)"):
            st.session_state.index += 1
            st.experimental_rerun()

# ======================================================================
#  PAGE 2 bis : ATTENTE SI LES 80 MOTS NE SONT PAS PRÊTS
# ======================================================================
elif st.session_state.page == "wait_real":
    if st.session_state.get("stimuli_ready"):
        st.session_state.page = "exp"
        st.experimental_rerun()
    elif st.session_state.get("stimuli_error"):
        st.error("Erreur pendant la génération des stimuli :\n\n"
                 + st.session_state["stimuli_error"])
    else:
        st.info("Préparation des 80 mots… merci de patienter.")
        st.progress(None)

# ======================================================================
#  PAGE 3 : EXPÉRIENCE RÉELLE (80 mots)
# ======================================================================
elif st.session_state.page == "exp":
    STIMULI = st.session_state["stimuli"]   # liste de 80 mots (str)
    # ----------- paramètres d’affichage -------------
    CYCLE, START, STEP = 350, 14, 14        # mêmes valeurs que ton code JS
    # ----------- bloc HTML/JS (accolades doublées) --
    html = f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
html,body{{height:100%;margin:0;display:flex;align-items:center;justify-content:center;
font-family:'Courier New',monospace}}
#scr{{font-size:60px;user-select:none}}
#ans{{display:none;font-size:48px;width:60%;text-align:center}}
</style></head>
<body id="body" tabindex="0">
<div id="scr"></div><input id="ans" autocomplete="off"/>
<script>
window.addEventListener('load',()=>document.getElementById('body').focus());

const W={json.dumps(STIMULI)},C={CYCLE},S={START},P={STEP};
let i=0,res=[];
const scr=document.getElementById('scr'), ans=document.getElementById('ans');

function run(){{ if(i>=W.length){{fin();return;}}
  const w=W[i],m='#'.repeat(w.length);
  let sd=S,md=C-sd,t0=performance.now(),on=true,t1,t2;
  (function loop(){{ if(!on)return;
    scr.textContent=w;
    t1=setTimeout(()=>{{ if(!on)return;
       scr.textContent=m;
       t2=setTimeout(()=>{{ if(on){{ sd+=P;md=Math.max(0,C-sd);loop(); }} }},md);
    }},sd);
  }})();
  window.addEventListener('keydown',function sp(e){{ if(e.code==='Space'&&on){{ 
        on=false;clearTimeout(t1);clearTimeout(t2);
        const rt=Math.round(performance.now()-t0);
        window.removeEventListener('keydown',sp);
        scr.textContent='';ans.style.display='block';ans.value='';ans.focus();
        ans.addEventListener('keydown',function ent(ev){{ if(ev.key==='Enter'){{ 
           ev.preventDefault();
           res.push({{word:w,rt_ms:rt,response:ans.value.trim()}});
           ans.removeEventListener('keydown',ent);
           ans.style.display='none';i++;run();
        }}}); }} }});
}}

function fin(){{ scr.style.fontSize='40px';scr.textContent='Merci !';
  const csv=['word;rt_ms;response',...res.map(r=>r.word+';'+r.rt_ms+';'+r.response)].join('\\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}}));
  a.download='results.csv';
  a.textContent='Télécharger les résultats';
  a.style.fontSize='32px';a.style.marginTop='30px';
  document.body.appendChild(a);
}}
run();
</script></body></html>"""
    components.html(html, height=650, scrolling=False)
