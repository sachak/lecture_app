# -*- coding: utf-8 -*-
"""
Expérience 3 – mots masqués
Liste des mots construite en tâche de fond puis interface Streamlit.
(Version sans f-string pour la page HTML.)
"""
from __future__ import annotations
import json, random, threading, queue
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ────────────────── petite fonction pour rerun compatible ─────────────────── #
def _do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ────────────── (tout le code de construction de la liste) ────────────────── #
# …………………………………  << inchangé : variables, load_sheets(), build_sheet() >>
# pour raccourcir, on assume que vous reprenez exactement la partie
# précédemment fournie jusqu’à la fin de la page « intro ».
# Ici on reprend à partir de la PAGE EXP  ───────────────────────────────────── #

# ------------------------------ PAGE EXP ----------------------------------- #
else:                                      # page 'exp'
    if not st.session_state.stimuli_ok:
        st.stop()

    STIMULI = st.session_state.STIMULI     # liste de 80 mots en majuscules
    CYCLE_MS, START_MS, STEP_MS = 350, 14, 14

    # -------- HTML / JavaScript sans f-string (pas besoin de doubler les {}) --
    html_template = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/>
<style>
html,body{
  height:100%;margin:0;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  font-family:'Courier New',monospace;}
#scr{font-size:60px;user-select:none;}
#ans{display:none;font-size:48px;width:60%;text-align:center;}
</style>
</head>
<body tabindex="0">
<div id="scr"></div>
<input id="ans" autocomplete="off"/>
<script>
const WORDS = __WORDS__;
const CYCLE = __CYCLE__;
const START = __START__;
const STEP  = __STEP__;

let trial = 0;
let results = [];
const scr = document.getElementById("scr");
const ans = document.getElementById("ans");

function nextTrial(){
  if(trial >= WORDS.length){ endExperiment(); return; }

  const w    = WORDS[trial];
  const mask = "#".repeat(w.length);

  let showDur = START;
  let hideDur = CYCLE - showDur;
  let tShow, tHide;
  const t0 = performance.now();
  let active = true;

  (function loop(){
     if(!active) return;
     scr.textContent = w;
     tShow = setTimeout(()=>{
        if(!active) return;
        scr.textContent = mask;
        tHide = setTimeout(()=>{
           if(active){
             showDur += STEP;
             hideDur = Math.max(0, CYCLE - showDur);
             loop();
           }
        }, hideDur);
     }, showDur);
  })();

  function onSpace(e){
     if(e.code === "Space" && active){
        active = false;
        clearTimeout(tShow); clearTimeout(tHide);

        const rt = Math.round(performance.now() - t0);
        window.removeEventListener("keydown", onSpace);

        scr.textContent = "";
        ans.style.display = "block";
        ans.value = "";
        ans.focus();

        ans.addEventListener("keydown", function onEnter(ev){
           if(ev.key === "Enter"){
              ev.preventDefault();
              results.push({word: w, rt_ms: rt, response: ans.value.trim()});
              ans.removeEventListener("keydown", onEnter);
              ans.style.display = "none";
              trial++;
              nextTrial();
           }
        });
     }
  }
  window.addEventListener("keydown", onSpace);
}

function endExperiment(){
  scr.style.fontSize = "40px";
  scr.textContent    = "Merci !";

  const csv = ["word;rt_ms;response",
               ...results.map(r => `${r.word};${r.rt_ms};${r.response}`)]
               .join("\\n");

  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type:"text/csv"}));
  a.download = "results.csv";
  a.textContent = "Télécharger les résultats";
  a.style.fontSize = "32px";
  a.style.marginTop = "30px";
  document.body.appendChild(a);
}

nextTrial();
</script>
</body></html>"""

    # -------- insertion des valeurs (simple replace) -------------------------
    html = (html_template
            .replace("__WORDS__", json.dumps(STIMULI))
            .replace("__CYCLE__", str(CYCLE_MS))
            .replace("__START__", str(START_MS))
            .replace("__STEP__",  str(STEP_MS)))

    components.v1.html(html, height=650, scrolling=False)
