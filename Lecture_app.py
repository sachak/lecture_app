# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test 80 mots, synchronisation rAF / 60 Hz)
Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations
import json, random
from pathlib import Path
from string import Template
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ────────────────────────── utilité rerun ──────────────────────────────────
def do_rerun():
    (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()

# ───────────────────────── configuration ───────────────────────────────────
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)

# ───────────────────────── états Streamlit ─────────────────────────────────
defaults = dict(page="screen_test", hz_ok=False,
                tirage_ok=False, tirage_running=False)
st.session_state |= {k: st.session_state.get(k, v) for k, v in defaults.items()}

# ───────────────────────── paramètres tirage (inchangés) ───────────────────
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2,
                          old20=.28, pld20=.28, freq=1.9)
XLSX            = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG = 5
TAGS            = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG     = 1000
MAX_TRY_FULL    = 1000
rng             = random.Random()

NUM_BASE       = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS = ["PAIN", "EAU"]

# ───────────────────────── tirage des stimuli (fonctions inchangées) ───────
def to_float(s):
    return pd.to_numeric(
        s.astype(str).str.replace(" ", "", regex=False)
         .str.replace("\xa0", "", regex=False)
         .str.replace(",", ".", regex=False),
        errors="coerce")

def shuffled(df): return df.sample(frac=1, random_state=rng.randint(0,1_000_000)).reset_index(drop=True)
def cat_code(tag): return -1 if "LOW" in tag else 1

@st.cache_data(show_spinner=False)
def load_sheets():
    if not XLSX.exists(): st.error(f"{XLSX.name} introuvable"); st.stop()
    xls = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets) != 4: st.error("Il faut 4 feuilles Feuil1..Feuil4"); st.stop()
    feuilles, all_freq_cols = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        fqs = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(fqs)
        need = ["ortho","old20","pld20","nblettres","nbphons"] + fqs
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()
        for c in NUM_BASE + fqs: df[c] = to_float(df[c])
        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)
        stats = {f"m_{c}": df[c].mean() for c in ("old20","pld20","nblettres","nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in ("old20","pld20","nblettres","nbphons")+tuple(fqs)}
        feuilles[sh] = dict(df=df, stats=stats, freq_cols=fqs)
    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles

# (fonctions masks, sd_ok, mean_lp_ok, pick_five, build_sheet identiques)
def masks(df, st_):
    return dict(
        LOW_OLD = df.old20 < st_["m_old20"] - st_["sd_old20"],
        HIGH_OLD= df.old20 > st_["m_old20"] + st_["sd_old20"],
        LOW_PLD = df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
        HIGH_PLD= df.pld20 > st_["m_pld20"] + st_["sd_pld20"])

def sd_ok(sub, st_, fq):
    return (sub.nblettres.std(ddof=0) <= st_["sd_nblettres"]*SD_MULT["letters"] and
            sub.nbphons.std(ddof=0)   <= st_["sd_nbphons"]  *SD_MULT["phons"]   and
            sub.old20.std(ddof=0)     <= st_["sd_old20"]    *SD_MULT["old20"]   and
            sub.pld20.std(ddof=0)     <= st_["sd_pld20"]    *SD_MULT["pld20"]   and
            all(sub[c].std(ddof=0) <= st_[f"sd_{c}"]*SD_MULT["freq"] for c in fq))

def mean_lp_ok(s, st_):
    return (abs(s.nblettres.mean()-st_["m_nblettres"]) <= MEAN_DELTA["letters"]*st_["sd_nblettres"] and
            abs(s.nbphons.mean()  -st_["m_nbphons"])   <= MEAN_DELTA["phons"]  *st_["sd_nbphons"])

def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG: return None
    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0,1_000_000)).copy()
        if tag=="LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD*st_["sd_old20"]:  continue
        if tag=="LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if tag=="HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD*st_["sd_pld20"]:  continue
        if not mean_lp_ok(samp, st_) or not sd_ok(samp, st_, fq): continue
        samp["source"], samp["group"] = feuille, tag
        samp["old_cat"] = cat_code(tag) if "OLD" in tag else 0
        samp["pld_cat"] = cat_code(tag) if "PLD" in tag else 0
        return samp
    return None

def build_sheet():
    F = load_sheets(); all_freq = F["all_freq_cols"]
    for _ in range(MAX_TRY_FULL):
        taken = {sh:set() for sh in F if sh!="all_freq_cols"}
        groups, ok = [], True
        for tag in TAGS:
            part=[]
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None: ok=False; break
                part.append(sub); taken[sh].update(sub.ortho)
            if not ok: break
            groups.append(shuffled(pd.concat(part, ignore_index=True)))
        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"]+NUM_BASE+all_freq+["source","group","old_cat","pld_cat"]
            return df[order]
    st.error("Impossible de générer la liste."); st.stop()

# ───────────────────────── HTML – TEST 60 Hz ───────────────────────────────
TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:30px 0}
button{font-size:24px;padding:8px 28px}
</style></head><body>
<h2>Test de fréquence d’écran (cible : 60 Hz)</h2>
<p>Cliquez sur « Démarrer » pour mesurer la fréquence réelle.</p>
<div id="res">--</div>
<button id="start">Démarrer</button>
<script>
Streamlit.setComponentReady();                     // annonce « prêt »
const res=document.getElementById("res");
document.getElementById("start").onclick=()=>{
  document.getElementById("start").disabled=true;
  let t=[],n=150;
  const step=k=>{
    t.push(k);
    if(t.length<n){requestAnimationFrame(step);}
    else{
      const d=t.slice(1).map((v,i)=>v-t[i]);           // écarts successifs
      const hz=1000/(d.reduce((a,b)=>a+b,0)/d.length);
      res.textContent=`≈ ${hz.toFixed(1)} Hz`;
      const ok=hz>58&&hz<62;
      res.style.color=ok?"lime":"red";
      document.getElementById("start").disabled=false;
      if(ok) Streamlit.setComponentValue("ok");        // renvoi valeur
    }}
  requestAnimationFrame(step);
};
</script></body></html>"""

# ───────────────────────── HTML – EXPÉ (rAF) ───────────────────────────────
EXP_HTML = Template(r""" … (identique à la version précédente) … """)

#  (pour gagner de la place : EXP_HTML et experiment_html sont inchangés
#   par rapport au message précédent)

# ───────────────────────── interface Streamlit ─────────────────────────────
if st.session_state.page == "screen_test":
    st.write("### Vérification de l’écran (60 Hz requis)")
    hz_value = components.html(TEST60_HTML, height=600, scrolling=False)
    if hz_value == "ok": st.session_state.hz_ok = True
    if st.button("Passer à la présentation ➜",
                 disabled=not st.session_state.hz_ok):
        st.session_state.page = "intro"; do_rerun()

# (les pages intro, fam, exp sont identiques à la version précédente)
