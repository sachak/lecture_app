# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JavaScript)
– Zone de saisie visible seulement après Espace, supprimée après Entrée.
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───────── PARAMÈTRES ────────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───────── ÉTAT SESSION ──────────────────────────────────────────────
s = st.session_state
if "stage" not in s:              # première exécution
    s.stage   = "intro"           # intro ▸ trial ▸ end
    s.idx     = 0                 # index du mot courant
    s.phase   = "js"              # js ▸ typing
    s.rt_ms   = None
    s.answer_ready = False        # flag déclenché par on_change
    s.results = []

# ───────── CHAMP CACHÉ (réception JS → Python) ───────────────────────
def hidden_receiver():
    st.markdown("<style>#receiver{display:none;}</style>", unsafe_allow_html=True)
    st.text_input("", key="receiver", label_visibility="collapsed")

# ───────── COMPOSANT JS (mot/masque) ─────────────────────────────────
def demask_component(word: str, i: int):
    mask = MASK_CHAR * len(word)
    html = f"""
<div id="stim" style="font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD  = "{word}";
const MASK  = "{mask}";
const CYCLE = {CYCLE_MS};
const STEP  = {STEP_MS};

let start = performance.now();
let stop  = false;
let rafID = null;
const div = document.getElementById("stim");

function flip(ts) {{
  if(stop) return;
  const el   = ts - start;
  const idx  = Math.floor(el / CYCLE);
  const dur  = Math.min(STEP*(idx+1), CYCLE);
  div.textContent = (el % CYCLE) < dur ? WORD : MASK;
  rafID = requestAnimationFrame(flip);
}}
rafID = requestAnimationFrame(flip);

function finish() {{
  stop = true;
  cancelAnimationFrame(rafID);
  div.textContent = "";
  div.style.display = "none";
  const rt = Math.round(performance.now() - start);
  const hidden = window.parent.document.getElementById("receiver");
  if(hidden){{
      hidden.value = JSON.stringify({{idx:{i}, rt:rt}});
      hidden.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}
}}

document.addEventListener('keydown', e=>{
  if(e.code==='Space' || e.key===' ') finish();
}});
</script>
"""
    components.html(html, height=400, scrolling=False)

# ───────── CALLBACK : validation de la réponse -----------------------
def on_answer():
    s.answer_ready = True          # déclenche le traitement dans page_trial

# ───────── PAGE INTRO ------------------------------------------------
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown(
        "Cliquez sur **Démarrer**. Un mot se dévoile progressivement ; "
        "appuyez sur la **barre Espace** dès que vous l’avez reconnu. "
        "Tapez alors le mot et validez par **Entrée**."
    )
    if st.button("Démarrer"):
        s.stage, s.phase = "trial", "js"
        st.rerun()

# ───────── PAGE TRIAL : un essai -------------------------------------
def page_trial():
    if s.idx >= len(STIMULI):
        s.stage = "end"; st.rerun(); return

    word = STIMULI[s.idx]
    hidden_receiver()
    msg = s.get("receiver", "")

    # ---- Phase 1 : présentation JS ----
    if s.phase == "js":
        demask_component(word, s.idx)
        if msg.startswith("{"):
            dat = json.loads(msg)
            s.rt_ms      = dat["rt"]
            s.phase      = "typing"
            s["receiver"] = ""           # reset champ caché
            st.rerun()

    # ---- Phase 2 : saisie du mot ----
    elif s.phase == "typing":
        st.write(f"Temps de réaction : **{s.rt_ms} ms**")

        key_answer = f"answer_{s.idx}"
        st.text_input("Tapez le mot reconnu puis Entrée :",
                      key=key_answer, on_change=on_answer)

        # Si la réponse vient d'être validée ---------------------------
        if s.answer_ready:
            typed = st.session_state.get(key_answer, "")
            s.answer_ready = False

            # Enregistrer le résultat
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = typed.upper() == word,
                rt_ms    = s.rt_ms
            ))

            # Nettoyer : supprimer le champ de réponse
            if key_answer in st.session_state:
                del st.session_state[key_answer]

            # Préparer essai suivant
            s.idx  += 1
            s.phase = "js"
            st.rerun()

# ───────── PAGE FIN ---------------------------------------------------
def page_end():
    st.title("Expérience terminée – merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Télécharger les résultats (.csv)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───────── ROUTAGE GLOBAL --------------------------------------------
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.stage]()
