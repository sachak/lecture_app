"""
Page 2 : protocole complet de l’Experiment 3
Alternance mot/masque (cycle 350 ms) ; +14 ms sur le mot à chaque cycle.
Le participant appuie ESPACE → champ-réponse → Entrée → essai suivant.
Un CSV « results.csv » est proposé à la fin.
"""

import json
import random
import streamlit as st
import streamlit.components.v1 as components

# ─────────────────── 1. PARAMÈTRES EXPÉRIMENTAUX ────────────────────
CYCLE_MS   = 350   # durée d’un cycle mot+masque
START_MS   = 14    # affichage du mot au premier cycle
STEP_MS    = 14    # augmentation par cycle

# Liste de 80 mots (exemples — à remplacer par votre matériel)
STIMULI = [
    "DOIGT","TABLE","CHAISE","MAISON","VOITURE","CHEVAL","OISEAU","BOUTEILLE",
    "MONTAGNE","RIVIERE","PLANTE","POMME","CHIEN","CHAT","MUSIQUE","PARAPLUIE",
    "MIROIR","FENETRE","LAMPE","TOMATE","SALADE","BUREAU","CASQUE","CAHIER",
    "NUAGE","ECRAN","SOURIS","CLAVIER","LIVRE","CRAYON","SERVIETTE","PORTE",
    "MOTEUR","VESTE","ROUTE","TRAIN","AVION","BATEAU","BIJOU","CROISSANT",
    "EGLISE","PRISON","CAMION","BUS","LUMIERE","OMBRE","SOEUR","FRERE",
    "MER","OCEAN","SABLE","FORET","ARBRE","FLEUR","SOLEIL","LUNE",
    "ETOILE","NEIGE","GLACE","PLUIE","VENT","ORAGE","COEUR","SANG",
    "TETE","MAIN","PIED","JAMBON","FROMAGE","BEURRE","PAIN","SUCRE",
    "MARCHÉ","VILLAGE","VITAMINE","BASKET","SPORT","ECOLE","EXAMEN","UNIVERS",
]
random.shuffle(STIMULI)          # ordre aléatoire pour chaque participant

# ─────────────────── 2. MISE EN PLEIN ÉCRAN (CSS) ───────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")

hide_streamlit_style = """
<style>
/* on masque menu, footer, barre latérale */
#MainMenu, header, footer {visibility: hidden;}
.css-1d391kg {display: none;}   /* barre latérale (class Streamlit) */
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ─────────────────── 3. HTML + JavaScript embarqués ─────────────────
html_code = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body {{
     height:100%; margin:0;
     display:flex; align-items:center; justify-content:center;
     background:white; font-family:'Courier New',monospace;
 }}
 #screen {{ font-size:60px; user-select:none; }}
 #answer {{ display:none; font-size:48px; width:60%; text-align:center; }}
</style></head><body>
<div id="screen"></div>
<input id="answer" autocomplete="off" />
<script>
/**********************************************************************
 * PARAMÈTRES REÇUS DE PYTHON
 *********************************************************************/
const WORDS   = {json.dumps(STIMULI)};    // liste des mots
const CYCLE   = {CYCLE_MS};               // 350 ms
const START   = {START_MS};               // 14 ms
const STEP    = {STEP_MS};                // +14 ms / cycle

/**********************************************************************
 * VARIABLES GLOBALES
 *********************************************************************/
let idx = 0;                      // indice du mot courant
let results = [];                 // stockage réponses
const scr = document.getElementById("screen");
const ans = document.getElementById("answer");

/**********************************************************************
 * FONCTION QUI GÈRE UN ESSAI
 *********************************************************************/
function runTrial() {{
  if (idx >= WORDS.length) {{ endExperiment(); return; }}

  const word = WORDS[idx];
  const mask = "#".repeat(word.length);

  let stimDur = START;
  let maskDur = CYCLE - stimDur;
  let startTime = performance.now();
  let cycling = true;

  // ---------- boucle mot / masque ----------
  function cycle() {{
    scr.textContent = word;
    setTimeout(() => {{
      scr.textContent = mask;
      setTimeout(() => {{
        if (cycling) {{
          stimDur += STEP;
          maskDur  = Math.max(0, CYCLE - stimDur);
          cycle();
        }}
      }}, maskDur);
    }}, stimDur);
  }}
  cycle();

  // ---------- appui sur ESPACE ----------
  function onSpace(ev) {{
    if (ev.code === "Space" && cycling) {{
      cycling = false;
      const rt = Math.round(performance.now() - startTime);
      window.removeEventListener("keydown", onSpace);

      scr.textContent = "";
      ans.style.display = "block";
      ans.value = "";
      ans.focus();

      // ---------- validation par Entrée ----------
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
}}

/**********************************************************************
 * FIN D’EXPÉRIENCE : création du CSV + lien de téléchargement
 *********************************************************************/
function endExperiment() {{
  scr.style.fontSize = "40px";
  scr.textContent = "Merci ! L’expérience est terminée.";

  const header = "word,rt_ms,response\\n";
  const rows   = results.map(r => `${{r.word}},${{r.rt_ms}},${{r.response}}`).join("\\n");
  const blob   = new Blob([header + rows], {{type: "text/csv"}});
  const url    = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url; link.download = "results.csv";
  link.textContent = "Télécharger les résultats";
  link.style.fontSize = "32px"; link.style.marginTop = "30px";
  document.body.appendChild(link);
}}

runTrial();            // on démarre le tout
</script></body></html>
"""

# ─────────────────── 4. AFFICHAGE DANS STREAMLIT ────────────────────
components.html(html_code, height=650, width=1100, scrolling=False)
