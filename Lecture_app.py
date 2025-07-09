# ─── exp3_frame.py ───────────────────────────────────────────────────────
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués (frame-accurate)

• 60 / 120 Hz
• Responsive : PC, TV, tablette, smartphone
• Mobile : tap + clavier virtuel QWERTZ (aucune suggestion)
• Plein-écran :
    – si Streamlit >= 1.25 → allow_fullscreen et requestFullscreen
    – sinon, fonctionnement bureau classique (barre URL sur mobile)
"""
from __future__ import annotations
import inspect, json, random
from pathlib import Path
from string import Template
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ────────────────── aides Streamlit ─────────────────────────────────────
def do_rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

def html_fs(html: str, **kwargs):
    """
    Enveloppe universelle pour components.html :
    – ajoute allow_fullscreen=True si l’argument existe dans cette version.
    – retire key/allow_fullscreen si non supportés pour éviter TypeError.
    """
    sig = inspect.signature(components.html).parameters
    if "allow_fullscreen" in sig:
        kwargs.setdefault("allow_fullscreen", True)
    else:
        kwargs.pop("allow_fullscreen", None)
    if "key" not in sig:
        kwargs.pop("key", None)
    return components.html(html, **kwargs)


# ───────────────── configuration Streamlit ──────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ─────────────────────────── constantes ─────────────────────────────────
XLSX            = Path(__file__).with_name("Lexique.xlsx")
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG = 5
MAX_TRY_TAG     = MAX_TRY_FULL = 1_000
rng             = random.Random()

NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]

CYCLE_MS        = 350
CROSS_MS        = 500

MEAN_FACTOR_OLDPLD = .35
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

# ────────────────────────── utilitaires ---------------------------------
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(r"[ ,\xa0]", "", regex=True).str.replace(",", "."),
        errors="coerce",
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int: return -1 if "LOW" in tag else (1 if "HIGH" in tag else 0)
def nearest_hz(x: float) -> int: return min([60,75,90,120,144], key=lambda v: abs(v-x))

# ────── 1. lecture Excel ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_sheets() -> Dict[str, Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable"); st.stop()

    xls  = pd.ExcelFile(XLSX)
    shs  = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(shs) != 4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4"); st.stop()

    feuilles, all_freq = {}, set()
    for sh in shs:
        df = xls.parse(sh)
        df.columns = df.columns.str.strip().str.lower()
        freq_cols  = [c for c in df.columns if c.startswith("freq")]
        all_freq.update(freq_cols)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + freq_cols
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for c in NUM_BASE + freq_cols:
            df[c] = to_float(df[c])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df          = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean()        for c in NUM_BASE}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in NUM_BASE + freq_cols}
        feuilles[sh] = dict(df=df, stats=stats, freq_cols=freq_cols)

    feuilles["all_freq_cols"] = sorted(all_freq)
    return feuilles


# ────── 2. tirage 80 mots ───────────────────────────────────────────────
def masks(df, st_): return dict(
    LOW_OLD=df.old20 < st_["m_old20"],
    HIGH_OLD=df.old20 > st_["m_old20"],
    LOW_PLD=df.pld20 < st_["m_pld20"],
    HIGH_PLD=df.pld20 > st_["m_pld20"],
)

def sd_ok(s, st_, fq):
    return (
        s.nblettres.std(ddof=0) <= st_["sd_nblettres"]*SD_MULT["letters"] and
        s.nbphons.std(ddof=0)   <= st_["sd_nbphons"]  *SD_MULT["phons"]   and
        s.old20.std(ddof=0)     <= st_["sd_old20"]    *SD_MULT["old20"]   and
        s.pld20.std(ddof=0)     <= st_["sd_pld20"]    *SD_MULT["pld20"]   and
        all(s[c].std(ddof=0) <= st_[f"sd_{c}"]*SD_MULT["freq"] for c in fq)
    )

def mean_lp_ok(s, st_):
    return (
        abs(s.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
        abs(s.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"]
    )

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]; fq = F[feuille]["freq_cols"]
    pool = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean()>=st_["m_old20"]-MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="HIGH_OLD" and samp.old20.mean()<=st_["m_old20"]+MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="LOW_PLD"  and samp.pld20.mean()>=st_["m_pld20"]-MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag=="HIGH_PLD" and samp.pld20.mean()<=st_["m_pld20"]+MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fq): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet() -> pd.DataFrame:
    F  = load_sheets(); ALL = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        take={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            bloc=[]
            for sh in take:
                sub=pick_five(tag, sh, take[sh], F)
                if sub is None: ok=False; break
                bloc.append(sub); take[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            return df[["ortho"]+NUM_BASE+ALL+["source","group","old_cat","pld_cat"]]
    st.error("Impossible de générer la liste."); st.stop()


# ────── 3. template HTML (responsive + clavier virtuel) ─────────────────
HTML_TPL = Template(r""" … (identique à la version précédente, déjà contenue ci-dessus) … """)

# ────── 3-bis. constructeur HTML ----------------------------------------
# (identique à la version précédente)

# ────── 4. TEST_HTML (identique) ----------------------------------------

# ────── 5. état de session ---------------------------------------------
# (identique)

# ────── 6. navigation Streamlit ----------------------------------------
# 1) test écran
if p.page == "screen_test":
    st.subheader("1. Vérification (facultative) de la fréquence d’écran")
    val = html_fs(TEST_HTML, height=520, scrolling=False, key="hz")
    if isinstance(val, (int, float, str)):
        try: p.hz_val = float(val)
        except ValueError: pass
    if p.hz_val is not None:
        st.write(f"Fréquence détectée ≈ **{nearest_hz(p.hz_val):d} Hz**")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Suivant 60 Hz ➜"):
            p.hz_sel = 60
            go("intro")
    with c2:
        if st.button("Suivant 120 Hz ➜"):
            p.hz_sel = 120
            go("intro")
    with c3:
        if st.button("Autre ➜"):
            go("incompatible")

# 2) page incompatible
elif p.page == "incompatible":
    st.error("Désolé : expérience réservée aux écrans 60 Hz ou 120 Hz.")

# 3) intro + tirage
elif p.page == "intro":
    st.subheader("2. Présentation de la tâche")
    st.markdown(f"""
Écran sélectionné : **{p.hz_sel} Hz**

Chaque essai : croix 500 ms → mot bref → masque (`#####`).

• Fixez le centre de l’écran  
• Dès que vous reconnaissez le mot, **tapotez l’écran OU appuyez sur ESPACE**  
• Tapez ensuite le mot (clavier virtuel sur mobile) puis **↵ / Entrée**

Déroulement : 2 essais d’entraînement + 80 essais de test.
""")
    if not p.tirage_run and not p.tirage_ok:
        p.tirage_run = True
        do_rerun()
    elif p.tirage_run and not p.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df = build_sheet()
            mots = df["ortho"].tolist()
            random.shuffle(mots)
            p.tirage_df = df
            p.stimuli = mots
            p.tirage_ok = True
            p.tirage_run = False
        st.success("Tirage terminé !")
    if p.tirage_ok and st.button("Commencer la familiarisation"):
        go("fam")

# 4) familiarisation
elif p.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.write("Croix 500 ms → mot → masque. Tapotez ou appuyez sur ESPACE dès que possible.")
    html_fs(
        experiment_html(PRACTICE_WORDS, p.hz_sel,
                        with_download=False, touch_trigger=False),
        height=650, scrolling=False
    )
    st.divider()
    if st.button("Passer au test principal"):
        p.page = "exp"
        p.exp_started = False
        do_rerun()

# 5) test principal
elif p.page == "exp":
    if not p.exp_started:
        st.header("Test principal : 80 mots")
        with st.expander("Aperçu (5 lignes)"):
            st.dataframe(p.tirage_df.head())
        if st.button("Commencer le test (plein écran)"):
            p.exp_started = True
            do_rerun()
    else:
        html_fs(
            experiment_html(p.stimuli, p.hz_sel,
                            with_download=True, touch_trigger=True),
            height=700, scrolling=False
        )

else:
    st.stop()
