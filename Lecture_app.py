# -*- coding: utf-8 -*-
"""
Expérience 3 – version « tout-en-un »
Correctif : plus de masque "####" qui reste visible quand le champ-réponse
apparaît.
"""

import json, random, streamlit as st
import streamlit.components.v1 as components

# ----------------------- PARAMÈTRES ------------------------------
STIMULI = [
    "DOIGT","TABLE","CHAISE","MAISON","VOITURE","CHEVAL","OISEAU","BOUTEILLE",
    # … vos 80 mots …
]
random.shuffle(STIMULI)
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ------------------- CONFIGURATION STREAMLIT ---------------------
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE_CSS = """
<style>
#MainMenu, header, footer {visibility:hidden;}
.css-1d391kg {display:none;}    /* barre latérale Streamlit */
</style>
"""
# état courant : intro  ou  exp
if "stage" not in st.session_state:
    st.session_state.stage = "intro"

# ----------------------- PAGE D'INTRO ----------------------------
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")

    st.markdown("""
Vous verrez un mot très brièvement au centre de l’écran, alternant avec un
masque de `#####`.  
À chaque cycle (350 ms) le mot dure **14 ms de plus** et le masque **14 ms de
moins**.

Procédure :
1. Fixez le centre.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Tapez le mot dans le champ qui apparaît puis validez par **Entrée**.  
""")

    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ---------------------- PAGE EXPÉRIENCE --------------------------
elif st.session_state.stage == "exp":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)

    html_code = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body {{
   height:100%; margin:0; display:flex; align-items:center; justify-content:center;
   background:white; font-family:'Courier New',monospace;
 }}
 #scr {{font-size:60px; user-select:none;}}
 #ans {{display:none; font-size:48px; width:60%; text-align:center;}}
</style>
</head>
<body id="body" tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
/******************************************************************
 * Auto-focus : dès le chargement de l’iframe
 *****************************************************************/
window.addEventListener('load', ()=>document.getElementById('body').focus());

/******************************************************************
 * Paramètres passés depuis Python
 *****************************************************************/
const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

/******************************************************************
 * Variables globales
 *****************************************************************/
let i = 0, results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

/******************************************************************
 * Lancement d’un essai
 *****************************************************************/
function trial(){{
  if(i >= WORDS.length) {{ end(); return; }}
  const w = WORDS[i], mask = "#".repeat(w.length);
  let sd = START, md = CYCLE - sd, t0 = performance.now(), go = true;
  let to1 = null, to2 = null;           // id des deux time-outs actifs

  function cycle(){{
    if(!go) return;                     // sécurité
    scr.textContent = w;
    to1 = setTimeout(()=>{{
      if(!go) return;                   // sécurité : on ne change plus l’écran
      scr.textContent = mask;
      to2 = setTimeout(()=>{{
        if(go){{
          sd += STEP;
          md = Math.max(0, CYCLE - sd);
          cycle();
        }}
      }}, md);
    }}, sd);
  }}
  cycle();

  /* ---------- Appui sur ESPACE = mot reconnu ---------- */
  function onSpace(ev){{
    if(ev.code === 'Space' && go){{
      go = false;                       // stoppe immédiatement le cycle
      clearTimeout(to1); clearTimeout(to2);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener('keydown', onSpace);

      scr.textContent = '';             // on vide l’écran
      ans.style.display = 'block'; ans.value = ''; ans.focus();

      /* ----- Entrée = validation ----- */
      ans.addEventListener('keydown', function onEnter(e){{
        if(e.key === 'Enter'){{
          e.preventDefault();
          results.push({{word:w, rt_ms:rt, response:ans.value.trim()}});
          ans.removeEventListener('keydown', onEnter);
          ans.style.display = 'none';
          i++; trial();
        }}
      }});
    }}
  }}
  window.addEventListener('keydown', onSpace);
}}

/******************************************************************
 * Fin : téléchargement CSV
 *****************************************************************/
function endExperiment() {
  scr.style.fontSize = '40px';
  scr.textContent    = 'Merci ! Fin de l’expérience.';

  /* séparateur */
  const SEP    = ';';

  /* entête + lignes */
  const header = ['word','rt_ms','response'].join(SEP) + '\\n';
  const rows   = results
                   .map(r => [r.word, r.rt_ms, r.response].join(SEP))
                   .join('\\n');

  const blob = new Blob([header + rows], {type: 'text/csv;charset=utf-8'});
  const url  = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href        = url;
  a.download    = 'results.csv';      // garde l’extension .csv
  a.textContent = 'Télécharger les résultats (.csv – séparateur ;)';
  a.style.fontSize = '32px';
  a.style.marginTop = '30px';
  document.body.appendChild(a);
}}

trial();  // lancement
</script>
</body></html>
"""
    components.html(html_code, height=650, width=1100, scrolling=False)
