# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JS)
– Zone de saisie réellement absente avant <Espace>
– Zone supprimée juste après validation <Entrée>
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───── Paramètres ────────────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"
WORDS = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE"
]
random.shuffle(WORDS)

# ───── État de session ───────────────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page = "intro"             # intro ▸ trial ▸ end
    s.i    = 0                   # index du mot
    s.rt   = None
    s.show_box = False           # faut-il afficher la zone ?
    s.answer_ready = False
    s.results = []
    s.box_ph = st.empty()        # placeholder permanent pour la zone

# ───── Champ caché pour recevoir le RT depuis JS ─────────────────────
st.markdown("<style>#receiver{display:none;}</style>", unsafe_allow_html=True)
hidden = st.text_input("", key="receiver", label_visibility="collapsed")

# ───── JavaScript (sans accolade à échapper) ─────────────────────────
JS_TEMPLATE = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>
<script>
const WORD  = "%%WORD%%";
const MASK  = "%%MASK%%";
const CYCLE = %%CYCLE%%;
const STEP  = %%STEP%%;
let start = performance.now(), stop=false;
const div = document.getElementById('stim');
let rafID = null;

function flip(ts){
  if(stop) return;
  const e = ts - start,
        i = Math.floor(e/CYCLE),
        d = Math.min(STEP*(i+1), CYCLE);
  div.textContent = (e % CYCLE) < d ? WORD : MASK;
  rafID = requestAnimationFrame(flip);
}
rafID = requestAnimationFrame(flip);

function finish(){
  stop = true;
  cancelAnimationFrame(rafID);
  div.textContent  = "";
  div.style.display= "none";
  const rt = Math.round(performance.now()-start);
  const tgt = window.parent.document.getElementById('receiver');
  if(tgt){
      tgt.value = JSON.stringify({rt:rt});
      tgt.dispatchEvent(new Event('input',{bubbles:true}));
  }
}
document.addEventListener('keydown', e=>{
  if(e.code==='Space' || e.key===' ') finish();
});
</script>
"""

def show_js(word:str):
    html = (JS_TEMPLATE
            .replace("%%WORD%%", word)
            .replace("%%MASK%%", MASK_CHAR*len(word))
            .replace("%%CYCLE%%", str(CYCLE_MS))
            .replace("%%STEP%%",  str(STEP_MS)))
    components.html(html, height=400, scrolling=False)

# ───── Callback : Entrée dans la zone de réponse ─────────────────────
def on_validate():
    s.answer_ready = True

# ───── PAGES ─────────────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.write("• Le mot se dévoile peu à peu.\n"
             "• Appuyez sur **Espace** dès que vous l’avez reconnu.\n"
             "• Tapez le mot et validez par **Entrée**.")
    if st.button("Démarrer"):
        s.page = "trial"
        s.show_box = False
        st.experimental_rerun()

def page_trial():
    # Si zone de réponse ne doit pas être visible → on s’assure qu’elle est vide
    if not s.show_box:
        s.box_ph.empty()

    # Fin d’expérience ?
    if s.i >= len(WORDS):
        s.page = "end"; st.experimental_rerun(); return

    word = WORDS[s.i]

    # Étape 1 : affichage / attente barre espace
    if not s.show_box:
        show_js(word)

    # Le JS vient-il d’envoyer le RT ?
    if hidden.startswith("{") and not s.show_box:
        s.rt       = json.loads(hidden)["rt"]
        s.receiver = ""          # reset
        s.show_box = True
        st.experimental_rerun()

    # Étape 2 : affichage de la zone de saisie
    if s.show_box:
        st.write(f"Temps de réaction : **{s.rt} ms**")
        s.box_ph.text_input("Votre réponse :", key=f"ans_{s.i}",
                            on_change=on_validate)

        # Après validation (Entrée)
        if s.answer_ready:
            typed = s.get(f"ans_{s.i}", "")
            s.answer_ready = False
            s.results.append(dict(
                stimulus = word,
                response = typed.upper(),
                correct  = typed.upper() == word,
                rt_ms    = s.rt
            ))
            # Nettoyage
            if f"ans_{s.i}" in s:
                del s[f"ans_{s.i}"]
            s.box_ph.empty()
            s.i += 1
            s.show_box = False
            st.experimental_rerun()

def page_end():
    st.title("Merci pour votre participation !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Télécharger les résultats",
                       df.to_csv(index=False).encode("utf-8"),
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───── Routage ───────────────────────────────────────────────────────
{"intro": page_intro, "trial": page_trial, "end": page_end}[s.page]()
