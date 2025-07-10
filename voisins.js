'use strict';

/********************************************************************
 * 0.  CONFIGURATION GLOBALE
 *******************************************************************/
const CFG = {
  XLSX_FILE      : "Lexique.xlsx",
  PRACTICE_WORDS : ["PAIN","EAU"],
  TOUCH_TRIGGER  : true,
  TAGS:["LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD"],
  N_PER_FEUIL_TAG:5, MAX_TRY_TAG:1000, MAX_TRY_FULL:1000,
  NUM_BASE:["nblettres","nbphons","old20","pld20"],
  CYCLE_MS:350, CROSS_MS:500,
  MEAN_FACTOR_OLDPLD:.35,
  MEAN_DELTA:{letters:.68,phons:.68},
  SD_MULT:{letters:2,phons:2,old20:.28,pld20:.28,freq:1.9},
  HZ:null               // sera défini après choix participant
};

/********************************************************************
 * 1.  OUTILS DIVERS
 *******************************************************************/
const $ = sel => document.querySelector(sel);
const page=$('#page'), scr=$('#scr'), ans=$('#ans'), vk=$('#vk');

const rng=()=>Math.random();
const shuffled=a=>[...a].sort(()=>rng()-.5);
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length;
const std =a=>{const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)**2)));};
const pick=(a,n)=>shuffled(a).slice(0,n);
const toFloat=v=>typeof v==="number"?v:parseFloat(String(v).replace(/[\s,]/g,"."));

/********************************************************************
 * 2.  LECTURE DE LEXIQUE.XLSX + TIRAGE 80 MOTS
 *******************************************************************/
async function loadSheets(){
  const data = await fetch(CFG.XLSX_FILE).then(r=>r.arrayBuffer());
  const wb   = XLSX.read(data,{type:"array"});
  const shNames = wb.SheetNames.filter(s=>s.toLowerCase().startsWith("feuil"));
  if(shNames.length!==4) throw "Il faut exactement 4 feuilles Feuil1…Feuil4";

  const feuilles={}, allFreq=new Set();
  for(const sh of shNames){
    const json = XLSX.utils.sheet_to_json(wb.Sheets[sh],{defval:null,raw:false});
    const cols = Object.keys(json[0]).map(c=>c.trim().toLowerCase());
    const need = ["ortho","old20","pld20","nblettres","nbphons"];
    need.forEach(c=>{if(!cols.includes(c))throw `Colonne manquante ${c} dans ${sh}`});
    const freqCols = cols.filter(c=>c.startsWith("freq"));
    freqCols.forEach(c=>allFreq.add(c));

    const df=json.filter(r=>need.every(k=>r[k]!=null)).map(r=>{
      const o={};
      [...need,...freqCols].forEach(k=>o[k]=toFloat(r[k]));
      o.ortho=String(r.ortho).toUpperCase();
      return o;
    });
    const stats={};
    CFG.NUM_BASE.forEach(c=>stats["m_"+c]=mean(df.map(r=>r[c])));
    [...CFG.NUM_BASE,...freqCols].forEach(c=>stats["sd_"+c]=std(df.map(r=>r[c])));
    feuilles[sh]={df,stats,freqCols};
  }
  feuilles.allFreqCols=[...allFreq];
  return feuilles;
}

function masks(r,st){return{
  LOW_OLD:r.old20<st.m_old20,  HIGH_OLD:r.old20>st.m_old20,
  LOW_PLD:r.pld20<st.m_pld20,  HIGH_PLD:r.pld20>st.m_pld20};}

function meanLpOK(sub,st){
  return Math.abs(mean(sub.map(r=>r.nblettres))-st.m_nblettres)<=CFG.MEAN_DELTA.letters*st.sd_nblettres &&
         Math.abs(mean(sub.map(r=>r.nbphons))-st.m_nbphons)<=CFG.MEAN_DELTA.phons*st.sd_nbphons;}
function sdOK(sub,st,fq){
  const v=a=>std(a);
  return v(sub.map(r=>r.nblettres))<=st.sd_nblettres*CFG.SD_MULT.letters &&
         v(sub.map(r=>r.nbphons))  <=st.sd_nbphons  *CFG.SD_MULT.phons   &&
         v(sub.map(r=>r.old20))    <=st.sd_old20    *CFG.SD_MULT.old20   &&
         v(sub.map(r=>r.pld20))    <=st.sd_pld20    *CFG.SD_MULT.pld20   &&
         fq.every(c=>v(sub.map(r=>r[c]))<=st["sd_"+c]*CFG.SD_MULT.freq);}

function pickFive(tag,feuille,used,F){
  const {df,stats:st,freqCols:fq}=F[feuille];
  const pool=df.filter(r=>masks(r,st)[tag] && !used.has(r.ortho));
  if(pool.length<CFG.N_PER_FEUIL_TAG) return null;
  for(let i=0;i<CFG.MAX_TRY_TAG;i++){
    const samp=pick(pool,CFG.N_PER_FEUIL_TAG);
    const mOld=mean(samp.map(r=>r.old20)), mPld=mean(samp.map(r=>r.pld20));
    if(tag==="LOW_OLD" && mOld>=st.m_old20-CFG.MEAN_FACTOR_OLDPLD*st.sd_old20) continue;
    if(tag==="HIGH_OLD"&& mOld<=st.m_old20+CFG.MEAN_FACTOR_OLDPLD*st.sd_old20) continue;
    if(tag==="LOW_PLD" && mPld>=st.m_pld20-CFG.MEAN_FACTOR_OLDPLD*st.sd_pld20) continue;
    if(tag==="HIGH_PLD"&& mPld<=st.m_pld20+CFG.MEAN_FACTOR_OLDPLD*st.sd_pld20) continue;
    if(!meanLpOK(samp,st)||!sdOK(samp,st,fq)) continue;
    return samp;
  }
  return null;
}

async function buildSheet(){
  const F=await loadSheets();
  const shNames=Object.keys(F).filter(k=>k!=="allFreqCols");
  for(let t=0;t<CFG.MAX_TRY_FULL;t++){
    const take={}, groups=[];
    shNames.forEach(sh=>take[sh]=new Set());
    let ok=true;
    for(const tag of CFG.TAGS){
      const bloc=[];
      for(const sh of shNames){
        const sub=pickFive(tag,sh,take[sh],F);
        if(!sub){ok=false;break;}
        bloc.push(...sub); sub.forEach(r=>take[sh].add(r.ortho));
      }
      if(!ok) break;
      groups.push(shuffled(bloc));
    }
    if(ok) return groups.flat();
  }
  throw "Impossible de générer la liste.";
}

/********************************************************************
 * 3.  VARIABLES DÉRIVÉES DE LA FRÉQUENCE
 *******************************************************************/
let FRAME_MS,CYCLE_F,CROSS_F,SCALE,START_F,STEP_F,IS_TOUCH;
function setHz(hz){
  CFG.HZ=hz;
  FRAME_MS=1000/hz;
  CYCLE_F=Math.round(CFG.CYCLE_MS/FRAME_MS);
  CROSS_F=Math.round(CFG.CROSS_MS/FRAME_MS);
  SCALE=hz/60;
  START_F=1*SCALE;
  STEP_F=1*SCALE;
  IS_TOUCH=('ontouchstart' in window)||(navigator.maxTouchPoints>0);
}

/********************************************************************
 * 4.  PETITES FONCTIONS UI
 *******************************************************************/
function resizeScr(){
  const b=Math.min(innerWidth,innerHeight);
  scr.style.fontSize=Math.max(Math.round(b*0.08),26)+'px';
  ans.style.fontSize=Math.max(Math.round(b*0.054),20)+'px';
  ans.style.width=Math.min(innerWidth*0.7,650)+'px';
}
addEventListener('resize',resizeScr);
addEventListener('orientationchange',resizeScr);
addEventListener('load',()=>{document.body.focus();setTimeout(resizeScr,80);});

/********************************************************************
 * 5.  PHASES
 *******************************************************************/
function page_Hz(){
  page.innerHTML=`
    <h2>1. Vérification de la fréquence d’écran</h2>
    <div id="hzVal" style="font-size:28px;">--</div>
    <button id="mes">Mesurer</button>
    <div style="margin-top:20px">
      <button id="hz60">Utiliser 60 Hz</button>
      <button id="hz120">Utiliser 120 Hz</button>
    </div>`;
  $('#mes').onclick=mesureHz;
  $('#hz60').onclick=()=>goIntro(60);
  $('#hz120').onclick=()=>goIntro(120);
}
function mesureHz(){
  const lbl=$('#hzVal'); lbl.textContent='Mesure…'; let f=0,t0=performance.now();
  (function loop(){f++; if(f<120){requestAnimationFrame(loop);}else{
    lbl.textContent='≈ '+(f*1000/(performance.now()-t0)).toFixed(1)+' Hz';
  }})();
}
function goIntro(h){setHz(h); page_Intro();}

let WORDS80=[];
function page_Intro(){
  page.innerHTML=`<h2>2. Présentation de la tâche</h2>
<p>Écran sélectionné : <b>${CFG.HZ} Hz</b></p>
<p>Croix 500 ms → mot bref → masque (#####).<br>
Touchez l’écran ou barre ESPACE dès que vous reconnaissez le mot,<br>
puis tapez-le (clavier virtuel sur mobile).</p>
<p>2 essais d’entraînement puis 80 essais de test.</p>
<button id="load">Préparer la liste et commencer la familiarisation</button>`;
  $('#load').onclick=async()=>{
    $('#load').disabled=true; $('#load').textContent='Tirage aléatoire…';
    WORDS80 = (await buildSheet()).map(r=>r.ortho);
    $('#load').textContent='Commencer la familiarisation';
    $('#load').disabled=false;
    $('#load').onclick=page_Practice;
  };
}

function page_Practice(){
  page.style.display='none'; scr.style.display='block';
  runBlock(CFG.PRACTICE_WORDS,'practice',page_TestReady);
}

function page_TestReady(){
  scr.style.display='none'; page.style.display='flex';
  page.innerHTML=`<h2>Fin de l’entraînement</h2>
<p>Quand vous êtes prêt·e :</p>
<button id="goFull">Commencer le test (plein écran)</button>`;
  $('#goFull').onclick=()=>{
    document.documentElement.requestFullscreen?.();
    page.style.display='none'; scr.style.display='block';
    runBlock(shuffled(WORDS80),'main',endExperiment);
  };
}

/********************************************************************
 * 6.  RUN BLOCK  (avec correctif touche ENTER)
 *******************************************************************/
function runBlock(wordArr, phaseLabel, onFinish){
  let trial=0, results=[];

  const nextTrial = ()=>{
    if(trial>=wordArr.length){ onFinish(results); return;}
    scr.textContent="+"; let frame=0, active=true;
    const crossLoop=()=>{if(!active)return;
      if(++frame>=CROSS_F)startStimulus();else requestAnimationFrame(crossLoop);};
    requestAnimationFrame(crossLoop);

    function startStimulus(){
      const w=wordArr[trial], mask="#".repeat(w.length); let showF=START_F, subF=0, phase="show";
      const t0=performance.now();
      (function anim(){
        if(!active)return;
        if(phase==="show"){
          if(subF===0) scr.textContent=w;
          if(++subF>=showF){phase="mask";subF=0;scr.textContent=mask;}
        }else{
          const hideF=Math.max(0,CYCLE_F-showF);
          if(++subF>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F);phase="show";subF=0;}
        } requestAnimationFrame(anim);
      })();

      function trigger(e){
        if(e instanceof KeyboardEvent && e.code!=="Space") return;
        if(e instanceof PointerEvent) e.preventDefault();
        if(!active)return; active=false;
        removeEventListener('keydown',trigger);
        if(CFG.TOUCH_TRIGGER) removeEventListener('pointerdown',trigger);
        promptAnswer(Math.round(performance.now()-t0),w);
      }
      addEventListener('keydown',trigger);
      if(CFG.TOUCH_TRIGGER) addEventListener('pointerdown',trigger,{passive:false});
    }
  };

  function promptAnswer(rt, currentWord){
    /* affichage champ réponse */
    scr.textContent=""; ans.value=""; ans.style.display="block";
    if(IS_TOUCH){ ans.readOnly=true; buildVK(); vk.style.display='flex'; }
    else{ ans.readOnly=false; setTimeout(()=>ans.focus(),40); }
    resizeScr();

    /* fonction de clôture */
    function finish(){
      ans.removeEventListener('keydown',onEnter);
      ans.style.display='none'; vk.style.display='none';
      results.push({word:currentWord,rt_ms:rt,response:ans.value.trim(),phase:phaseLabel});
      trial++; nextTrial();
    }

    /* ENTER (clavier physique) */
    function onEnter(ev){
      if(ev.key==="Enter" || ev.keyCode===13){
        ev.preventDefault(); finish();
      }
    }
    ans.addEventListener('keydown',onEnter);

    /* ENTER du clavier virtuel */
    window.finishAnswer = finish;
  }

  nextTrial();
}

/********************************************************************
 * 7.  FIN EXPÉRIMENTATION
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
 * 8.  CLAVIER VIRTUEL
 *******************************************************************/
function buildVK(){ if(vk.firstChild) return;
  const rows=["QWERTZUIOP","ASDFGHJKL","YXCVBNM","ÇÉÈÊÏÔ←↵"];
  rows.forEach(r=>{
    const d=document.createElement('div'); d.className='krow';
    [...r].forEach(ch=>{
      const b=document.createElement('button'); b.className='key'; b.textContent=ch;
      d.appendChild(b);
    }); vk.appendChild(d);
  });
  vk.addEventListener('pointerdown',e=>{
    const t=e.target; if(!t.classList.contains('key')) return;
    e.preventDefault(); const k=t.textContent;
    if(k==="←") ans.value=ans.value.slice(0,-1);
    else if(k==="↵") window.finishAnswer?.();
    else ans.value+=k;
  },{passive:false});
}

/********************************************************************
 * 9.  LANCEMENT
 *******************************************************************/
page_Hz();
