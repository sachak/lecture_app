# -*- coding: utf-8 -*-
"""
EXPERIMENT 3 – présentation masquée d’un mot
  • page 1 : instructions + bouton « Démarrer »
  • page 2 : alternance MOT / #####, arrêt sur ESPACE, saisie réponse
  • CSV final séparé par des « ; » (compatible Excel FR)
"""

import json, random, streamlit as st
import streamlit.components.v1 as components

# ───────────────────────── PARAMÈTRES ──────────────────────────
STIMULI = [
    # 80 mots d’exemple – remplacez par votre liste
    "DOIGT","TABLE","CHAISE","MAISON","VOITURE","CHEVAL","OISEAU","BOUTEILLE",
    "MONTAGNE","RIVIERE","PLANTE","POMME","CHIEN","CHAT","MUSIQUE","PARAPLUIE",
    "MIROIR","FENETRE","LAMPE","TOMATE","SALADE","BUREAU","CASQUE","CAHIER",
    "NUAGE","ECRAN","SOURIS","CLAVIER","LIVRE","CRAYON","SERVIETTE","PORTE",
    "MOTEUR","VESTE","ROUTE","TRAIN","AVION","BATEAU","BIJOU","CROISSANT",
    "EGLISE","PRISON","CAMION","BUS","LUMIERE","OMBRE","SOEUR","FRERE",
    "MER","OCEAN","SABLE","FORET","ARBRE","FLEUR","SOLEIL","LUNE",
    "ETOILE","NEIGE","GLACE","PLUIE","VENT","ORAGE","COEUR","SANG",
    "TETE","MAIN","PIED","JAMBON","FROMAGE","BEURRE","PAIN","SUCRE",
    "MARCHE","VILLAGE","VITAMINE","BASKET","SPORT","ECOLE","EXAMEN","UNIVERS"
]
random.shuffle(STIMULI)

CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

# ───────────────── CONFIGURATION STREAMLIT ─────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
HIDE_CSS = """
<style>
#MainMenu, header, footer {visibility:hidden;}
.css-1d391kg {display:none;}   /* sidebar Streamlit */
</style>
"""

if "stage" not in st.session_state:
    st.session_state.stage = "intro"        # intro → exp

# ───────────────────────── PAGE INTRO ──────────────────────────
if st.session_state.stage == "intro":
    st.title("EXPERIMENT 3 : reconnaissance de mots masqués")

    st.markdown("""
Vous verrez un mot très brièvement, alternant avec un masque de **#####**.  
À chaque cycle (350 ms) : le mot dure **14 ms de plus** et le masque **14 ms de moins**.

Procédure :
1. Fixez le centre de l’écran.  
2. Appuyez sur **ESPACE** dès que vous reconnaissez le mot.  
3. Un champ apparaît ; tapez le mot puis validez par **Entrée**.  
""")

    if st.button("Démarrer l’expérience"):
        st.session_state.stage = "exp"
        st.experimental_rerun()

# ───────────────────────── PAGE EXPÉRIENCE ─────────────────────
elif st.session_state.stage == "exp":
    st.markdown(HIDE_CSS, unsafe_allow_html=True)

    html_code = f"""
<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<style>
 html,body {{
   height:100%; margin:0;
   display:flex; align-items:center; justify-content:center;
   background:#ffffff; font-family:"Courier New",monospace;
 }}
 #scr {{font-size:60px; user-select:none;}}
 #ans {{display:none; font-size:48px; width:60%; text-align:center;}}
</style>
</head>
<body id="body" tabindex="0">
  <div id="scr"></div>
  <input id="ans" autocomplete="off" />
<script>
/******************************************************************
 * Focus immédiat dans l'iframe (clic « Démarrer » = geste user)
 *****************************************************************/
window.addEventListener('load', () =>
  document.getElementById('body').focus()
);

/******************** Paramètres reçus de Python *******************/
const WORDS = {json.dumps(STIMULI)};
const CYCLE = {CYCLE_MS}, START = {START_MS}, STEP = {STEP_MS};

/******************** Variables globales ***************************/
let i = 0, results = [];
const scr = document.getElementById('scr');
const ans = document.getElementById('ans');

/******************** Lancement d'un essai *************************/
function trial() {{
  if (i >= WORDS.length) {{ end(); return; }}
  const w = WORDS[i], mask = "#".repeat(w.length);
  let sd = START, md = CYCLE - sd, t0 = performance.now(), go = true;
  let t1 = null, t2 = null;                // id des time-outs actifs

  function loop() {{
    if (!go) return;
    scr.textContent = w;
    t1 = setTimeout(() => {{
      if (!go) return;
      scr.textContent = mask;
      t2 = setTimeout(() => {{
        if (go) {{
          sd += STEP;
          md = Math.max(0, CYCLE - sd);
          loop();
        }}
      }}, md);
    }}, sd);
  }}
  loop();

  /******************** Appui sur ESPACE ****************************/
  function onSpace(ev) {{
    if (ev.code === 'Space' && go) {{
      go = false;
      clearTimeout(t1); clearTimeout(t2);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener('keydown', onSpace);

      scr.textContent = "";
      ans.style.display = "block";
      ans.value = "";
      ans.focus();

      /**************** Entrée = validation de la réponse ***********/
      ans.addEventListener('keydown', function onEnter(e) {{
        if (e.key === 'Enter') {{
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

/******************** Fin d’expérience -> CSV « ; » ***************/
function end() {{
  scr.style.fontSize = "40px";
  scr.textContent    = "Merci ! Fin de l’expérience.";

  const SEP = ';';
  const header = ['word','rt_ms','response'].join(SEP) + '\\n';
  const rows   = results
                   .map(r => [r.word, r.rt_ms, r.response].join(SEP))
                   .join('\\n');
  const blob = new Blob([header + rows],
                        {{type:'text/csv;charset=utf-8'}});
  const url  = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url; a.download = 'results.csv';
  a.textContent = 'Télécharger les résultats (.csv)';
  a.style.fontSize = '32px';
  a.style.marginTop = '30px';
  document.body.appendChild(a);
}}

trial();  // premier essai
</script>
</body></html>
"""
    components.html(html_code, height=650, width=1100, scrolling=False)
