# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Tâche de reconnaissance de mots masqués
(familiarisation + test 80 mots)

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
from streamlit import components

# ────────────────────────── OUTIL RERUN ────────────────────────────────────
def do_rerun():
    st.session_state.rerun = True   # « drapeau » pour Streamlit ≥ 1.25
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ───────────────────────── CONFIG STREAMLIT ────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
.css-1d391kg {display:none;}          /* ancien spinner Streamlit           */
</style>""", unsafe_allow_html=True)

# =============================================================================
# 1. PARAMÈTRES DU TIRAGE
# =============================================================================
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = {"letters": .68, "phons": .68}
SD_MULT            = {"letters": 2, "phons": 2,
                      "old20": .28, "pld20": .28, "freq": 1.9}
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1_000
MAX_TRY_FULL    = 1_000
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# =============================================================================
# 2. OUTILS DIVERS
# =============================================================================
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str)
                           .str.replace(" ",  "", regex=False)
                           .str.replace("\xa0","", regex=False)
                           .str.replace(",", ".", regex=False),
                         errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int:    # -1 = LOW ; +1 = HIGH
    return -1 if "LOW" in tag else 1

# =============================================================================
# 3. CHARGEMENT EXCEL + TIRAGE DES 80 MOTS
# =============================================================================
@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable."); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheet_names = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheet_names) != 4:
        st.error("Il faut exactement 4 feuilles nommées Feuil1 … Feuil4."); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheet_names:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        freq_cols = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(freq_cols)
        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for col in NUM_BASE + freq_cols:
            df[col] = to_float(df[col])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()           for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0)    for c in ("old20","pld20","nblettres","nbphons") + tuple(freq_cols)}
        feuilles[sh] = {"df": df, "stats": stats, "freq_cols": freq_cols}

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

def masks(df, st_):
    return {"LOW_OLD":  df.old20 < st_["m_old20"] - st_["sd_old20"],
            "HIGH_OLD": df.old20 > st_["m_old20"] + st_["sd_old20"],
            "LOW_PLD":  df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
            "HIGH_PLD": df.pld20 > st_["m_pld20"] + st_["sd_pld20"]}

def sd_ok(sub, st_, fq_cols):
    return (sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
            sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
            sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
            sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
            all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq_cols))

def mean_lp_ok(sub, st_):
    return (abs(sub.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(sub.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fqs = F[feuille]["freq_cols"]
    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fqs): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F = load_sheets(); all_freq_cols = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken = {sh:set() for sh in F if sh!="all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            parts=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                parts.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(parts, ignore_index=True)))
        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq_cols + ["source","group","old_cat","pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste (contraintes trop strictes)."); st.stop()

# =============================================================================
# 4. GÉNÉRATION HTML / JS
# =============================================================================
HTML_TPL = Template(r"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;display:flex;flex-direction:column;
          align-items:center;justify-content:center;font-family:'Courier New',monospace}
#scr{font-size:60px;user-select:none}
#ans{display:none;font-size:48px;width:60%;text-align:center}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
window.addEventListener("load",()=>document.body.focus());
const WORDS = $WORDS;
const CYCLE = $CYCLE;
const START = $START;
const STEP  = $STEP;

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

function nextTrial(){
  if(trial >= WORDS.length){ endExperiment(); return; }
  const w = WORDS[trial];
  const mask = "#".repeat(w.length);

  let showDur = START;
  let hideDur = CYCLE - showDur;
  let tShow, tHide;
  const t0 = performance.now();
  let active = true;

  (function loop(){
    if(!active) return;
    scr.textContent = w;
    tShow = setTimeout(()=>{ if(!active) return;
      scr.textContent = mask;
      tHide = setTimeout(()=>{ if(active){
          showDur += STEP;
          hideDur = Math.max(0, CYCLE - showDur);
          loop();
      }}, hideDur);
    }, showDur);
  })();

  function onSpace(e){
    if(e.code === "Space" && active){
      active = false;
      clearTimeout(tShow); clearTimeout(tHide);
      const rt = Math.round(performance.now() - t0);
      window.removeEventListener("keydown", onSpace);
      scr.textContent = "";
      ans.style.display = "block"; ans.value = ""; ans.focus();
      ans.addEventListener("keydown", function onEnter(ev){
        if(ev.key==="Enter"){
          ev.preventDefault();
          results.push({word:w, rt_ms:rt, response:ans.value.trim()});
          ans.removeEventListener("keydown", onEnter);
          ans.style.display = "none";
          trial += 1; nextTrial();
        }
      });
    }
  }
  window.addEventListener("keydown", onSpace);
}

function endExperiment(){
  scr.style.fontSize = "40px";
  scr.textContent = $END_MSG;
  $DOWNLOAD
}
$STARTER              /* ► code qui lance l’expérience               */
</script>
</body>
</html>
""")

def experiment_html(words, *, with_download=True,
                    cycle_ms=350, start_ms=14, step_ms=14,
                    fullscreen=False):
    """Construit la page HTML de l’expérience."""
    # Bloc téléchargement (optionnel) -------------------------------------------------
    download_js = ""
    if with_download:
        download_js = r"""
const csv = ["word;rt_ms;response",
             ...results.map(r => `${r.word};${r.rt_ms};${r.response}`)].join("\n");
const a = document.createElement("a");
a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
a.download = "results.csv";
a.textContent = "Télécharger les résultats";
a.style.fontSize = "32px";
a.style.marginTop = "30px";
document.body.appendChild(a);"""
    download_js = download_js.replace("$","$$")    # échapper les $

    # Code de démarrage --------------------------------------------------------------
    if fullscreen:
        starter_js = r"""
scr.textContent = "Appuyez sur la barre ESPACE pour commencer";
function firstKey(e){
    if(e.code==="Space"){
        window.removeEventListener("keydown", firstKey);
        document.documentElement.requestFullscreen?.();
        nextTrial();
    }
}
window.addEventListener("keydown", firstKey);"""
    else:
        starter_js = "nextTrial();"

    html = HTML_TPL.substitute(
        WORDS=json.dumps(words),
        CYCLE=cycle_ms,
        START=start_ms,
        STEP=step_ms,
        END_MSG=json.dumps("Merci !" if with_download else "Fin de l’entraînement"),
        DOWNLOAD=download_js,
        STARTER=starter_js
    )
    return html

# =============================================================================
# 5. NAVIGATION / ÉTATS STREAMLIT
# =============================================================================
if "page"        not in st.session_state: st.session_state.page        = "intro"
if "tirage_ok"   not in st.session_state: st.session_state.tirage_ok   = False
if "tirage_run"  not in st.session_state: st.session_state.tirage_run  = False
if "exp_started" not in st.session_state: st.session_state.exp_started = False

# ─────────────────────────── PAGE INTRO ────────────────────────────────────
if st.session_state.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")
    st.markdown("""
**Principe**  
Des mots sont présentés très brièvement, suivis d’un masque (suite de “#”).

**Votre tâche**  
• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.

1. Entraînement (2 mots)  2. Test principal (80 mots)
""")

    # tirage automatique au premier affichage
    if not st.session_state.tirage_run and not st.session_state.tirage_ok:
        st.session_state.tirage_run = True; do_rerun()

    if st.session_state.tirage_run and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet()
            mots = df["ortho"].tolist(); random.shuffle(mots)
            st.session_state.tirage_df = df
            st.session_state.stimuli   = mots
            st.session_state.tirage_ok = True
            st.session_state.tirage_run = False
        st.success("Tirage terminé !")

    if st.session_state.tirage_ok:
        if st.button("Commencer la familiarisation"):
            st.session_state.page = "fam"; do_rerun()

# ───────────────────────── PAGE FAMILIARISATION ────────────────────────────
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** dès que le mot apparaît, tapez-le puis **Entrée**.")
    components.v1.html(
        experiment_html(PRACTICE_WORDS, with_download=False),
        height=650, scrolling=False
    )
    st.divider()
    if st.button("Passer au test principal"):
        st.session_state.page = "exp"
        st.session_state.exp_started = False   # on n'a pas encore lancé le test
        do_rerun()

# ────────────────────────── PAGE TEST PRINCIPAL ────────────────────────────
elif st.session_state.page == "exp":
    # 1) écran d’attente + bouton
    if not st.session_state.exp_started:
        st.header("Test principal : 80 mots")
        with st.expander("Aperçu des statistiques du tirage"):
            st.dataframe(st.session_state.tirage_df.head())
        st.markdown("Quand vous êtes prêt·e, cliquez sur **Commencer le test**. "
                    "La fenêtre passera alors en plein écran.")
        if st.button("Commencer le test"):
            st.session_state.exp_started = True
            do_rerun()
    # 2) test proprement dit : on n’affiche plus que l’iframe
    else:
        components.v1.html(
            experiment_html(st.session_state.stimuli,
                            with_download=True,
                            fullscreen=True),
            height=700, scrolling=False
        )
