# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
Version responsive plein-écran (zéro scroll)

Exécution :  streamlit run exp3_responsive.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
from pathlib import Path
import inspect, random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ────────────────────────── utilitaire « re-run » ─────────────────────────
def _rerun():  (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ───────────────────── configuration générale (plein-écran) ──────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
html,body,.stApp          {height:100%; margin:0; overflow:hidden;}
main.block-container       {padding:0;}                 /* supprime marge centre */
#MainMenu,header,footer    {visibility:hidden;}         /* cache menu & footer  */
button:disabled            {opacity:.45!important; cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── état de session ──────────────────────────────
for k, v in dict(page="screen_test", hz_val=None,
                 tirage_running=False, tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state
def go(pg:str):  p.page = pg; _rerun()

# ────────────────── constantes & fonctions de tirage (inchangées) ────────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = MAX_TRY_FULL = 1_000
rng             = random.Random()
NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]

def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[  ,]", "", regex=True)     # espaces insécables etc.
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag:str) -> int:  return -1 if "LOW" in tag else 1

@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error("Fichier « Lexique.xlsx » introuvable"); st.stop()

    xls    = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets) != 4:
        st.error("Le classeur doit contenir exactement 4 feuilles Feuil1…Feuil4")
        st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheets:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()

        fq = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(fq)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + fq
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for c in NUM_BASE + fq:
            df[c] = to_float(df[c])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df          = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in
                 ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in
                  ("old20", "pld20", "nblettres", "nbphons") + tuple(fq)}

        feuilles[sh] = dict(df=df, stats=stats, freq_cols=fq)

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

def masks(df, st_) -> dict[str, pd.Series]:
    return dict(
        LOW_OLD  = df.old20 < st_["m_old20"] - st_["sd_old20"],
        HIGH_OLD = df.old20 > st_["m_old20"] + st_["sd_old20"],
        LOW_PLD  = df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
        HIGH_PLD = df.pld20 > st_["m_pld20"] + st_["sd_pld20"])

def sd_ok(sub, st_, fq) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq))

def mean_lp_ok(s, st_) -> bool:
    return (
        abs(s.nblettres.mean() - st_["m_nblettres"])
            <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(s.nbphons.mean()  - st_["m_nbphons"])
            <= MEAN_DELTA["phons"]   * st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]

    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fq):
            continue

        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F        = load_sheets()
    all_freq = F["all_freq_cols"]

    for _ in range(MAX_TRY_FULL):
        taken  = {sh:set() for sh in F if sh != "all_freq_cols"}
        groups = []; ok = True

        for tag in TAGS:
            bloc = []
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok = False; break
                bloc.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq + \
                    ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    st.error("Impossible de générer la liste."); st.stop()

# ────────────────────────── composant HTML plein-écran ───────────────────
def full_html(body:str, *, key:str|None=None, height:int=200):
    """
    Place un composant HTML occupant 100 % de la fenêtre.
    Ajoute key uniquement si la version de Streamlit l'accepte.
    """
    html_doc = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
    <style>html,body{{height:100%;margin:0;overflow:hidden;}}</style></head>
    <body>{body}
    <script>
      function resize(){{Streamlit.setFrameHeight(window.innerHeight);}}
      window.addEventListener("load",resize);
      window.addEventListener("resize",resize);
      Streamlit.setComponentReady();
    </script></body></html>"""

    kwargs = dict(height=height, scrolling=False)
    if key and "key" in inspect.signature(components.html).parameters:
        kwargs["key"] = key
    return components.html(html_doc, **kwargs)

# ────────────────────────── test fréquence (HTML) ────────────────────────
TEST_HTML_BODY = r"""
<h2 style="font-size:6vw;margin:0 0 2vh">Test de fréquence</h2>
<div id="res" style="font-size:8vw;margin:4vh 0">--</div>
<button id="go"  style="font-size:4vw;padding:1vh 4vw" onclick="mesure()">Démarrer</button>
<button id="next" style="display:none;font-size:4vw;padding:1vh 4vw;margin-top:2vh"
        onclick="next()">Suivant ➜</button>
<script>
let hzVal=null;
function mesure(){
  const res=document.getElementById('res'), go=document.getElementById('go');
  go.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0,t0=performance.now();
  function loop(){
    f++; if(f<120){requestAnimationFrame(loop);}
    else{
      const hz=f*1000/(performance.now()-t0);
      hzVal=hz.toFixed(1);
      const good=Math.abs(hz-60)<1.5;
      res.textContent='≈ '+hzVal+' Hz';
      res.style.color = good?'lime':'red';
      document.getElementById('next').style.display = good?'inline-block':'none';
      Streamlit.setComponentValue(hzVal);
      go.disabled=false;
    }}
  requestAnimationFrame(loop);
}
function next(){ Streamlit.setComponentValue('NEXT'); }
</script>"""

COMMERCIAL = [60, 75, 90, 120, 144]
def nearest_hz(x: float) -> int: return min(COMMERCIAL, key=lambda v:abs(v-x))

# ─────────────────────────────── PAGES ───────────────────────────────────
# 0 — Test fréquence
if p.page == "screen_test":

    st.markdown("## 1. Vérification (facultative) de la fréquence d’écran",
                unsafe_allow_html=True)

    val = full_html(TEST_HTML_BODY, key="hz_test")

    if isinstance(val, str) and val == "NEXT":
        if p.hz_val is None or nearest_hz(p.hz_val) != 60:
            st.error("Fréquence non compatible : impossible de poursuivre.")
        else:
            go("intro")

    elif isinstance(val, (int, float, str)):
        try:  p.hz_val = float(val)
        except ValueError:  pass

# 1 — Présentation + tirage
elif p.page == "intro":

    st.markdown("""
<div style='height:100%;display:flex;flex-direction:column;
            align-items:center;justify-content:center;text-align:center'>
  <h2>2. Présentation de la tâche</h2>
  <p style='max-width:600px;font-size:1.4rem'>
  Des mots seront affichés très brièvement puis masqués (<code>#####</code>).<br>
  • Fixez le centre de l’écran.<br>
  • Dès que vous reconnaissez un mot, appuyez sur <b>ESPACE</b>.<br>
  • Tapez ensuite le mot puis <b>Entrée</b>.<br><br>
  Étapes : 1)&nbsp;Entraînement (2 mots) 2)&nbsp;Test principal (80 mots)
  </p>
</div>""", unsafe_allow_html=True)

    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True; _rerun()

    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df            = build_sheet()
            p.stimuli     = df["ortho"].sample(frac=1).tolist()
            p.tirage_ok   = True
            p.tirage_running = False
        st.success("Tirage terminé !")

    if p.tirage_ok and st.button("Commencer la familiarisation",
                                 use_container_width=True):
        go("fam")

# 2 — Familiarisation
elif p.page == "fam":
    st.markdown("<h2 style='text-align:center'>Familiarisation (2 mots)</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;font-size:1.3rem'>"
                "Appuyez sur <b>ESPACE</b> dès que le mot apparaît, tapez-le puis "
                "<b>Entrée</b>.</p>", unsafe_allow_html=True)

    full_html("""
      <div style='background:#000;color:#fff;height:100%;
                  display:flex;align-items:center;justify-content:center;
                  font-size:3rem'>
         — Votre tâche de familiarisation ici —
      </div>""", key="fam")

    if st.button("Passer au test principal", use_container_width=True):
        go("exp")

# 3 — Test principal
elif p.page == "exp":
    st.markdown("<h2 style='text-align:center'>Test principal (80 mots)</h2>",
                unsafe_allow_html=True)

    full_html("""
      <div style='background:#000;color:#fff;height:100%;
                  display:flex;align-items:center;justify-content:center;
                  font-size:3rem'>
         — Votre tâche principale ici —
      </div>""", key="exp")
