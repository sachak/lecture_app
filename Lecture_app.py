# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test principal ; contrôle 60 Hz)

Exécution :   streamlit run exp3.py
Dépendance :  Lexique.xlsx (4 feuilles : Feuil1 … Feuil4)
"""
from __future__ import annotations

from pathlib import Path
import inspect, random
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ═════════════════════════════ OUTIL « rerun » ════════════════════════════
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ══════════════ PARAMÈTRES D’AFFICHAGE STREAMLIT ═════════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>
""", unsafe_allow_html=True)


# ══════════════ ÉTAT INITIAL DE L’APPLICATION ════════════════════════════
for k, v in dict(page="screen_test",
                 hz_val=None,          # valeur mesurée (float ou None)
                 tirage_running=False,
                 tirage_ok=False).items():
    st.session_state.setdefault(k, v)
p = st.session_state     # alias court


# ══════════════ CONSTANTES & OUTILS « TIRAGE DES 80 MOTS » ═══════════════
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

XLSX             = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG  = 5
TAGS             = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG      = MAX_TRY_FULL = 1_000
rng              = random.Random()

NUM_BASE = ["nblettres", "nbphons", "old20", "pld20"]


def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r"[ ,\u00a0]", "", regex=True)
         .str.replace(",", ".", regex=False),
        errors="coerce")


def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1,
                     random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)


def cat_code(tag: str) -> int:            # –1 pour LOW, +1 pour HIGH
    return -1 if "LOW" in tag else 1


@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists():
        st.error("Fichier « Lexique.xlsx » introuvable"); st.stop()

    xls    = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets) != 4:
        st.error("Le classeur doit contenir 4 feuilles Feuil1…Feuil4"); st.stop()

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
        df = df.dropna(subset=need).reset_index(drop=True)

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
        HIGH_PLD = df.pld20 > st_["m_pld20"] + st_["sd_pld20"]
    )


def sd_ok(sub, st_, fq) -> bool:
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq)
    )


def mean_lp_ok(s, st_) -> bool:
    return (
        abs(s.nblettres.mean() - st_["m_nblettres"])
            <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(s.nbphons.mean()  - st_["m_nbphons"])
            <= MEAN_DELTA["phons"]   * st_["sd_nbphons"]
    )


def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]

    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG,
                           random_state=rng.randint(0, 1_000_000)).copy()

        if tag == "LOW_OLD" and samp.old20.mean() >= \
           st_["m_old20"] - MEAN_FACTOR_OLDPLD * st_["sd_old20"]:  continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= \
           st_["m_old20"] + MEAN_FACTOR_OLDPLD * st_["sd_old20"]:  continue
        if tag == "LOW_PLD" and samp.pld20.mean() >= \
           st_["m_pld20"] - MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:  continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= \
           st_["m_pld20"] + MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:  continue

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
        taken  = {sh: set() for sh in F if sh != "all_freq_cols"}
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


# ══════════════ CODE HTML / JS : TEST FRÉQUENCE + VALEUR envoyée à Python ═
TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:26px 0}
button{font-size:22px;padding:6px 26px;margin:4px}
</style></head><body>
<h2>Test de fréquence</h2>
<div id="res">--</div>
<button id="go" onclick="mesure()">Démarrer</button>
<script>
function mesure(){
  const res=document.getElementById('res'),btn=document.getElementById('go');
  btn.disabled=true; res.textContent='Mesure en cours…'; res.style.color='#fff';
  let f=0,t0=performance.now();
  function loop(){
    f++; if(f<120){ requestAnimationFrame(loop); }
    else{
      const hz=f*1000/(performance.now()-t0);
      Streamlit.setComponentValue(hz.toFixed(1));   // envoi vers Python
      btn.disabled=false;
    }}
  requestAnimationFrame(loop);
}
Streamlit.setComponentReady();
</script></body></html>
"""


# ══════════════ OUTIL : ARRONDIR À LA FRÉQUENCE « COMMERCE » LA + PROCHE ═
COMMERCIAL = [60, 75, 90, 120, 144]
def nearest_hz(x: float) -> int:
    return min(COMMERCIAL, key=lambda v: abs(v-x))


# ══════════════ NAVIGATION (changement de page) ══════════════════════════
def go(page: str):
    p.page = page
    do_rerun()


# ════════════════════════════ PAGE 0 : TEST ÉCRAN ════════════════════════
if p.page == "screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")

    # compatibilité du paramètre key (toutes versions de Streamlit)
    html_sig = inspect.signature(components.html).parameters
    kwargs   = dict(height=550, scrolling=False)
    if "key" in html_sig:
        kwargs["key"] = "hz_test"

    hz_js = components.html(TEST60_HTML, **kwargs)

    # Mémoriser la valeur renvoyée (str -> float) si différente
    if hz_js and hz_js != p.hz_val:
        try:
            p.hz_val = float(hz_js)
        except ValueError:
            p.hz_val = None

    # Affichage du résultat (simplifié)
    if p.hz_val is not None:
        hz_round = nearest_hz(p.hz_val)
        if hz_round == 60:
            st.success("60 Hz – OK")
        else:
            st.error(f"Désolé, vous ne pouvez pas réaliser l’expérience.")
            st.markdown(f"Fréquence détectée ≈ **{hz_round} Hz**", unsafe_allow_html=True)
    else:
        st.info("Cliquez sur « Démarrer » pour lancer la mesure.")

    st.divider()
    # Bouton « Suivant » toujours présent
    if st.button("Suivant ➜"):
        go("intro")


# ═══════════════════ PAGE 1 : PRÉSENTATION + TIRAGE 80 MOTS ══════════════
elif p.page == "intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown("""
Des mots seront affichés très brièvement puis masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.  

Étapes : 1) Entraînement (2 mots) 2) Test principal (80 mots)
""")

    # Tirage aléatoire : déclenchement puis affichage d’un spinner
    if not p.tirage_running and not p.tirage_ok:
        p.tirage_running = True; do_rerun()

    elif p.tirage_running and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df   = build_sheet()
            mots = df["ortho"].tolist(); random.shuffle(mots)
            p.stimuli = mots
            p.tirage_ok, p.tirage_running = True, False
        st.success("Tirage terminé !")

    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")


# ═════════════════════ PAGE 2 : FAMILIARISATION ══════════════════════════
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Appuyez sur **ESPACE** dès que le mot apparaît, "
             "tapez-le puis **Entrée**.")

    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche de familiarisation ici —</div>",
        height=300, scrolling=False)

    if st.button("Passer au test principal"):
        go("exp")


# ═════════════════════ PAGE 3 : TEST PRINCIPAL ═══════════════════════════
elif p.page == "exp":
    st.header("Test principal (80 mots)")
    components.html(
        "<div style='height:300px;background:#000;color:#fff;"
        "display:flex;align-items:center;justify-content:center'>"
        "— Votre tâche principale ici —</div>",
        height=300, scrolling=False)
