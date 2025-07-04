import json
import streamlit as st
import streamlit.components.v1 as components

###############################################################################
# 1. PARAMÈTRES EXPÉRIMENTAUX – à adapter si besoin
###############################################################################
STIMULI = [
    # Les 80 mots d’Experiments 1-2  (exemple)
    "Doigt", "Table", "Chaise", "Maison", "Voiture", "Cheval", "Oiseau", "Bouteille",
    # … complétez jusqu’à 80 …
]

CYCLE_LEN_MS   = 350      # durée d’un cycle complet mot+masque
STIM_START_MS  = 14       # 14 ms au premier cycle
STIM_STEP_MS   = 14       # +14 ms à chaque cycle

###############################################################################
# 2. INTERFACE STREAMLIT
###############################################################################
st.set_page_config(page_title="Expérience masquage visuel – Expe 3", layout="centered")
st.title("EXPERIMENT 3 – reconnaissance visuelle de mots masqués")
st.markdown(
"""
Appuyez sur **Espace** dès que vous reconnaissez le mot.  
Le champ réponse s’affichera alors ; tapez le mot, validez par **Entrée**.  
Essayez d’être rapide *et* précis.  
"""
)

if "started" not in st.session_state:
    st.session_state.started = False

if not st.session_state.started:
    if st.button("Démarrer l’expérience"):
        st.session_state.started = True
        st.experimental_rerun()
    st.stop()

###############################################################################
# 3. CONSTRUCTION DU BLOC HTML + JavaScript
###############################################################################
stim_json  = json.dumps([w.upper() for w in STIMULI])  # transmissible à JS
html_code  = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
    body,html         {{ margin:0; height:100%; display:flex;
                         justify-content:center; align-items:center;
                         font-family: 'Courier New', monospace; }}
    #disp             {{ font-size:48px; user-select:none; }}
    #resp             {{ font-size:36px; padding:4px 8px; width:60%;
                         text-align:center; display:none; }}
</style>
</head>
<body>
    <div id="disp"></div>
    <input id="resp" autocomplete="off" />
<script>
//////////////////////////////////////////////////////////////////////
// PARAMETRES PASSÉS DE PYTHON -> JS
//////////////////////////////////////////////////////////////////////
const stimuli       = {stim_json};      // liste de mots
const CYCLE_LEN     = {CYCLE_LEN_MS};   // 350 ms
const STIM_START    = {STIM_START_MS};  // 14 ms
const STIM_INC      = {STIM_STEP_MS};   // +14 ms / cycle

//////////////////////////////////////////////////////////////////////
// VARIABLES DE CONTROLE
//////////////////////////////////////////////////////////////////////
let index     = 0;           // mot courant
let results   = [];          // stockage des données
let disp      = document.getElementById('disp');
let respBox   = document.getElementById('resp');

//////////////////////////////////////////////////////////////////////
// FONCTION PRINCIPALE : lance un essai
//////////////////////////////////////////////////////////////////////
function runTrial() {{
    if (index >= stimuli.length) {{ endExp(); return; }}

    const word      = stimuli[index];
    const mask      = "#".repeat(word.length);
    let stimDur     = STIM_START;
    let maskDur     = CYCLE_LEN - stimDur;
    let t0          = performance.now();   // début du premier cycle
    let running     = true;                // true tant qu’on alterne mot/masque

    // ---------- Gestion des cycles mot/masque ----------
    function oneCycle() {{
        // Affiche le mot
        disp.textContent = word;
        setTimeout(() => {{
            // Affiche le masque
            disp.textContent = mask;
            setTimeout(() => {{
                if(running) {{
                    stimDur += STIM_INC;
                    maskDur  = Math.max(0, CYCLE_LEN - stimDur);
                    oneCycle();            // cycle suivant
                }}
            }}, maskDur);
        }}, stimDur);
    }}
    oneCycle();  // lancement du premier cycle (14 ms + 336 ms)

    // ---------- Détection de l’appui sur ESPACE ----------
    function onSpace(ev) {{
        if (ev.code === "Space" && running) {{
            running = false;                       // stoppe la boucle mot/masque
            let RT  = performance.now() - t0;      // calcul du temps de réaction
            disp.textContent = "";                 // on efface l’écran
            respBox.style.display = "block";       // le champ réponse apparaît
            respBox.value = "";
            respBox.focus();
            window.removeEventListener('keydown', onSpace);

            // ---------- Validation par ENTREE ----------
            respBox.addEventListener('keydown', function onEnter(e) {{
                if (e.key === "Enter") {{
                    e.preventDefault();
                    let typed = respBox.value.trim();
                    results.push({{word: word, rt: Math.round(RT), response: typed}});
                    respBox.style.display = "none";
                    respBox.removeEventListener('keydown', onEnter);
                    index += 1;
                    runTrial();             // mot suivant
                }}
            }});
        }}
    }}
    window.addEventListener('keydown', onSpace);
}}

//////////////////////////////////////////////////////////////////////
// FIN D’EXPÉRIENCE : export CSV + envoi à Streamlit
//////////////////////////////////////////////////////////////////////
function endExp() {{
    disp.style.fontSize = "32px";
    disp.textContent    = "Merci, l’expérience est terminée !";
    // Génération d’un CSV téléchargeable
    let header  = "word,rt_ms,response\\n";
    let rows    = results.map(r => `${{r.word}},${{r.rt}},${{r.response}}`).join("\\n");
    let blob    = new Blob([header+rows], {{type: 'text/csv'}});
    let url     = URL.createObjectURL(blob);
    let aLink   = document.createElement('a');
    aLink.href  = url;
    aLink.download = "results.csv";
    aLink.textContent = "Télécharger les résultats";
    aLink.style.display = "block";
    aLink.style.marginTop = "25px";
    document.body.appendChild(aLink);

    // Envoi des données à Streamlit (visible dans st.session_state)
    const msg = {{type: "results", payload: results}};
    window.parent.postMessage({{isStreamlitMessage:true, ...msg }}, "*");
}}

// ------------------------- ON LANCE L’EXPERIENCE -----------------------------
runTrial();
</script>
</body>
</html>
"""

###############################################################################
# 4. RENDER HTML IN STREAMLIT
###############################################################################
components.html(html_code, height=400, scrolling=False)
