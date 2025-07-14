/* ***************************************************************************
 *  EXPÉRIENCE – envoi des données vers Azure SQL (HTTP Function)
 *  AUCUNE DEMANDE DE NOM : un identifiant aléatoire est attribué à la fin
 * ***************************************************************************/
'use strict';

/********************************************************************
 * 0. CONFIGURATION GÉNÉRALE
 ********************************************************************/
const CFG = {
  XLSX_FILE      : 'Lexique.xlsx',
  PRACTICE_WORDS : ['PAIN', 'EAU'],
  TOUCH_TRIGGER  : true,

  TAGS           : ['LOW_OLD', 'HIGH_OLD', 'LOW_PLD', 'HIGH_PLD'],
  N_PER_FEUIL_TAG: 5,
  MAX_TRY_TAG    : 1000,
  MAX_TRY_FULL   : 1000,

  NUM_BASE       : ['nblettres', 'nbphons', 'old20', 'pld20'],
  CYCLE_MS       : 350,
  CROSS_MS       : 500,
  MEAN_FACTOR_OLDPLD : .35,
  MEAN_DELTA     : {letters : .68, phons : .68},
  SD_MULT        : {letters : 2, phons : 2, old20 : .28, pld20 : .28, freq : 1.9},
  HZ             : null,               // défini plus tard

  /* paramètres API */
  API_URL        : '/api/save_results',
  API_KEY        : '',
  API_SECRET     : 'udzKkYgnwQnfs7LW2Oi3xwgfhDhYiucZaXZrV4sY'
};

/********************************************************************
 * 0.b  IDENTIFIANT ALÉATOIRE (128 bits → base-36 → 12 caractères)
 ********************************************************************/
function genPID () {
  const a = new Uint32Array(4);
  crypto.getRandomValues(a);           // navigateur moderne
  return [...a].map(n => n.toString(36).padStart(7, '0'))
               .join('')
               .slice(0, 6)
               .toUpperCase();
}
const PID = genPID();                  // généré une seule fois au chargement

/********************************************************************
 * 1. OUTILS DOM et STATISTIQUES
 ********************************************************************/
const $         = sel => document.querySelector(sel);
const page      = $('#page');
const scr       = $('#scr');
const ans       = $('#ans');
const vk        = $('#vk');

const rng       = () => Math.random();
const shuffled  = a => [...a].sort(() => rng() - .5);
const mean      = a => a.reduce((s, x) => s + x, 0) / a.length;
const std       = a => { const m = mean(a); return Math.sqrt(mean(a.map(x => (x - m) ** 2))); };
const pick      = (a, n) => shuffled(a).slice(0, n);
const toFloat   = v => typeof v === 'number' ? v : parseFloat(String(v).replace(/[\s,]/g, '.'));

/********************************************************************
 * 2. LECTURE DU LEXIQUE .XLSX + TIRAGE DES 80 MOTS
 ********************************************************************/
async function loadSheets () {
  const buf      = await fetch(CFG.XLSX_FILE).then(r => r.arrayBuffer());
  const wb       = XLSX.read(buf, {type: 'array'});
  const shNames  = wb.SheetNames.filter(s => s.toLowerCase().startsWith('feuil'));
  if (shNames.length !== 4) throw 'Il faut exactement 4 feuilles Feuil1 … Feuil4';

  const feuilles = {}, allFreq = new Set();
  for (const sh of shNames) {
    const json   = XLSX.utils.sheet_to_json(wb.Sheets[sh], {defval: null, raw: false});
    const cols   = Object.keys(json[0]).map(c => c.trim().toLowerCase());
    const need   = ['ortho', 'old20', 'pld20', 'nblettres', 'nbphons'];
    need.forEach(c => { if (!cols.includes(c)) throw `Colonne ${c} manquante dans ${sh}`; });
    const freq   = cols.filter(c => c.startsWith('freq'));
    freq.forEach(c => allFreq.add(c));

    const df = json
      .filter(r => need.every(k => r[k] != null))
      .map(r => {
        const o = {};
        [...need, ...freq].forEach(k => o[k] = toFloat(r[k]));
        o.ortho = String(r.ortho).toUpperCase();
        return o;
      });

    const stats = {};
    CFG.NUM_BASE.forEach(c             => stats['m_'  + c] = mean(df.map(r => r[c])));
    [...CFG.NUM_BASE, ...freq].forEach(c => stats['sd_' + c] = std (df.map(r => r[c])));

    feuilles[sh] = {df, stats, freqCols: freq};
  }
  feuilles.allFreqCols = [...allFreq];
  return feuilles;
}

/* … (Toutes les fonctions pickFive, buildSheet, etc. restent identiques)
   ────────────────────────────────────────────────────────────────────── */

/********************************************************************
 * 3. VARIABLES DYNAMIQUES EN FONCTION DU HZ CHOISI
 ********************************************************************/
let FRAME_MS, CYCLE_F, CROSS_F, SCALE, START_F, STEP_F, IS_TOUCH;
function setHz (hz) {
  CFG.HZ = hz;
  FRAME_MS = 1000 / hz;
  CYCLE_F  = Math.round(CFG.CYCLE_MS / FRAME_MS);
  CROSS_F  = Math.round(CFG.CROSS_MS / FRAME_MS);
  SCALE    = hz / 60;
  START_F  = 1 * SCALE;
  STEP_F   = 1 * SCALE;
  IS_TOUCH = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/********************************************************************
 * 4. MISE À L’ÉCHELLE DE L’INTERFACE
 ********************************************************************/
function resizeScr () {
  const b = Math.min(innerWidth, innerHeight);
  scr.style.fontSize = Math.max(Math.round(b * .08), 26) + 'px';
  ans.style.fontSize = Math.max(Math.round(b * .054), 20) + 'px';
  ans.style.width    = Math.min(innerWidth * .7, 650)    + 'px';
}
addEventListener('resize', resizeScr);
addEventListener('orientationchange', resizeScr);
addEventListener('load', () => setTimeout(resizeScr, 80));

/********************************************************************
 * 5. PHASE 1 : VÉRIFICATION HZ ÉCRAN
 ********************************************************************/
function page_Hz () {
  page.innerHTML = `
    <h2>1. Vérification de la fréquence d’écran</h2>
    <div id="hzVal" style="font-size:28px;">--</div>
    <button id="mes">Mesurer</button>
    <div style="margin-top:20px">
      <button id="hz60">Utiliser 60 Hz</button>
      <button id="hz120">Utiliser 120 Hz</button>
      <button id="hzOther">Autre</button>
    </div>`;
  $('#mes'    ).onclick = mesureHz;
  $('#hz60'   ).onclick = () => startLoading(60);
  $('#hz120'  ).onclick = () => startLoading(120);
  $('#hzOther').onclick = page_Incompatible;
}
function mesureHz () {
  const lbl = $('#hzVal');
  lbl.textContent = 'Mesure…';
  let f = 0, t0 = performance.now();
  (function loop () {
    f++;
    if (f < 120) requestAnimationFrame(loop);
    else lbl.textContent = '≈ ' + (f * 1000 / (performance.now() - t0)).toFixed(1) + ' Hz';
  })();
}
function page_Incompatible () {
  scr.style.display  = 'none';
  page.style.display = 'flex';
  page.innerHTML = `<h2>Désolé</h2><p>Cette expérience nécessite un écran 60 Hz ou 120 Hz.</p>`;
}

/********************************************************************
 * 5.b  CHARGEMENT / INSTRUCTIONS
 ********************************************************************/
let WORDS80 = [];
function startLoading (hzSel) {
  setHz(hzSel);
  page.innerHTML = `<h2>Préparation…</h2><p id="stat">Tirage aléatoire des 80 mots…</p>`;
  buildSheet()
    .then(list => {
      WORDS80 = list.map(r => ({
        word          : r.ortho,
        groupe        : r.groupe,
        nblettres     : r.nblettres,
        nbphons       : r.nbphons,
        old20         : r.old20,
        pld20         : r.pld20,
        freqfilms2    : r.freqfilms2,
        freqlemfilms2 : r.freqlemfilms2,
        freqlemlivres : r.freqlemlivres,
        freqlivres    : r.freqlivres
      }));
      page_Intro();
    })
    .catch(e => page.innerHTML = '<p style="color:red">' + e + '</p>');
}

function page_Intro () {
  page.innerHTML = `
    <h2>Instructions</h2>
    <p>Croix 500 ms → mot bref → masque.</p>
    <p>Touchez l’écran ou barre ESPACE dès que vous reconnaissez le mot,<br>
       puis tapez-le (clavier virtuel sur mobile).</p>
    <button id="startP">Commencer la familiarisation</button>`;
  $('#startP').onclick = page_Practice;
}

function page_Practice () {
  page.style.display = 'none';
  scr.style.display  = 'block';
  runBlock(CFG.PRACTICE_WORDS, 'practice', page_TestReady);
}

function page_TestReady () {
  scr.style.display  = 'none';
  page.style.display = 'flex';
  page.innerHTML = `<h2>Fin de l’entraînement</h2>
    <button id="goFull">Commencer le test (plein écran)</button>`;
  $('#goFull').onclick = () => {
    document.documentElement.requestFullscreen?.();
    page.style.display = 'none';
    scr.style.display  = 'block';
    runBlock(shuffled(WORDS80), 'main', endExperiment);
  };
}

/********************************************************************
 * 6. PRÉSENTATION DES ESSAIS + COLLECTE DES RÉPONSES
 ********************************************************************/
function runBlock (wordArr, phaseLabel, onFinish) {
  let trial = 0, results = [];

  const nextTrial = () => {
    if (trial >= wordArr.length) { onFinish(results); return; }

    const obj  = wordArr[trial];
    const w    = obj.word || obj;             // string dans la phase practice
    const grp  = obj.groupe || null;
    const len  = obj.nblettres || w.length;
    const mask = '#'.repeat(w.length);

    scr.textContent = '+';
    let frame = 0, active = true;
    const crossLoop = () => {
      if (!active) return;
      if (++frame >= CROSS_F) startStimulus();
      else requestAnimationFrame(crossLoop);
    };
    requestAnimationFrame(crossLoop);

    function startStimulus () {
      let showF = START_F, subF = 0, phase = 'show';
      const t0 = performance.now();

      (function anim () {
        if (!active) return;
        if (phase === 'show') {
          if (subF === 0) scr.textContent = w;
          if (++subF >= showF) { phase = 'mask'; subF = 0; scr.textContent = mask; }
        } else {
          const hideF = Math.max(0, CYCLE_F - showF);
          if (++subF >= hideF) { showF = Math.min(showF + STEP_F, CYCLE_F); phase = 'show'; subF = 0; }
        }
        requestAnimationFrame(anim);
      })();

      function trigger (e) {
        if (e instanceof KeyboardEvent && e.code !== 'Space') return;
        if (e instanceof PointerEvent) e.preventDefault();
        if (!active) return;
        active = false;

        removeEventListener('keydown', trigger);
        if (CFG.TOUCH_TRIGGER) removeEventListener('pointerdown', trigger);

        promptAnswer(Math.round(performance.now() - t0), w, grp, len);
      }
      addEventListener('keydown', trigger);
      if (CFG.TOUCH_TRIGGER) addEventListener('pointerdown', trigger, {passive: false});
    }
  };

  function promptAnswer (rt, obj) {
    scr.textContent   = '';
    ans.value         = '';
    ans.style.display = 'block';
    ans.readOnly      = false;
    vk.style.display  = 'none';
    setTimeout(() => ans.focus(), 40);
    resizeScr();

    function finish () {
      ans.blur();
      ans.style.display = 'none';

      results.push({
        ...obj,                    /* word, groupe, nblettres… */
        rt_ms      : rt,
        response   : ans.value.trim(),
        phase      : phaseLabel,
        participant: PID          /* ← identifiant aléatoire */
      });
      trial++;
      nextTrial();
    }
    ans.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); finish(); } };
  }

  nextTrial();
}

/********************************************************************
 * 7. FIN D’EXPÉRIENCE – ENVOI + AFFICHAGE DU PID
 ********************************************************************/
function endExperiment (results) {
  scr.style.fontSize = 'min(6vw,48px)';
  scr.textContent    = 'Merci, enregistrement…';

  fetch(CFG.API_URL, {
    method : 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(CFG.API_SECRET ? {'x-api-secret': CFG.API_SECRET} : {})
    },
    body   : JSON.stringify(results)
  })
  .then(r => {
    scr.innerHTML = r.ok
      ? `Merci de votre participation&nbsp;!<br><br>Votre identifiant est&nbsp;:<br><b>${PID}</b>`
      : `Enregistrement impossible (erreur&nbsp;${r.status}).<br>
         Veuillez noter votre identifiant&nbsp;:<br><b>${PID}</b>`;
  })
  .catch(() => {
    scr.innerHTML = `Problème réseau.<br>
      Veuillez noter votre identifiant&nbsp;:<br><b>${PID}</b>`;
  });
}

/********************************************************************
 * 8. CLAVIER VIRTUEL (inchangé)
 ********************************************************************/
function buildVK () {
  if (vk.firstChild) return;
  const rows = ['QWERTZUIOP', 'ASDFGHJKL', 'YXCVBNM', 'ÇÉÈÊÏÔ←↵'];
  rows.forEach(r => {
    const d = document.createElement('div'); d.className = 'krow';
    [...r].forEach(ch => {
      const b = document.createElement('button'); b.className = 'key';
      b.textContent = ch;
      d.appendChild(b);
    });
    vk.appendChild(d);
  });
}

/********************************************************************
 * 9. LANCEMENT
 ********************************************************************/
page_Hz();
