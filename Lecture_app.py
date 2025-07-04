# -*- coding: utf-8 -*-
"""
Expérience 3 – Progressive-demasking 100 % web
© 2024 – libre de droits pour usage pédagogique
"""
import json, random, time, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components


# ───────── PARAMÈTRES GÉNÉRAUX ──────────────────────────────────────────────
CYCLE_MS = 350      # durée fixe d’un cycle (ms)
STEP_MS  = 14       # +14 ms d’affichage mot / –14 ms masque
MASK_CH  = "#"      # caractère du masque

# Liste exemple (remplacez par vos 80 stimuli réels)
STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───────── INITIALISATION ÉTAT SESSION ──────────────────────────────────────
def init_state():
    s = st.session_state
    s.setdefault("page", "intro")
    s.setdefault("trial", 0)            # index stimulus courant
    s.setdefault("waiting_js", False)   # composant JS actif ?
    s.setdefault("typing", False)       # on attend la saisie du mot
    s.setdefault("rt_ms", None)         # RT du dernier essai
    s.setdefault("results", [])         # liste de dicts
init_state()


# ───────── HTML ÉCOUTEUR (réception message JS → Streamlit) ─────────────────
def receiver_component():
    components.html(
        """
<script>
/* Écoute les messages provenant de l’iframe du stimulus */
window.addEventListener("message", (evt)=>{
  if(evt.data && evt.data.source === "demask"){
     const hidden = window.parent.document.getElementById("demask_receiver");
     if(hidden){
        hidden.value = JSON.stringify(evt.data);
        hidden.dispatchEvent(new Event('input', {bubbles:true}));
     }
  }
});
</script>
""",
        height=0,
    )


# ───────── HTML STIMULUS PROGRESSIVE DEMASKING (JS) ─────────────────────────
def demask_component(word):
    """Retourne le code HTML/JS qui fait :
       - alterner mot / masque (+14 ms par cycle)
       - écouter la barre espace (reconnaissance)
       - envoyer {word, rt} au parent (Streamlit)"""
    mask = MASK_CH * len(word)
    html = f"""
<div id="stim" style="font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;">
</div>

<script>
const word     = "{word}";
const mask     = "{mask}";
const cycle_ms = {CYCLE_MS};
const step_ms  = {STEP_MS};

let start = performance.now();
const stimDiv = document.getElementById("stim");

/* Boucle d’animation frame-lockée */
function flip(ts){{
   const elapsed   = ts - start;
   const cycleIdx  = Math.floor(elapsed / cycle_ms);
   const stim_dur  = Math.min(step_ms * (cycleIdx+1), cycle_ms);
   const inCycle   = elapsed % cycle_ms;
   const showWord  = inCycle < stim_dur;
   stimDiv.textContent = showWord ? word : mask;
   requestAnimationFrame(flip);
}}
requestAnimationFrame(flip);

/* Réponse : barre espace */
window.addEventListener("keydown", (e)=>{
   if(e.code === "Space"){{
       const rt = performance.now() - start;
       window.parent.postMessage({{source:"demask",
                                   word:word,
                                   rt:Math.round(rt)}}, "*");
   }}
}});
</script>
"""
    components.html(html, height=400, scrolling=False)


# ───────── PAGE INTRO ────────────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif (en ligne)")
    st.markdown("""
Appuyez sur **Démarrer** pour lancer l’expérience.  
Regardez le mot apparaître progressivement ; dès que vous l’avez reconnu,
appuyez sur la **barre espace**.  
Vous taperez ensuite le mot que vous avez vu.
""")
    if st.button("Démarrer"):
        st.session_state.page = "trial"
        st.session_state.waiting_js = True
        st.rerun()


# ───────── PAGE TRIAL (une tentative) ───────────────────────────────────────
def page_trial():
    i = st.session_state.trial
    if i >= len(STIMULI):
        st.session_state.page = "end"
        st.rerun()
        return

    word = STIMULI[i]

    # 1) Stimulus JS actif
    if st.session_state.waiting_js:
        receiver_component()            # écouteur de messages
        demask_component(word)          # stimulus dans un iframe

        # input caché qui recevra le JSON {word, rt}
        hidden = st.text_input("", key="demask_receiver",
                               label_visibility="collapsed")
        if hidden:                      # un message vient d'arriver
            try:
                data = json.loads(hidden)
                st.session_state.rt_ms = data["rt"]
            except Exception:
                st.stop()
            st.session_state.waiting_js = False
            st.session_state.typing     = True
            st.session_state["demask_receiver"] = ""   # reset
            st.rerun()

    # 2) Demande de saisie du mot reconnu
    elif st.session_state.typing:
        st.write(f"Temps de réaction : **{st.session_state.rt_ms} ms**")
        typed = st.text_input(
            "Tapez le mot reconnu puis appuyez sur Entrée :",
            key=f"in_{i}"
        )
        if typed:
            st.session_state.results.append({
                "stimulus" : word,
                "response" : typed.upper(),
                "rt_ms"    : st.session_state.rt_ms,
                "correct"  : typed.upper() == word
            })
            # Préparation essai suivant
            st.session_state.trial      += 1
            st.session_state.waiting_js  = True
            st.session_state.typing      = False
            st.rerun()


# ───────── PAGE FIN ─────────────────────────────────────────────────────────
def page_end():
    st.title("Expérience terminée, merci !")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Télécharger les résultats (.csv)",
                       csv, file_name=f"demasking_{uuid.uuid4()}.csv",
                       mime="text/csv")
    st.success("Vous pouvez maintenant fermer l’onglet.")


# ───────── ROUTAGE PRINCIPAL ────────────────────────────────────────────────
page = st.session_state.page
if   page == "intro":  page_intro()
elif page == "trial":  page_trial()
else:                  page_end()
