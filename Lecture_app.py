@@ -1,22 +1,17 @@
# -*- coding: utf-8 -*-
"""
Expérience 3 – Masquage progressif d'un mot.
1. Page d'instructions.
2. Après clic sur "Démarrer", bascule automatique vers l'expérience.
   – Mot + masque alternés dans des cycles de 350 ms.
   – Le mot gagne 14 ms et le masque en perd 14 ms à chaque cycle.
   – ESPACE = mot reconnu  ➜ champ-réponse (Entrée pour valider).
   – Fin : téléchargement d’un CSV (mot, RT, réponse).
Expérience 3 : présentation mot / masque.
1. Page d’instructions.
2. Après clic sur « Démarrer » : focus automatique sur l’iframe ⇒
   l’appui sur ESPACE fonctionne tout de suite (pas besoin de cliquer dans l’écran).
"""

import json
import random
import streamlit as st
import json, random, streamlit as st
import streamlit.components.v1 as components

# ────────────────────── PARAMÈTRES GÉNÉRAUX ────────────────────────
# 80 mots d'exemple (mettez vos propres stimuli)
# ───────────────────────── PARAMÈTRES ──────────────────────────
STIMULI = [
    # 80 mots – exemples
    "DOIGT","TABLE","CHAISE","MAISON","VOITURE","CHEVAL","OISEAU","BOUTEILLE",
    "MONTAGNE","RIVIERE","PLANTE","POMME","CHIEN","CHAT","MUSIQUE","PARAPLUIE",
    "MIROIR","FENETRE","LAMPE","TOMATE","SALADE","BUREAU","CASQUE","CAHIER",
@@ -28,168 +23,138 @@
    "TETE","MAIN","PIED","JAMBON","FROMAGE","BEURRE","PAIN","SUCRE",
    "MARCHE","VILLAGE","VITAMINE","BASKET","SPORT","ECOLE","EXAMEN","UNIVERS"
]
random.shuffle(STIMULI)                  # ordre aléatoire pour chaque participant
random.shuffle(STIMULI)

CYCLE_MS = 350      # durée complète mot+masque
START_MS = 14       # mot à 14 ms au 1er cycle
STEP_MS  = 14       # +14 ms par cycle pour le mot (le masque perd 14 ms)
CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ────────────────────────── CONFIG PAGE ───────────────────────────
# ─────────────────── config globale Streamlit ──────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")

# Cache barre latérale, menu, footer pour la phase « expérience »
HIDE_STREAMLIT_CSS = """
HIDE_CSS = """
<style>
#MainMenu, header, footer {visibility: hidden;}
.css-1d391kg {display: none;}      /* barre latérale */
#MainMenu, header, footer {visibility:hidden;}
.css-1d391kg {display:none;}         /* barre latérale Streamlit */
</style>
"""

# ─────────────────────── GESTION DES « PAGES » ─────────────────────
# ───────────────────── choix de la « page » ────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "intro"      # intro  →  experiment
    st.session_state.stage = "intro"

# ────────────────────────── PAGE INTRO ────────────────────────────
# ───────────────────────── PAGE 1 : INTRO ──────────────────────
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")

    st.markdown("""
Bienvenue !

Vous verrez un mot très brièvement affiché au centre de l’écran, alternant avec un masque de **#####**.  
À chaque cycle de 350 ms :
• le mot reste **14 ms de plus**.  
• le masque reste **14 ms de moins**.
Vous verrez un mot très brièvement, alternant avec un masque de **#####**.  
À chaque cycle (350 ms) le mot reste **14 ms de plus** et le masque **14 ms de moins**.

Procédure :
1. Fixez le centre de l’écran.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Un champ apparaît : tapez le mot reconnu puis validez avec **Entrée**.  

Cliquez sur le bouton ci-dessous pour commencer l’expérience.
3. Un champ apparaît : tapez le mot reconnu et validez par **Entrée**.  
""")

    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "experiment"
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ─────────────────────── PAGE EXPÉRIENCE ───────────────────────────
elif st.session_state.stage == "experiment":
    st.markdown(HIDE_STREAMLIT_CSS, unsafe_allow_html=True)
# ───────────────────── PAGE 2 : EXPÉRIENCE ─────────────────────
elif st.session_state.stage == "exp":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)

    # Code HTML + JavaScript inséré dans Streamlit
    html_code = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body {{
    height:100%; margin:0;
    display:flex; align-items:center; justify-content:center;
    background:white; font-family:'Courier New',monospace;
   height:100%; margin:0;
   display:flex; align-items:center; justify-content:center;
   background:white; font-family:'Courier New',monospace;
 }}
 #screen  {{ font-size:60px; user-select:none; }}
 #answer  {{ display:none; font-size:48px; width:60%; text-align:center; }}
 #scr   {{font-size:60px; user-select:none;}}
 #ans   {{display:none; font-size:48px; width:60%; text-align:center;}}
</style>
</head><body>
  <div id="screen"></div>
  <input id="answer" autocomplete="off" />
</head>
<body tabindex="0" id="body">  <!-- tabindex + id pour prendre le focus -->
  <div id="scr"></div>
  <input id="ans" autocomplete="off" />
<script>
/*********************************************************************
 * Paramètres transmis par Python
 ********************************************************************/
const WORDS = {json.dumps(STIMULI)};      // liste des mots
const CYCLE = {CYCLE_MS};                 // 350 ms
const START = {START_MS};                 // 14 ms
const STEP  = {STEP_MS};                  // +14 ms / cycle

/*********************************************************************
 * Variables globales
 ********************************************************************/
let idx = 0;                              // indice du mot courant
let results = [];                         // stockage des résultats
const scr = document.getElementById("screen");
const ans = document.getElementById("answer");

/*********************************************************************
 * Lance un essai
 ********************************************************************/
function runTrial() {{
  if (idx >= WORDS.length) {{ endExperiment(); return; }}

  const word = WORDS[idx];
  const mask = "#".repeat(word.length);

  let stimDur = START;
  let maskDur = CYCLE - stimDur;
  let t0 = performance.now();
  let cycling = true;

  function oneCycle() {{
    scr.textContent = word;
    setTimeout(() => {{
      scr.textContent = mask;
      setTimeout(() => {{
        if (cycling) {{
          stimDur += STEP;
          maskDur = Math.max(0, CYCLE - stimDur);
          oneCycle();
        }}
      }}, maskDur);
    }}, stimDur);
  }}
  oneCycle();

  // ── ESPACE = mot reconnu ───────────────────────────────────────
  function onSpace(ev) {{
    if (ev.code === "Space" && cycling) {{
      cycling = false;
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener("keydown", onSpace);

      scr.textContent = "";
      ans.style.display = "block";
      ans.value = "";
      ans.focus();

      // ── Entrée = validation de la réponse ─────────────────────
      ans.addEventListener("keydown", function onEnter(e) {{
        if (e.key === "Enter") {{
          e.preventDefault();
          results.push({{word: word, rt_ms: rt, response: ans.value.trim()}});
          ans.removeEventListener("keydown", onEnter);
          ans.style.display = "none";
          idx += 1;
          runTrial();
        }}
      }});
    }}
  }}
  window.addEventListener("keydown", onSpace);
/*****************************************************************
 * Auto-focus immédiat : la page a été chargée suite au clic sur
 * « Démarrer » ; ce clic est considéré comme un geste utilisateur,
 * donc le navigateur accepte que l’iframe prenne le focus.
 *****************************************************************/
window.addEventListener('load', () => {{
  document.getElementById('body').focus();   // le body reçoit le focus
}});

/*****************************************************************
 * Paramètres Python → JS
 *****************************************************************/
const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

/*****************************************************************
 * Variables
 *****************************************************************/
let i = 0, results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

/*****************************************************************
 * Boucle d’un essai
 *****************************************************************/
function trial() {{
 if (i >= WORDS.length) {{ end(); return; }}
 const w = WORDS[i], mask = "#".repeat(w.length);
 let sd = START, md = CYCLE - sd, t0 = performance.now(), go=true;

 function cycle() {{
   scr.textContent = w;
   setTimeout(()=>{{
     scr.textContent = mask;
     setTimeout(()=>{{ if(go){{ sd+=STEP; md=Math.max(0,CYCLE-sd); cycle(); }} }}, md);
   }}, sd);
 }}
 cycle();

 function onSpace(e) {{
   if (e.code === 'Space' && go) {{
     go = false; const rt = Math.round(performance.now()-t0);
     window.removeEventListener('keydown', onSpace);
     scr.textContent = '';
     ans.style.display='block'; ans.value=''; ans.focus();

     ans.addEventListener('keydown', function onEnter(ev){{
       if(ev.key==='Enter') {{
         ev.preventDefault();
         results.push({{word:w, rt_ms:rt, response:ans.value.trim()}});
         ans.removeEventListener('keydown', onEnter);
         ans.style.display='none'; i++; trial();
       }}
     }});
   }}
 }}
 window.addEventListener('keydown', onSpace);
}}

/*********************************************************************
 * Fin d’expérience → CSV téléchargeable
 ********************************************************************/
function endExperiment() {{
  scr.style.fontSize = "40px";
  scr.textContent = "Merci ! L’expérience est terminée.";

  const header = "word,rt_ms,response\\n";
  const rows   = results.map(r => `${{r.word}},${{r.rt_ms}},${{r.response}}`).join("\\n");
  const blob   = new Blob([header + rows], {{type: "text/csv"}});
  const url    = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url; a.download = "results.csv";
  a.textContent = "Télécharger les résultats";
  a.style.fontSize = "32px";
  a.style.marginTop = "30px";
/*****************************************************************
 * Fin d’expérience : CSV
 *****************************************************************/
function end() {{
  scr.style.fontSize='40px'; scr.textContent='Merci ! Fin de l’expérience.';
  const csv = "word,rt_ms,response\\n"+
              results.map(r=>`${{r.word}},${{r.rt_ms}},${{r.response}}`).join("\\n");
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{type:'text/csv'}}));
  a.download = 'results.csv';
  a.textContent = 'Télécharger les résultats';
  a.style.fontSize='32px'; a.style.marginTop='30px';
  document.body.appendChild(a);
}}

runTrial();        // démarrage de la première présentation
trial();  // lancement
</script>
</body></html>
    """

    # Affichage du bloc HTML/JS dans Streamlit
"""
    # Affiche l’iframe (focus pris automatiquement)
    components.html(html_code, height=650, width=1100, scrolling=False)
