# ─── exp3_frame.py ───────────────────────────────────────────────────────
# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués (frame-accurate)
• Test de fréquence d’écran avec affichage arrondi :
   27-33→30, 58-62→60, 73-77→75, 84-86→85,
   88-92→90, 98-102→100, 118-122→120, 141-146→144 Hz
• Choix 60 Hz / 120 Hz / autre
• Croix + 500 ms ; présentation rAF
"""

from __future__ import annotations
import inspect, json, random
from pathlib import Path
from string import Template
from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def do_rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer{visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ──────────────────────────── constantes ────────────────────────────────
XLSX = Path(__file__).with_name("Lexique.xlsx")

TAGS             = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
N_PER_FEUIL_TAG  = 5
MAX_TRY_TAG      = MAX_TRY_FULL = 1_000
rng              = random.Random()

NUM_BASE         = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS   = ["PAIN", "EAU"]

CYCLE_MS         = 350   # mot + masque
CROSS_MS         = 500   # croix 500 ms

MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

# ────────────────────────── petits utilitaires ──────────────────────────
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(r"[ ,\xa0]", "", regex=True).str.replace(",", "."),
        errors="coerce",
    )

def shuffled(df: pd.DataFrame) -> pd.DataFrame:
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag: str) -> int: return -1 if "LOW" in tag else (1 if "HIGH" in tag else 0)

# ───────── mapping fréquence mesurée → étiquette « propre » (côté Python) ─
def label_hz(meas: float) -> int | None:
    ranges = [
        (30 , 27 , 33 ),
        (60 , 58 , 62 ),
        (75 , 73 , 77 ),
        (85 , 84 , 86 ),
        (90 , 88 , 92 ),
        (100, 98 , 102),
        (120, 118, 122),
        (144, 141, 146),
    ]
    for lbl, low, high in ranges:
        if low <= meas <= high:
            return lbl
    return None

# ────── 1. lecture et préparation de Lexique.xlsx ───────────────────────
@st.cache_data(show_spinner=False)
def load_sheets() -> Dict[str, Dict]:
    if not XLSX.exists():
        st.error(f"Fichier « {XLSX.name} » introuvable"); st.stop()

    xls = pd.ExcelFile(XLSX)
    shs = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(shs) != 4:
        st.error("Il faut exactement 4 feuilles Feuil1 … Feuil4"); st.stop()

    feuilles, all_freq = {}, set()
    for sh in shs:
        df = xls.parse(sh)
        df.columns  = df.columns.str.strip().str.lower()
        freq_cols   = [c for c in df.columns if c.startswith("freq")]
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

# ────── 2. fonctions de tirage (identiques) ─────────────────────────────
def masks(df, st_): return dict(
    LOW_OLD = df.old20 < st_["m_old20"],
    HIGH_OLD= df.old20 > st_["m_old20"],
    LOW_PLD = df.pld20 < st_["m_pld20"],
    HIGH_PLD= df.pld20 > st_["m_pld20"],
)

def sd_ok(sub, st_, fq):
    return (
        sub.nblettres.std(ddof=0) <= st_["sd_nblettres"] * SD_MULT["letters"] and
        sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]   * SD_MULT["phons"]   and
        sub.old20.std(ddof=0)     <= st_["sd_old20"]     * SD_MULT["old20"]   and
        sub.pld20.std(ddof=0)     <= st_["sd_pld20"]     * SD_MULT["pld20"]   and
        all(sub[c].std(ddof=0) <= st_[f"sd_{c}"] * SD_MULT["freq"] for c in fq)
    )

def mean_lp_ok(s, st_):
    return (
        abs(s.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
        abs(s.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"]
    )

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 1_000_000)).copy()
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
    F  = load_sheets()
    ALL= F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        take={sh:set() for sh in F if sh!="all_freq_cols"}; groups=[]; ok=True
        for tag in TAGS:
            bloc=[]
            for sh in take:
                sub=pick_five(tag,sh,take[sh],F)
                if sub is None: ok=False; break
                bloc.append(sub); take[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))
        if ok:
            df=pd.concat(groups, ignore_index=True)
            return df[["ortho"]+NUM_BASE+ALL+["source","group","old_cat","pld_cat"]]
    st.error("Impossible de générer la liste."); st.stop()

# ────── 3. gabarit HTML (croix + rAF) ────────────────────────────────────
HTML_TPL = Template(r""" … (inchangé, voir version précédente) … """)
#  ↳ Le contenu est identique à la version envoyée juste avant ; on ne le
#    ré-affiche pas ici pour ne pas alourdir. Seule la partie TEST_HTML
#    change pour afficher l’étiquette.

# ────── 4. composant test fréquence écran (affichage arrondi) ────────────
TEST_HTML=r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:24px}button{font-size:22px;padding:6px 26px;margin:4px}</style></head><body>
<h2>Test de fréquence</h2><div id="res">--</div><button id="go" onclick="mesure()">Démarrer</button>
<script>
function niceLabel(h){          // mapping JS identique aux consignes
  if(h>=27 && h<=33)  return 30;
  if(h>=58 && h<=62)  return 60;
  if(h>=73 && h<=77)  return 75;
  if(h>=84 && h<=86)  return 85;
  if(h>=88 && h<=92)  return 90;
  if(h>=98 && h<=102) return 100;
  if(h>=118&& h<=122) return 120;
  if(h>=141&& h<=146) return 144;
  return h.toFixed(1);
}
function mesure(){
  const r=document.getElementById('res'),b=document.getElementById('go');
  b.disabled=true;r.textContent='Mesure…';let f=0,t0=performance.now();
  function loop(){
    f++;
    if(f<120){requestAnimationFrame(loop);}
    else{
      const hz=f*1000/(performance.now()-t0),
            lbl=niceLabel(hz);
      r.textContent='≈ '+lbl+' Hz';
      Streamlit.setComponentValue(hz.toFixed(1));   // envoie la valeur brute
      b.disabled=false;
    }}
  requestAnimationFrame(loop);
}
Streamlit.setComponentReady();
</script></body></html>"""

# ────── 5. état session ─────────────────────────────────────────────────
for k,v in {"page":"screen_test","tirage_ok":False,"tirage_run":False,
            "stimuli":[], "tirage_df":pd.DataFrame(),"exp_started":False,
            "hz_val":None,"hz_sel":None}.items():
    st.session_state.setdefault(k,v)
p=st.session_state
def go(page:str): p.page=page; do_rerun()

# ────── 6. PAGES … (identiques à la version précédente) ─────────────────
#    A partir d’ici, tout le code est inchangé : utilisation de label_hz()
#    pour l’affichage sous le composant, boutons « Suivant », intro,
#    familiarisation, test principal, etc.
