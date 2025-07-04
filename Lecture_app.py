import json, random, streamlit as st
import streamlit.components.v1 as components

#############################################################################
# PARAMÈTRES
#############################################################################
STIMULI = [  # 80 mots en majuscules
    "DOIGT", "TABLE", "CHAISE", "MAISON", "VOITURE", "CHEVAL", "OISEAU",
    "BOUTEILLE",  # … complétez la liste …
]
random.shuffle(STIMULI)      # ordre aléatoire pour chaque participant

CYCLE_MS    = 350            # durée cycle mot+masque
START_MS    = 14             # 14 ms au 1er cycle
STEP_MS     = 14             # +14 ms / cycle

#############################################################################
# MISE EN PLEIN ÉCRAN : on masque la barre latérale Streamlit
#############################################################################
st.set_page_config(layout="wide", page_title="Expérience 3")
hide_menu = """
<style>
    #MainMenu, header, footer {visibility: hidden;}
    .css-1d391kg {display:none;}          /* barre latérale */
</style>
"""
st.markdown(hide_menu, unsafe_allow_html=True)

#############################################################################
# HTML + JavaScript : protocole temporel précis (≈ 16,7 ms min à 60 Hz)
#############################################################################
html = f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8">
<style>
    html,body   {{height:100%; margin:0; display:flex; align-items:center;
                  justify-content:center; background:white;
                  font-family:'Courier New', monospace;}}
    #screen     {{font-size:60px; user-select:none;}}
    #answer     {{display:none; font-size:48px; width:60%; text-align:center;}}
</style>
</head>
<body>
<div id="screen"></div>
<input id="answer" autocomplete="off"/>
<script>
/////////////////////////////////////////////////////////////////////////////
// PARAMETRES ENVOYÉS DE PYTHON -> JS
/////////////////////////////////////////////////////////////////////////////
const words      = {json.dumps(STIMULI)};
const CYCLE_MS   = {CYCLE_MS};
const START_MS   = {START_MS};
const STEP_MS    = {STEP_MS};

/////////////////////////////////////////////////////////////////////////////
// VARIABLES
/////////////////////////////////////////////////////////////////////////////
let idx = 0;
let results = [];
const disp  = document.getElementById("screen");
const input = document.getElementById("answer");

/////////////////////////////////////////////////////////////////////////////
// FONCTION QUI LANCE UN ESSAI
/////////////////////////////////////////////////////////////////////////////
function runTrial() {{
    if (idx >= words.length) {{ endExperiment(); return; }}

    const word = words[idx];
    const mask = "#".repeat(word.length);
    let stimDur = START_MS;
    let maskDur = CYCLE_MS - stimDur;
    let startTime = performance.now();
    let cycling = true;

    function cycle() {{
        disp.textContent = word;
        setTimeout(() => {{
            disp.textContent = mask;
            setTimeout(() => {{
                if (cycling) {{
                    stimDur += STEP_MS;
                    maskDur  = Math.max(0, CYCLE_MS - stimDur);
                    cycle();
                }}
            }}, maskDur);
        }}, stimDur);
    }}
    cycle();

    // ---------- Quand on appuie sur ESPACE ----------
    function onSpace(ev) {{
        if (ev.code === "Space" && cycling) {{
            cycling = false;
            const rt = Math.round(performance.now() - startTime);
            window.removeEventListener("keydown", onSpace);
            disp.textContent = "";
            input.style.display = "block";
            input.value = "";
            input.focus();

            // ---------- Validation de la réponse par Entrée ----------
            input.addEventListener("keydown", function onEnter(e) {{
                if (e.key === "Enter") {{
                    e.preventDefault();
                    results.push({{word: word, rt_ms: rt, response: input.value.trim()}});
                    input.removeEventListener("keydown", onEnter);
                    input.style.display = "none";
                    idx += 1;
                    runTrial();
                }}
            }});
        }}
    }}
    window.addEventListener("keydown", onSpace);
}}

/////////////////////////////////////////////////////////////////////////////
// FIN D’EXPÉRIENCE : on propose le CSV à télécharger
/////////////////////////////////////////////////////////////////////////////
function endExperiment() {{
    disp.style.fontSize = "40px";
    disp.textContent = "Merci ! L’expérience est terminée.";
    let csv  = "word,rt_ms,response\\n" +
               results.map(r => `${{r.word}},${{r.rt_ms}},${{r.response}}`).join("\\n");
    let blob = new Blob([csv], {{type: "text/csv"}});
    let url  = URL.createObjectURL(blob);

    let link = document.createElement("a");
    link.href = url;
    link.download = "results.csv";
    link.textContent = "Télécharger les résultats";
    link.style.fontSize = "32px";
    link.style.marginTop = "30px";
    document.body.appendChild(link);
}}

runTrial();   // On démarre immédiatement la 1re présentation
</script>
</body></html>
"""
components.html(html, height=600, width=1000, scrolling=False)
