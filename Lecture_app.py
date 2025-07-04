# -*- coding: utf-8 -*-
"""
Progressive-demasking (Streamlit + JS)
• Aucune zone de réponse avant Espace
• Zone supprimée juste après Entrée
"""
import json, random, uuid, pandas as pd, streamlit as st
import streamlit.components.v1 as cpn

# ─── paramètres ─────────────────────────────────────────────
CYCLE_MS, STEP_MS, MASK = 350, 14, "#"
WORDS = ["AVION","BALAI","CARTE","CHAUD","CRANE","GARDE","LIVRE","MERCI",
         "NAGER","PARLE","PORTE","PHOTO","RADIO","ROULE","SALON","SUCRE",
         "TABLE","TIGRE","VIVRE","VOILE"]
random.shuffle(WORDS)

# ─── état session ──────────────────────────────────────────
s = st.session_state
if "page" not in s:
    s.page, s.idx, s.phase = "intro", 0, "js"   # phases : js ▸ typing
    s.rt, s.data           = None, []
    s.box                  = st.empty()         # placeholder permanent

# ─── champ caché JS → Python (invisible) ──────────────────
st.markdown("<style>#receiver{display:none}</style>", unsafe_allow_html=True)
hidden = st.text_input("", key="receiver", label_visibility="collapsed")

# ─── gabarit JS (accolades doublées) ──────────────────────
JS_TPL = """
<div id='stim' style='font-size:64px;text-align:center;
                      font-family:monospace;margin-top:25vh;'></div>
<script>
const WORD  = "{w}";
const MASK  = "{m}";
const CYCLE = {c};
const STEP  = {s};

let start = performance.now();
let stop  = false;
let rafID = null;
const div = document.getElementById('stim');

function flip(ts) {{
  if(stop) return;
  const e = ts - start;
  const i = Math.floor(e / CYCLE);
  const d = Math.min(STEP * (i + 1), CYCLE);
  div.textContent = (e % CYCLE) < d ? WORD : MASK;
  rafID = requestAnimationFrame(flip);
}}
rafID = requestAnimationFrame(flip);

function finish() {{
  stop = true;
  cancelAnimationFrame(rafID);
  div.remove();
  const rt = Math.round(performance.now() - start);
  const tgt = window.parent.document.getElementById('receiver');
  if(tgt) {{
      tgt.value = JSON.stringify({{rt: rt}});
      tgt.dispatchEvent(new Event('input', {{bubbles: true}}));
  }}
}}

document.addEventListener('keydown', e => {{
  if(e.code === 'Space' || e.key === ' ') finish();
}});
</script>
""".replace("{","{{").replace("}","}}")  # on double toutes les accolades
# puis on remet les champs utiles (w,m,c,s) en simple accolade
JS_TPL = JS_TPL.replace("{{w}}","{w}").replace("{{m}}","{m}") \
               .replace("{{c}}","{c}").replace("{{s}}","{s}")

def show_js(word: str):
    html = JS_TPL.format(w=word,
                         m=MASK*len(word),
                         c=CYCLE_MS,
                         s=STEP_MS)
    cpn.html(html, height=400, scrolling=False)

# ─── pages ────────────────────────────────────────────────
def page_intro():
    st.title("Tâche de dévoilement progressif")
    st.write("1. Le mot se dévoile progressivement.\n"
             "2. Appuyez sur **Espace** dès que vous le reconnaissez.\n"
             "3. Tapez le mot puis **Entrée**.")
    if st.button("Démarrer"):
        s.page, s.phase = "trial", "js"
        st.experimental_rerun()

def page_trial():
    if s.idx >= len(WORDS):
        s.page = "end"; st.experimental_rerun(); return
    word = WORDS[s.idx]

    if s.phase == "js":
        s.box.empty()                # aucun champ visible
        show_js(word)
        if hidden.startswith("{"):
            s.rt = json.loads(hidden)["rt"]
            s.receiver = ""
            s.phase = "typing"
            st.experimental_rerun()

    elif s.phase == "typing":
        st.write(f"RT : **{s.rt} ms**")
        answer = s.box.text_input("Votre réponse :", key=f"ans_{s.idx}")
        if answer:                   # Entrée
            s.data.append(dict(
                stimulus = word,
                response = answer.upper(),
                correct  = answer.upper()==word,
                rt_ms    = s.rt))
            # nettoyage
            s.box.empty()
            del st.session_state[f"ans_{s.idx}"]
            s.idx  += 1
            s.phase = "js"
            st.experimental_rerun()

def page_end():
    st.title("Merci !")
    df = pd.DataFrame(s.data)
    st.dataframe(df, use_container_width=True)
    st.download_button("💾 CSV",
                       df.to_csv(index=False).encode(),
                       file_name=f"demask_{uuid.uuid4()}.csv",
                       mime="text/csv")

# ─── routage ─────────────────────────────────────────────
{"intro": page_intro,
 "trial": page_trial,
 "end":   page_end}[s.page]()
