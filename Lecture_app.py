# -*- coding: utf-8 -*-
"""
EXPÉRIENCE 3 – Reconnaissance de mots masqués
(familiarisation + test 80 mots, synchronisation rAF / 60 Hz)

Exécution :  streamlit run exp3.py
Dépendance : Lexique.xlsx (Feuil1 … Feuil4)
"""
from __future__ import annotations

import random, pandas as pd
from pathlib import Path
from string  import Template
import streamlit as st
import streamlit.components.v1 as components


# ═════════════════════════ utilitaire rerun ════════════════════════════════
def do_rerun(): (st.rerun if hasattr(st, "rerun") else st.experimental_rerun)()


# ═════════════════════ configuration Streamlit ════════════════════════════
st.set_page_config(page_title="Expérience 3", layout="wide")
st.markdown("""
<style>
#MainMenu, header, footer {visibility:hidden;}
button:disabled{opacity:.45!important;cursor:not-allowed!important;}
</style>""", unsafe_allow_html=True)


# ═════════════════════ initialisation état de session ═════════════════════
for k, v in dict(page="screen_test", hz_ok=False,
                 tirage_ok=False, tirage_running=False).items():
    st.session_state.setdefault(k, v)


# ═════════════════════════════ paramètres tirage ═══════════════════════════
MEAN_FACTOR_OLDPLD = .45
MEAN_DELTA         = dict(letters=.68, phons=.68)
SD_MULT            = dict(letters=2, phons=2, old20=.28, pld20=.28, freq=1.9)

XLSX             = Path(__file__).with_name("Lexique.xlsx")
N_PER_FEUIL_TAG  = 5
TAGS             = ("LOW_OLD", "HIGH_OLD", "LOW_PLD", "HIGH_PLD")
MAX_TRY_TAG      = MAX_TRY_FULL = 1_000
rng              = random.Random()

NUM_BASE        = ["nblettres", "nbphons", "old20", "pld20"]
PRACTICE_WORDS  = ["PAIN", "EAU"]


# ═════════════════════════════ outils tirage ══════════════════════════════
def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str)
         .str.replace("[ ,\u00a0]", "", regex=True)
         .str.replace(",", ".",  regex=False),
        errors="coerce")

def shuffled(df):                      # mélange reproductible
    return df.sample(frac=1, random_state=rng.randint(0, 1_000_000)).reset_index(drop=True)

def cat_code(tag): return -1 if "LOW"  in tag else 1


@st.cache_data(show_spinner=False)
def load_sheets() -> dict[str, dict]:
    if not XLSX.exists(): st.error(f"{XLSX.name} introuvable"); st.stop()
    xls    = pd.ExcelFile(XLSX)
    sheets = [s for s in xls.sheet_names if s.lower().startswith("feuil")]
    if len(sheets) != 4: st.error("Il faut 4 feuilles Feuil1…Feuil4"); st.stop()

    feuilles, all_freq_cols = {}, set()
    for sh in sheets:
        df = xls.parse(sh); df.columns = df.columns.str.strip().str.lower()
        fq = [c for c in df.columns if c.startswith("freq")]
        all_freq_cols.update(fq)

        need = ["ortho", "old20", "pld20", "nblettres", "nbphons"] + fq
        if any(c not in df.columns for c in need):
            st.error(f"Colonnes manquantes dans {sh}"); st.stop()

        for c in NUM_BASE + fq:
            df[c] = to_float(df[c])

        df["ortho"] = df["ortho"].astype(str).str.upper()
        df = df.dropna(subset=need).reset_index(drop=True)

        stats = {f"m_{c}": df[c].mean() for c in ("old20", "pld20", "nblettres", "nbphons")}
        stats |= {f"sd_{c}": df[c].std(ddof=0) for c in ("old20", "pld20", "nblettres", "nbphons") + tuple(fq)}

        feuilles[sh] = dict(df=df, stats=stats, freq_cols=fq)

    feuilles["all_freq_cols"] = sorted(all_freq_cols)
    return feuilles


def masks(df, st_): return dict(
    LOW_OLD  = df.old20 < st_["m_old20"] - st_["sd_old20"],
    HIGH_OLD = df.old20 > st_["m_old20"] + st_["sd_old20"],
    LOW_PLD  = df.pld20 < st_["m_pld20"] - st_["sd_pld20"],
    HIGH_PLD = df.pld20 > st_["m_pld20"] + st_["sd_pld20"]
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
        abs(s.nblettres.mean() - st_["m_nblettres"]) <= MEAN_DELTA["letters"] * st_["sd_nblettres"] and
        abs(s.nbphons.mean()  - st_["m_nbphons"])    <= MEAN_DELTA["phons"]   * st_["sd_nbphons"]
    )


def pick_five(tag, feuille, used, F):
    df, st_ = F[feuille]["df"], F[feuille]["stats"]
    fq      = F[feuille]["freq_cols"]
    pool    = df.loc[masks(df, st_)[tag] & ~df.ortho.isin(used)]
    if len(pool) < N_PER_FEUIL_TAG:
        return None

    for _ in range(MAX_TRY_TAG):
        samp = pool.sample(N_PER_FEUIL_TAG, random_state=rng.randint(0, 1_000_000)).copy()

        # moyenne suffisamment éloignée de la moyenne générale
        if tag == "LOW_OLD"  and samp.old20.mean() >= st_["m_old20"] - MEAN_FACTOR_OLDPLD * st_["sd_old20"]:
            continue
        if tag == "HIGH_OLD" and samp.old20.mean() <= st_["m_old20"] + MEAN_FACTOR_OLDPLD * st_["sd_old20"]:
            continue
        if tag == "LOW_PLD"  and samp.pld20.mean() >= st_["m_pld20"] - MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:
            continue
        if tag == "HIGH_PLD" and samp.pld20.mean() <= st_["m_pld20"] + MEAN_FACTOR_OLDPLD * st_["sd_pld20"]:
            continue

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
        groups = []
        ok     = True

        for tag in TAGS:
            bloc = []
            for sh in taken:
                sub = pick_five(tag, sh, taken[sh], F)
                if sub is None:
                    ok = False
                    break
                bloc.append(sub)
                taken[sh].update(sub.ortho)
            if not ok:
                break
            groups.append(shuffled(pd.concat(bloc, ignore_index=True)))

        if ok:
            df = pd.concat(groups, ignore_index=True)
            order = ["ortho"] + NUM_BASE + all_freq + ["source", "group", "old_cat", "pld_cat"]
            return df[order]

    st.error("Impossible de générer la liste."); st.stop()


# ═════════════════════════ HTML : test 60 Hz (corrigé) ════════════════════
TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:30px 0}button{font-size:24px;padding:8px 28px}
</style></head><body>
<h2>Test de fréquence (60 Hz)</h2>
<div id="res">--</div><button id="go">Démarrer</button>

<script>
const res=document.getElementById("res");
const btn=document.getElementById("go");

function sendToStreamlit(value){
  window.parent.postMessage(
    {isStreamlitMessage:true, type:"streamlit:setComponentValue", value:value},
    "*"
  );
}

btn.onclick=()=>{
  btn.disabled=true; res.style.color="#fff"; res.textContent="Mesure en cours…";
  let t=[],n=120;
  function step(k){
      t.push(k);
      if(t.length<n){ requestAnimationFrame(step); }
      else{
        const d=t.slice(1).map((v,i)=>v-t[i]);
        const hz=1000/(d.reduce((a,b)=>a+b,0)/d.length);
        res.textContent="≈ "+hz.toFixed(1)+" Hz";
        const ok=hz>58 && hz<62;
        res.style.color = ok ? "lime" : "red";
        btn.disabled=false;
        if(ok){ sendToStreamlit("ok"); }
      }
  }
  requestAnimationFrame(step);
};
</script>
</body></html>
"""


# ═════════════════════ page 0 : TEST 60 Hz ════════════════════════════════
if st.session_state.page == "screen_test":
    st.write("### Vérification de l’écran (60 Hz requis)")
    hz_val = components.html(TEST60_HTML, height=600, scrolling=False, key="test60hz")
    if hz_val == "ok":
        st.session_state.hz_ok = True

    st.button("Passer à la présentation ➜",
              disabled=not st.session_state.hz_ok,
              on_click=lambda: (st.session_state.update(page="intro"), do_rerun()))


# ═════════════════════ page 1 : INTRO / TIRAGE ════════════════════════════
elif st.session_state.page == "intro":
    st.title("TÂCHE DE RECONNAISSANCE DE MOTS")
    st.markdown("""
Des mots seront présentés très brièvement puis masqués (`#####`).

• Fixez le centre de l’écran.  
• Dès que vous reconnaissez un mot, appuyez sur **ESPACE**.  
• Tapez ensuite le mot puis **Entrée**.

1. Entraînement (2 mots)  2. Test principal (80 mots)
""")

    # Tirage asynchrone
    if not st.session_state.tirage_running and not st.session_state.tirage_ok:
        st.session_state.tirage_running = True
        do_rerun()

    elif st.session_state.tirage_running and not st.session_state.tirage_ok:
        with st.spinner("Tirage aléatoire des 80 mots…"):
            df  = build_sheet()
            mots = df["ortho"].tolist()
            random.shuffle(mots)
            st.session_state.stimuli = mots
            st.session_state.tirage_ok = True
            st.session_state.tirage_running = False
        st.success("Tirage terminé !")

    if st.session_state.tirage_ok:
        st.button("Commencer la familiarisation",
                  on_click=lambda: (st.session_state.update(page="fam"), do_rerun()))


# ═════════════════════ page 2 : FAMILIARISATION ═══════════════════════════
elif st.session_state.page == "fam":
    st.header("Familiarisation (2 mots)")
    st.markdown("Appuyez sur **ESPACE** dès que le mot apparaît, "
                "puis tapez-le et validez par **Entrée**.")

    # ——— iframe familiarisation (placeholder) ———
    components.html(
        Template(open(__file__).read()).substitute(),   # à remplacer par votre HTML expérimental
        height=650, scrolling=False, key="fam_iframe")

    st.divider()
    st.button("Passer au test principal",
              on_click=lambda: (st.session_state.update(page="exp"), do_rerun()))


# ═════════════════════ page 3 : TEST PRINCIPAL ════════════════════════════
elif st.session_state.page == "exp":
    components.html(
        Template(open(__file__).read()).substitute(),   # à remplacer par votre HTML expérimental
        height=700, scrolling=False, key="exp_iframe")
