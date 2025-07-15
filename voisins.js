/* ***************************************************************************
 * EXPÉRIENCE  –  Collecte de données vers Azure SQL (Function HTTP)
 * ***************************************************************************/
'use strict';

/********************************************************************
 * 0. CONFIGURATION
 ********************************************************************/
const CFG = {
  XLSX_FILE      : "Lexique.xlsx",
  PRACTICE_WORDS : ["PAIN","EAU"],
  TOUCH_TRIGGER  : true,
  TAGS           : ["LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD"],
  N_PER_FEUIL_TAG: 5,
  MAX_TRY_TAG    : 1000,
  MAX_TRY_FULL   : 1000,
  NUM_BASE       : ["nblettres","nbphons","old20","pld20"],
  CYCLE_MS       : 350,
  CROSS_MS       : 500,
  MEAN_FACTOR_OLDPLD : .35,
  MEAN_DELTA     : {letters:.68, phons:.68},
  SD_MULT        : {letters:2, phons:2, old20:.28, pld20:.28, freq:1.9},
  HZ             : null,            // défini après choix participant

  // Paramètres API (à personnaliser)
  API_URL   : "/api/save_results",
  API_KEY   : "",
  API_SECRET: "udzKkYgnwQnfs7LW2Oi3xwgfhDhYiucZaXZrV4sY"
};

/********************************************************************
 * 1. OUTILS GÉNÉRAUX
 ********************************************************************/
const $ = s => document.querySelector(s);
const page = $('#page');
const scr  = $('#scr');
const ans  = $('#ans');
const vk   = $('#vk');
const rng  = () => Math.random();
const shuffled = a => [...a].sort(() => rng() - .5);
const mean     = a => a.reduce((s,x)=>s+x,0)/a.length;
const std      = a => {const m=mean(a); return Math.sqrt(mean(a.map(x=>(x-m)**2)));};
const pick     = (a,n)=>shuffled(a).slice(0,n);
const toFloat  = v => typeof v==="number"?v:parseFloat(String(v).replace(/[\s,]/g,"."));

// ---------- ANONYMOUS-ID : fonction et variable globale ----------
const randomID = () =>
  [...Array(6)]
    .map(()=>"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
      .charAt(Math.floor(Math.random()*36)))
    .join('');
const PID = randomID();      // code anonyme attribué à ce participant
// -----------------------------------------------------------------

/********************************************************************
 * 2. LECTURE .XLSX + TIRAGE 80 MOTS
 ********************************************************************/
async function loadSheets(){
  const data = await fetch(CFG.XLSX_FILE).then(r=>r.arrayBuffer());
  const wb   = XLSX.read(data,{type:'array'});
  const shNames = wb.SheetNames.filter(s=>s.toLowerCase().startsWith('feuil'));
  if(shNames.length!==4) throw "Il faut exactement 4 feuilles Feuil1…Feuil4";

  const feuilles={}, allFreq=new Set();
  for(const sh of shNames){
    const json = XLSX.utils.sheet_to_json(wb.Sheets[sh],{defval:null,raw:false});
    const cols = Object.keys(json[0]).map(c=>c.trim().toLowerCase());
    const need = ["ortho","old20","pld20","nblettres","nbphons"];
    need.forEach(c=>{if(!cols.includes(c)) throw `Colonne ${c} manquante dans ${sh}`});
    const freqCols = cols.filter(c=>c.startsWith('freq'));
    freqCols.forEach(c=>allFreq.add(c));

    const df=json.filter(r=>need.every(k=>r[k]!=null)).map(r=>{
      const o={};
      [...need,...freqCols].forEach(k=>o[k]=toFloat(r[k]));
      o.ortho=String(r.ortho).toUpperCase();
      return o;
    });
    const stats={};
    CFG.NUM_BASE.forEach(c=>stats['m_'+c]=mean(df.map(r=>r[c])));
    [...CFG.NUM_BASE,...freqCols].forEach(c=>stats['sd_'+c]=std(df.map(r=>r[c])));
    feuilles[sh]={df,stats,freqCols};
  }
  feuilles.allFreqCols=[...allFreq];
  return feuilles;
}

function masks(r,st){return{
  LOW_OLD : r.old20 < st.m_old20,
  HIGH_OLD: r.old20 > st.m_old20,
  LOW_PLD : r.pld20 < st.m_pld20,
  HIGH_PLD: r.pld20 > st.m_pld20
};}

function meanLpOK(sub,st){
  return Math.abs(mean(sub.map(r=>r.nblettres))-st.m_nblettres)<=CFG.MEAN_DELTA.letters*st.sd_nblettres &&
         Math.abs(mean(sub.map(r=>r.nbphons))-st.m_nbphons)<=CFG.MEAN_DELTA.phons*st.sd_nbphons;
}
function sdOK(sub,st,fq){
  const v=a=>std(a);
  return v(sub.map(r=>r.nblettres))<=st.sd_nblettres*CFG.SD_MULT.letters &&
         v(sub.map(r=>r.nbphons))  <=st.sd_nbphons  *CFG.SD_MULT.phons   &&
         v(sub.map(r=>r.old20))    <=st.sd_old20    *CFG.SD_MULT.old20   &&
         v(sub.map(r=>r.pld20))    <=st.sd_pld20    *CFG.SD_MULT.pld20   &&
         fq.every(c=>v(sub.map(r=>r[c]))<=st['sd_'+c]*CFG.SD_MULT.freq);
}

function pickFive(tag,feuille,used,F){
  const {df,stats:st,freqCols:fq}=F[feuille];
  const pool = df.filter(r=>masks(r,st)[tag] && !used.has(r.ortho));
  if(pool.length < CFG.N_PER_FEUIL_TAG) return null;

  for(let i=0;i<CFG.MAX_TRY_TAG;i++){
    const samp = pick(pool, CFG.N_PER_FEUIL_TAG);
    const mOld = mean(samp.map(r=>r.old20));
    const mPld = mean(samp.map(r=>r.pld20));
    if(tag==="LOW_OLD" && mOld>=st.m_old20-CFG.MEAN_FACTOR_OLDPLD*st.sd_old20) continue;
    if(tag==="HIGH_OLD"&& mOld<=st.m_old20+CFG.MEAN_FACTOR_OLDPLD*st.sd_old20) continue;
    if(tag==="LOW_PLD" && mPld>=st.m_pld20-CFG.MEAN_FACTOR_OLDPLD*st.sd_pld20) continue;
    if(tag==="HIGH_PLD"&& mPld<=st.m_pld20+CFG.MEAN_FACTOR_OLDPLD*st.sd_pld20) continue;
    if(!meanLpOK(samp,st) || !sdOK(samp,st,fq)) continue;
    samp.forEach(r=>r.groupe=tag);
    return samp;
  }
  return null;
}

async function buildSheet(){
  const F = await loadSheets();
  const shNames = Object.keys(F).filter(k=>k!=="allFreqCols");
  for(let t=0;t<CFG.MAX_TRY_FULL;t++){
    const take={}, groups=[]; shNames.forEach(sh=>take[sh]=new Set()); let ok=true;
    for(const tag of CFG.TAGS){
      const bloc=[];
      for(const sh of shNames){
        const sub = pickFive(tag, sh, take[sh], F);
        if(!sub){ ok=false; break; }
        bloc.push(...sub); sub.forEach(r=>take[sh].add(r.ortho));
      }
      if(!ok) break;
      groups.push(shuffled(bloc));
    }
    if(ok) return groups.flat();
  }
  throw "Impossible de générer la liste de 80 mots.";
}

/********************************************************************
 * 3. VARIABLES DÉRIVÉES DE LA FRÉQUENCE
 ********************************************************************/
let FRAME_MS,CYCLE_F,CROSS_F,SCALE,START_F,STEP_F,IS_TOUCH;
function setHz(hz){
  CFG.HZ = hz;
  FRAME_MS = 1000 / hz;
  CYCLE_F  = Math.round(CFG.CYCLE_MS / FRAME_MS);
  CROSS_F  = Math.round(CFG.CROSS_MS / FRAME_MS);
  SCALE    = hz / 60;
  START_F  = 1 * SCALE;
  STEP_F   = 1 * SCALE;
  IS_TOUCH = ('ontouchstart' in window) || (navigator.maxTouchPoints>0);
}

/********************************************************************
 * 4. RESIZE
 ********************************************************************/
function resizeScr(){
  const b=Math.min(innerWidth,innerHeight);
  scr.style.fontSize = Math.max(Math.round(b*0.08),26)+'px';
  ans.style.fontSize = Math.max(Math.round(b*0.054),20)+'px';
  ans.style.width    = Math.min(innerWidth*0.7,650)+'px';
}
addEventListener('resize',resizeScr);
addEventListener('orientationchange',resizeScr);
addEventListener('load',()=>{setTimeout(resizeScr,80);});

/********************************************************************
 * 5. PHASES
 ********************************************************************/
function page_Welcome(){

  /* 1. On autorise le défilement vertical et on aligne le contenu en haut */
  page.style.justifyContent = 'flex-start';   // plus au centre verticalement
  page.style.overflowY      = 'auto';         // scroll si nécessaire
  page.style.padding        = '2rem 1rem';    // un peu d’air sur les côtés

  /* 2. Contenu HTML */
  page.innerHTML = `
    <h2 style="margin-top:0">Conformité éthique</h2>

    <ul style="max-width:700px;text-align:left;line-height:1.4;margin:0 auto;">
      <li><strong>Aucun risque&nbsp;:</strong> Cette expérience ne présente aucun danger physique ni psychologique.</li>
      <li><strong>Participation volontaire&nbsp;:</strong> Vous êtes libre de participer ou de quitter l’expérience à tout moment.</li>
      <li><strong>Confidentialité et anonymat&nbsp;:</strong>
        <ul>
          <li>Aucune donnée personnelle n’est collectée.</li>
          <li>Les réponses sont enregistrées de manière strictement anonyme.</li>
          <li>Les données recueillies sont utilisées uniquement à des fins de recherche scientifique.</li>
        </ul>
      </li>
    </ul>

    <h3>Contact</h3>
    <p style="max-width:700px;margin:0 auto;">
      Pour toute question ou information complémentaire, vous pouvez contacter le responsable de l’étude&nbsp;:<br>
      <a href="mailto:prenom.nom@univ.fr">prenom.nom@univ.fr</a> <!-- remplacez par l’adresse réelle -->
    </p>

    <p style="max-width:700px;margin:24px auto 0;">
      Sur la base des informations qui précèdent, pour confirmer votre accord sur les points mentionnés
      et débuter l'étude, cliquez sur « Je donne mon accord ».
    </p>

    <div style="margin:32px 0;display:flex;gap:20px;flex-wrap:wrap;justify-content:center;">
      <button id="btnOk" style="flex:1 1 180px;min-width:150px;">Je donne mon accord</button>
      <button id="btnNo" style="flex:1 1 180px;min-width:150px;">Je ne donne pas mon accord</button>
    <br>
    </div>
  `;

  /* 3. Gestion des boutons */
  $('#btnOk').onclick = () => {
    /* On remet le style du conteneur comme sur les autres pages */
    page.style.justifyContent = 'center';
    page.style.overflowY      = 'hidden';
    page.style.padding        = '0';

    page_Hz();   // on passe à l’étape suivante (mesure des Hz)
  };

  $('#btnNo').onclick = () => {
    page.style.overflowY = 'hidden';
    page.innerHTML = `
      <h2>Fin de l’expérience</h2>
      <p>Vous avez choisi de ne pas participer. Aucune donnée n’a été enregistrée.</p>
    `;
  };
}
function page_Hz(){
  page.innerHTML=`
    <h2>Veuillez mesurer la fréquence de votre écran pour calibrer l’expérience.</h2>
    <div id="hzVal" style="font-size:28px;">--</div>
    <button id="mes">Mesurer</button>
    <div style="margin-top:20px">
      <button id="hz60">Utiliser 60 Hz</button>
      <button id="hz120">Utiliser 120 Hz</button>
      <button id="hzOther">Autre</button>
    </div>`;
  $('#mes').onclick   = mesureHz;
  $('#hz60').onclick  = ()=>startLoading(60);
  $('#hz120').onclick = ()=>startLoading(120);
  $('#hzOther').onclick = page_Incompatible;
}
function mesureHz(){
  const lbl = $('#hzVal');
  lbl.textContent = 'Mesure…';
  let f = 0, t0 = performance.now();

  (function loop(){
    f++;
    if (f < 120) {
      requestAnimationFrame(loop);
    } else {
      // fréquence brute
      const freq = f*1000/(performance.now()-t0);

      // affichage arrondi 60 / 120 Hz
      let txt;
      if (freq >= 58.0 && freq <= 62.0) {
        txt = '60 Hz';
      } else if (freq >= 118.0 && freq <= 122.0) {
        txt = '120 Hz';
      } else {
        txt = '≈ ' + freq.toFixed(1) + ' Hz';
      }
      lbl.textContent = txt;
    }
  })();
}
function page_Incompatible(){
  scr.style.display='none'; page.style.display='flex';
  page.innerHTML=`<h2>Désolé</h2><p>Cette expérience nécessite un écran 60 Hz ou 120 Hz.</p>`;
}

/* ---- Tirage auto puis instructions ---- */

let WORDS80=[];
function startLoading(hzSel){
  setHz(hzSel);
  page.innerHTML=`<h2>Préparation…</h2><p id="stat">Tirage aléatoire des 80 mots…</p>`;
  buildSheet().then(list=>{
    WORDS80 = list.map(r=>({
     word            : r.ortho,
     groupe          : r.groupe,
     nblettres       : r.nblettres,
     nbphons         : r.nbphons,
     old20           : r.old20,
     pld20           : r.pld20,
     freqfilms2      : r.freqfilms2,
     freqlemfilms2   : r.freqlemfilms2,
     freqlemlivres   : r.freqlemlivres,
     freqlivres      : r.freqlivres
   }));
    page_Intro();
  }).catch(e=>{page.innerHTML='<p style="color:red">'+e+'</p>';});
}

function page_Intro(){
  page.innerHTML=`<h2>Instructions</h2>
  <p>Code anonyme du participant : <strong>${PID}</strong><br>
     (notez-le si vous souhaitez, plus tard, recevoir vos résultats).</p>
  <p>Fixez la croix. Un mot apparaîtra brièvement, masqué par des ###, puis réapparaîtra en alternance, de plus en plus lentement.
Quand vous reconnaissez le mot, appuyez sur ESPACE ou touchez l’écran avec le doigt, tapez le mot, puis validez avec Entrée ⏎. Attention aux accents et pluriels.
Une phase d’essai avec 2 mots précède le test principal de 80 mots.</p>
  <button id="startP">Commencer la familiarisation</button>`;
  $('#startP').onclick=page_Practice;
}

function page_Practice(){
  page.style.display='none'; scr.style.display='block';
  runBlock(CFG.PRACTICE_WORDS,'practice',page_TestReady);
}

function page_TestReady(){
  scr.style.display='none'; page.style.display='flex';
  page.innerHTML=`<h2>Fin de l’entraînement</h2>
  <button id="goFull">Commencer le test (plein écran)</button>`;
  $('#goFull').onclick=()=>{
    document.documentElement.requestFullscreen?.();
    page.style.display='none'; scr.style.display='block';
    runBlock(shuffled(WORDS80),'main',endExperiment);
  };
}

/********************************************************************
 * 6. RUN BLOCK  (présentation / réponses)
 ********************************************************************/
function runBlock(wordArr, phaseLabel, onFinish){
  let trial=0, results=[];

  const nextTrial = ()=>{
    if(trial>=wordArr.length){onFinish(results); return;}
    const obj=wordArr[trial];
    const w   = obj.word || obj;
    const mask="#".repeat(w.length);
    scr.textContent="+"; let frame=0, active=true;

    const crossLoop=()=>{ if(!active) return;
      if(++frame>=CROSS_F) startStimulus(); else requestAnimationFrame(crossLoop); };
    requestAnimationFrame(crossLoop);

    function startStimulus(){
      let showF=START_F, subF=0, phase="show";
      const t0=performance.now();

      (function anim(){
        if(!active) return;
        if(phase==="show"){
          if(subF===0) scr.textContent=w;
          if(++subF>=showF){phase="mask"; subF=0; scr.textContent=mask;}
        }else{
          const hideF=Math.max(0,CYCLE_F-showF);
          if(++subF>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F); phase="show"; subF=0;}
        }
        requestAnimationFrame(anim);
      })();

      function trigger(e){
        if(e instanceof KeyboardEvent && e.code!=="Space") return;
        if(e instanceof PointerEvent) e.preventDefault();
        if(!active) return; active=false;

        removeEventListener('keydown',trigger);
        if(CFG.TOUCH_TRIGGER) removeEventListener('pointerdown',trigger);

        promptAnswer(Math.round(performance.now()-t0), obj);   // correction
      }
      addEventListener('keydown',trigger);
      if(CFG.TOUCH_TRIGGER) addEventListener('pointerdown',trigger,{passive:false});
    }
  };

  /* ----------- PROMPT ANSWER (corrigé + clavier virtuel) ----------- */
  function promptAnswer(rt, obj){
    scr.textContent   = "";
    ans.value         = "";
    ans.style.display = 'block';

    let vkListener=null;

    if(IS_TOUCH){                       // --- mobile / tactile
      buildVK();
      ans.readOnly     = true;          // bloque le clavier système
      vk.style.display = 'block';

      vkListener = e=>{
        const k = e.target.closest('.key');
        if(!k) return;
        const ch = k.textContent;
        if(ch === '←'){
          ans.value = ans.value.slice(0,-1);
        }else if(ch === '↵'){
          finish();
        }else{
          ans.value += ch;
        }
      };
      vk.addEventListener('click', vkListener);
    }else{                              // --- desktop
      ans.readOnly     = false;
      vk.style.display = 'none';
    }

    setTimeout(()=>ans.focus(),40);
    resizeScr();

    ans.onkeydown = e=>{
      if(e.key==="Enter"){
        e.preventDefault();
        finish();
      }
    };

    function finish(){
      if(vkListener) vk.removeEventListener('click', vkListener);
      ans.blur(); ans.style.display='none'; vk.style.display='none';

      results.push({
        ...obj,
        rt_ms      : rt,
        response   : ans.value.trim(),
        phase      : phaseLabel,
        participant: PID                     // ---------- ANONYMOUS-ID
      });
      trial++;
      nextTrial();
    }
  }

  nextTrial();
}

/********************************************************************
 * 7. FIN D’EXPÉRIENCE — ENVOI VERS AZURE FUNCTION
 ********************************************************************/
function endExperiment(results){
  scr.style.fontSize="min(6vw,48px)";
  scr.textContent="Merci, enregistrement…";

  fetch(CFG.API_URL,{
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      ...(CFG.API_SECRET?{"x-api-secret":CFG.API_SECRET}:{})
    },
    body:JSON.stringify(results)
  })
  .then(r=>scr.textContent=r.ok?"Merci !":"Erreur "+r.status)
  .catch(()=>scr.textContent="Erreur réseau");
}

/********************************************************************
 * 8. CLAVIER VIRTUEL
 ********************************************************************/
function buildVK(){
  if(vk.firstChild) return;             // déjà construit
  const rows=["QWERTZUIOP","ASDFGHJKL","YXCVBNM","ÇÉÈÊÏÔ←↵"];
  rows.forEach(r=>{
    const d=document.createElement('div'); d.className='krow';
    [...r].forEach(ch=>{
      const b=document.createElement('button'); b.className='key';
      b.textContent=ch; d.appendChild(b);
    });
    vk.appendChild(d);
  });
}

/********************************************************************
 * 9. LANCEMENT
 ********************************************************************/
buildVK();           // construit le clavier une fois
page_Welcome();      // <— c’est elle qui s’affichera d’abord
