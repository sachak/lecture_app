'use strict';

/********************************************************************
 * 0.  CONFIG de base (sera complétée quand le participant choisit Hz)
 *******************************************************************/
const CFG = {
  XLSX_FILE      : "Lexique.xlsx",
  PRACTICE_WORDS : ["PAIN","EAU"],
  TOUCH_TRIGGER  : true,           // tap écran actif
  // autres constantes identiques à la version précédente …
  TAGS:["LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD"],
  N_PER_FEUIL_TAG:5,MAX_TRY_TAG:1000,MAX_TRY_FULL:1000,
  NUM_BASE:["nblettres","nbphons","old20","pld20"],
  CYCLE_MS:350,CROSS_MS:500,
  MEAN_FACTOR_OLDPLD:.35,
  MEAN_DELTA:{letters:.68,phons:.68},
  SD_MULT:{letters:2,phons:2,old20:.28,pld20:.28,freq:1.9}
};

/********************************************************************
 * 1.  OUTILS
 *******************************************************************/
const $ = sel => document.querySelector(sel);
const page = $('#page'), scr=$('#scr'), ans=$('#ans'), vk=$('#vk');
const rng = () => Math.random(), shuffled=a=>[...a].sort(()=>rng()-.5);
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length;
const std=a=>{const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)**2)));};
const pick=(a,n)=>shuffled(a).slice(0,n);
const toFloat=v=>typeof v==="number"?v:parseFloat(String(v).replace(/[\s,]/g,"."));

/********************************************************************
 * 2.  FEUILLES EXCEL  +  TIRAGE (identiques à la version précédente)
 *******************************************************************/
async function loadSheets(){ /* … même code que précédemment … */ }
function buildSheet(){ /* … même code que précédemment … */ }

/********************************************************************
 * 3.  Variables dérivées (ré-initialisées après choix de la fréquence)
 *******************************************************************/
let FRAME_MS,CYCLE_F,CROSS_F,SCALE,START_F,STEP_F,IS_TOUCH;
function setHz(hz){
  CFG.HZ = hz;
  FRAME_MS = 1000/CFG.HZ;
  CYCLE_F  = Math.round(CFG.CYCLE_MS/FRAME_MS);
  CROSS_F  = Math.round(CFG.CROSS_MS/FRAME_MS);
  SCALE    = CFG.HZ/60;
  START_F  = 1*SCALE;
  STEP_F   = 1*SCALE;
  IS_TOUCH = ('ontouchstart' in window)||(navigator.maxTouchPoints>0);
}

/********************************************************************
 * 4.  PHASE 1 – écran « Choix / mesure Hz »
 *******************************************************************/
function page_Hz(){
  page.innerHTML = `
    <h2>1. Vérification de la fréquence d’écran</h2>
    <div id="hzVal" style="font-size:28px;margin:12px">--</div>
    <button id="mes">Mesurer</button>
    <div style="margin-top:20px">
      <button id="hz60">Utiliser 60 Hz</button>
      <button id="hz120">Utiliser 120 Hz</button>
    </div>`;
  $('#mes').onclick = mesureHz;
  $('#hz60').onclick = ()=>goIntro(60);
  $('#hz120').onclick=()=>goIntro(120);
  scr.style.display='none'; ans.style.display='none'; vk.style.display='none';
}

function mesureHz(){
  const lbl=$('#hzVal'); lbl.textContent='Mesure…'; let f=0,t0=performance.now();
  function loop(){
    f++; if(f<120){requestAnimationFrame(loop);}
    else{
      const hz=f*1000/(performance.now()-t0);
      lbl.textContent='≈ '+hz.toFixed(1)+' Hz';
    }
  }
  requestAnimationFrame(loop);
}

function goIntro(hzSel){ setHz(hzSel); page_Intro(); }

/********************************************************************
 * 5.  PHASE 2 – instructions + génération des mots
 *******************************************************************/
let SHEET80=[];                     // sera rempli par buildSheet()
function page_Intro(){
  page.innerHTML = `<h2>2. Présentation de la tâche</h2>
<p>Écran sélectionné : <b>${CFG.HZ} Hz</b></p>
<p>Croix 500 ms → mot très bref → masque (#####).<br>
Touchez l’écran <i>ou</i> barre ESPACE dès que le mot est reconnu,<br>
puis tapez le mot (clavier virtuel sur mobile).</p>
<p>2 essais d’entraînement puis 80 essais de test.</p>
<button id="load">Préparer la liste et commencer la familiarisation</button>`;
  $('#load').onclick=async()=>{
    $('#load').disabled=true; $('#load').textContent='Tirage aléatoire…';
    SHEET80 = await buildSheet();                 // chargement + tirage
    $('#load').textContent='Commencer la familiarisation';
    $('#load').disabled=false;
    $('#load').onclick = page_Practice;
  };
}

/********************************************************************
 * 6.  PHASE 3 – familiarisation (2 mots)
 *******************************************************************/
function page_Practice(){
  page.style.display='none'; scr.style.display='block';
  runBlock(CFG.PRACTICE_WORDS,'practice',()=>page_TestReady());
}

/********************************************************************
 * 7.  PHASE 4 – bouton « Commencer le test » + plein-écran
 *******************************************************************/
function page_TestReady(){
  scr.style.display='none'; page.style.display='flex';
  page.innerHTML=`<h2>Fin de l’entraînement</h2>
<p>Quand vous êtes prêt·e&nbsp;:</p>
<button id="goFull">Commencer le test (plein écran)</button>`;
  $('#goFull').onclick=()=>{
    document.documentElement.requestFullscreen?.();
    page.style.display='none'; scr.style.display='block';
    runBlock(shuffled(SHEET80.map(r=>r.ortho)),'main', endExperiment);
  };
}

/********************************************************************
 * 8.  PHASE 5 – bloc (fonction générique : pratique / test)
 *******************************************************************/
function runBlock(wordArray, phaseLabel, onFinish){
  let trial=0, results=[];

  const finishAnswer = rt => {
    results.push({word:wordArray[trial],rt_ms:rt,response:ans.value.trim(),phase:phaseLabel});
    trial++; nextTrial();
  };

  const promptAnswer = rt =>{
    scr.textContent=''; ans.value=''; ans.style.display='block';
    if(IS_TOUCH){ans.readOnly=true; buildVK(); vk.style.display='flex';}
    else{ans.readOnly=false; setTimeout(()=>ans.focus(),40);}
    function keyEnter(e){if(e.key==="Enter"){e.preventDefault();finishAnswer(rt);}}
    addEventListener('keydown',keyEnter,{once:true});
    if(IS_TOUCH) finishAnswer.rt=rt;            // pour VK ↵
    finishAnswer.fn=( )=>finishAnswer(rt);      // pour VK ↵
    window.finishAnswer=finishAnswer.fn;        // export pour VK
  };

  const nextTrial = ()=>{
    if(trial>=wordArray.length){ ans.style.display='none'; vk.style.display='none'; onFinish(results); return;}
    const w=wordArray[trial],mask="#".repeat(w.length); let active=true;
    scr.textContent="+"; let frame=0;
    const crossLoop=()=>{if(!active)return;
      if(++frame>=CROSS_F)startStimulus();else requestAnimationFrame(crossLoop);};
    requestAnimationFrame(crossLoop);

    function startStimulus(){
      let showF=START_F,subF=0,phase="show";
      const t0=performance.now();
      function anim(){
        if(!active)return;
        if(phase==="show"){
          if(subF===0) scr.textContent=w;
          if(++subF>=showF){phase="mask";subF=0;scr.textContent=mask;}
        }else{
          const hideF=Math.max(0,CYCLE_F-showF);
          if(++subF>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F);phase="show";subF=0;}
        } requestAnimationFrame(anim);
      } requestAnimationFrame(anim);

      function trig(e){
        if(e instanceof KeyboardEvent && e.code!=="Space") return;
        if(e instanceof PointerEvent) e.preventDefault();
        if(!active)return; active=false;
        removeEventListener('keydown',trig);
        if(CFG.TOUCH_TRIGGER) removeEventListener('pointerdown',trig);
        promptAnswer(Math.round(performance.now()-t0));
      }
      addEventListener('keydown',trig);
      if(CFG.TOUCH_TRIGGER) addEventListener('pointerdown',trig,{passive:false});
    }
  };
  nextTrial();
}

/********************************************************************
 * 9.  FIN D’EXPÉRIENCE
 *******************************************************************/
function endExperiment(res){
  scr.style.fontSize="min(6vw,48px)";
  scr.textContent="Merci !";
  const csv=["word;rt_ms;response;phase",...res.map(r=>
        `${r.word};${r.rt_ms};${r.response};${r.phase}`)].join("\n");
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  a.download="results.csv"; a.textContent="Télécharger les résultats";
  a.style.fontSize="min(6vw,32px)"; a.style.marginTop="30px";
  document.body.appendChild(a);

  if(typeof testableSubmit==="function") testableSubmit({csv});
}

/********************************************************************
 * 10.  CLAVIER VIRTUEL (identique)
 *******************************************************************/
function buildVK(){ if(vk.firstChild) return;
  const rows=["QWERTZUIOP","ASDFGHJKL","YXCVBNM","ÇÉÈÊÏÔ←↵"];
  rows.forEach(r=>{
    const d=document.createElement('div');d.className='krow';
    [...r].forEach(ch=>{
      const b=document.createElement('button');b.className='key';b.textContent=ch;d.appendChild(b);
    }); vk.appendChild(d);
  });
  vk.addEventListener('pointerdown',e=>{
    const t=e.target;if(!t.classList.contains('key')) return;
    e.preventDefault(); const k=t.textContent;
    if(k==="←") ans.value=ans.value.slice(0,-1);
    else if(k==="↵") window.finishAnswer?.();
    else ans.value+=k;
  },{passive:false});
}

/********************************************************************
 * 11.  DÉMARRAGE
 *******************************************************************/
page_Hz();          // écran 1 au chargement
