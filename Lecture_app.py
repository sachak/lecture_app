# -*- coding: utf-8 -*-
"""
Expérience 3 – Progressive-demasking (Streamlit + JS)
Stimulus retiré dès l’appui sur <Espace>.
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as components

# ───── paramètres généraux ──────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK_CHAR = 350, 14, "#"

STIMULI = [
    "AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI","NAGER","PARLE",
    "PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE","TABLE","TIGRE","VIVRE","VOILE",
    "ATOUT","BALLE","CANNE","CHIEN","FABLE","GELER","METRE","NAVET","PAGNE","PLAGE",
    "REGLE","RIVET","SAUTE","SOURD","TITRE","VALSE","VOYOU","AMBRE","BASIN","GLACE"
]
random.shuffle(STIMULI)

# ───── état session ────────────────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page, s.i, s.wait_js, s.typing, s.rt, s.results = "intro", 0, False, False, None, []

# ───── composant récepteur (JS → Python) ───────────────────────────
def receiver():
    components.html(
        """
<script>
window.addEventListener("message", evt =>{
  if(evt.data && evt.data.source === "demask"){
      const target = window.parent.document.getElementById("receiver_input");
      if(target){
         target.value = JSON.stringify(evt.data);
         target.dispatchEvent(new Event('input',{bubbles:true}));
      }
  }
});
</script>
""", height=0)

# ───── composant stimulus avec retrait immédiat ────────────────────
def demask(word: str):
    mask = MASK_CHAR * len(word)
    html = f"""
<div id="stim" style="font-size:64px;text-align:center;font-family:monospace;margin-top:25vh;"></div>

<script>
const WORD     = "{word}";
const MASK     = "{mask}";
const CYCLE_MS = {CYCLE_MS};
const STEP_MS  = {STEP_MS};

let t0   = performance.now();
let div  = document.getElementById("stim");
let quit = false;                        // devient true après <Espace>

/* boucle frame-lockée */
function flip(ts){{
   if(quit) return;                      // on a déjà appuyé Espace
   const e = ts - t0;
   const idx = Math.floor(e/CYCLE_MS);
   const stimDur = Math.min(STEP_MS*(idx+1), CYCLE_MS);
   const show = (e % CYCLE_MS) < stimDur;
   div.textContent = show ? WORD : MASK;
   requestAnimationFrame(flip);
}}
requestAnimationFrame(flip);

/* appui Espace = réponse + effacement */
window.addEventListener("keydown", ev=>{
    if(ev.code === "Space" && !quit){{
        quit = true;
        div.textContent = "";                    // ① efface le mot/masque
        const rt = performance.now() - t0;
        window.parent.postMessage({{             // ② envoie RT
            source:"demask", word:WORD, rt:Math.round(rt)
        }},"*");
    }}
});
</script>
"""
    components.html(html, height=400, scrolling=False)

# ───── pages ───────────────────────────────────────────────────────
def intro():
    st.title("Tâche de dévoilement progressif – en ligne")
    st.markdown("""
Appuyez sur **Démarrer**. Le mot se dévoilera peu à peu ; appuyez sur la
**barre Espace** dès que vous l’avez reconnu, puis saisissez-le.
""")
    if st.button("Démarrer"):
        s.page, s.wait_js = "trial", True
        st.rerun()

def trial():
    if s.i >= len(STIMULI):
        s.page = "end"; st.rerun(); return
    word = STIMULI[s.i]

    if s.wait_js:                               # phase JS active
        receiver()
        demask(word)
        msg = st.text_input("", key="receiver_input",
                            label_visibility="collapsed")
        if msg:
            data = json.loads(msg)
            s.rt = data["rt"]
            s.wait_js, s.typing = False, True
            s["receiver_input"] = ""
            st.rerun()

    elif s.typing:                              # saisie du mot
        st.write(f"Temps de réaction : **{s.rt} ms**")
        typed = st.text_input("Tapez le mot reconnu :", key=f"t_{s.i}")
        if typed:
            s.results.append(dict(stimulus=word,
                                   response=typed.upper(),
                                   correct=(typed.upper()==word),
                                   rt_ms=s.rt))
            s.i += 1
            s.wait_js, s.typing = True, False
            st.rerun()

def end():
    st.title("Expérience terminée, merci !")
    df = pd.DataFrame(s.results)
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Télécharger CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"demask_{uuid.uuid4()}.csv",
        mime="text/csv")
    st.success("Vous pouvez fermer l’onglet.")

# ───── routage ─────────────────────────────────────────────────────
{"intro": intro, "trial": trial, "end": end}[s.page]()
