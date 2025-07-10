'use strict';

/**********************************************************************
 * 1. CONFIGURATION
 *********************************************************************/
const CFG = {
  XLSX_FILE        : "Lexique.xlsx",
  TAGS             : ["LOW_OLD","HIGH_OLD","LOW_PLD","HIGH_PLD"],
  N_PER_FEUIL_TAG  : 5,
  MAX_TRY_TAG      : 1000,
  MAX_TRY_FULL     : 1000,
  NUM_BASE         : ["nblettres","nbphons","old20","pld20"],
  PRACTICE_WORDS   : ["PAIN","EAU"],
  CYCLE_MS         : 350,
  CROSS_MS         : 500,
  MEAN_FACTOR_OLDPLD: .35,
  MEAN_DELTA       : {letters:.68, phons:.68},
  SD_MULT          : {letters:2, phons:2, old20:.28, pld20:.28, freq:1.9},
  HZ               : 60,           // 60 ou 120
  TOUCH_TRIGGER    : true
};

/**********************************************************************
 * 2. OUTILS
 *********************************************************************/
const rng       = () => Math.random();
const shuffled  = a  => [...a].sort(()=>rng()-.5);
const catCode   = t  => t.includes("LOW")?-1:(t.includes("HIGH")?1:0);
const mean      = a  => a.reduce((s,x)=>s+x,0)/a.length;
const std       = a  => {const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)**2)));};
const pick      = (a,n)=>shuffled(a).slice(0,n);
const toFloat   = v  => typeof v==="number"?v:parseFloat(String(v).replace(/[\s,]/g,"."));

/**********************************************************************
 * 3. LECTURE DE LEXIQUE.XLSX (SheetJS)
 *********************************************************************/
async function loadSheets(){
  const data=await fetch(CFG.XLSX_FILE).then(r=>r.arrayBuffer());
  const wb=XLSX.read(data,{type:"array"});
  const shNames=wb.SheetNames.filter(s=>s.toLowerCase().startsWith("feuil"));
  if(shNames.length!==4) throw "Il faut exactement 4 feuilles Feuil1…Feuil4";

  const feuilles={}, allFreq=new Set();
  for(const sh of shNames){
    const json=XLSX.utils.sheet_to_json(wb.Sheets[sh],{defval:null,raw:false});
    const cols=Object.keys(json[0]).map(c=>c.trim().toLowerCase());
    const need=["ortho","old20","pld20","nblettres","nbphons"];
    need.forEach(c=>{if(!cols.includes(c))throw `Colonne manquante ${c} dans ${sh}`});
    const freqCols=cols.filter(c=>c.startsWith("freq"));
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

/**********************************************************************
 * 4. TIRAGE DES 80 MOTS
 *********************************************************************/
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
         fq.every(c=>v(sub.map(r=>r[c]))<=st["sd_"+c]*CFG.SD_MULT.freq);
}
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
    samp.forEach(r=>{
      r.source=feuille;r.group=tag;
      r.old_cat=tag.includes("OLD")?catCode(tag):0;
      r.pld_cat=tag.includes("PLD")?catCode(tag):0;
    });
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

/**********************************************************************
 * 5. INTERFACE EXPÉRIMENTALE
 *********************************************************************/
const FRAME_MS = 1000/CFG.HZ;
const CYCLE_F  = Math.round(CFG.CYCLE_MS/FRAME_MS);
const CROSS_F  = Math.round(CFG.CROSS_MS/FRAME_MS);
const SCALE    = CFG.HZ/60;
const START_F  = 1*SCALE;
const STEP_F   = 1*SCALE;
const IS_TOUCH = ('ontouchstart' in window)||(navigator.maxTouchPoints>0);

const scr=document.getElementById('scr');
const ans=document.getElementById('ans');
const vk =document.getElementById('vk');
let finishAnswer=()=>{};

function resizeAll(){
  const b=Math.min(innerWidth,innerHeight);
  scr.style.fontSize=Math.max(Math.round(b*0.08),26)+'px';
  ans.style.fontSize=Math.max(Math.round(b*0.054),20)+'px';
  ans.style.width=Math.min(innerWidth*0.7,650)+'px';
}
addEventListener('resize',resizeAll);
addEventListener('orientationchange',resizeAll);
addEventListener('load',()=>{document.body.focus();setTimeout(resizeAll,80);});

function buildVK(){
  if(vk.firstChild) return;
  const rows=["QWERTZUIOP","ASDFGHJKL","YXCVBNM","ÇÉÈÊÏÔ←↵"];
  rows.forEach(r=>{
    const d=document.createElement('div');d.className='krow';
    [...r].forEach(ch=>{
      const b=document.createElement('button');b.className='key';b.textContent=ch;d.appendChild(b);
    });vk.appendChild(d);
  });
  vk.addEventListener('pointerdown',e=>{
    const t=e.target;if(!t.classList.contains('key'))return;
    e.preventDefault();
    const k=t.textContent;
    if(k==="←") ans.value=ans.value.slice(0,-1);
    else if(k==="↵") finishAnswer();
    else ans.value+=k;
  },{passive:false});
}

/**********************************************************************
 * 6. LOGIQUE
 *********************************************************************/
let phase="intro", trial=0, WORDS=[], results=[];
function setWords(arr,p){WORDS=[...arr];trial=0;phase=p;nextTrial();}

function intro(){
  scr.textContent="Chargement du lexique…";
  buildSheet().then(list=>{
    window.sheet80=list;
    scr.textContent="Touchez / ESPACE pour commencer la familiarisation";
    function start(e){
      if(e instanceof KeyboardEvent && e.code!=="Space") return;
      if(e instanceof PointerEvent) e.preventDefault();
      removeEventListener('keydown',start);removeEventListener('pointerdown',start);
      setWords(CFG.PRACTICE_WORDS,"practice");
    }
    addEventListener('keydown',start);
    addEventListener('pointerdown',start,{passive:false});
  }).catch(err=>scr.textContent=err);
}

function nextTrial(){
  if(trial>=WORDS.length){fin();return;}
  const w=WORDS[trial],mask="#".repeat(w.length);let active=true;
  scr.textContent="+";let frame=0;
  const crossLoop=()=>{if(!active)return;
    if(++frame>=CROSS_F)startStimulus();else requestAnimationFrame(crossLoop);}
  requestAnimationFrame(crossLoop);

  function startStimulus(){
    let showF=START_F,subF=0,phaseS="show";
    const t0=performance.now();
    function anim(){
      if(!active) return;
      if(phaseS==="show"){
        if(subF===0) scr.textContent=w;
        if(++subF>=showF){phaseS="mask";subF=0;scr.textContent=mask;}
      }else{
        const hideF=Math.max(0,CYCLE_F-showF);
        if(++subF>=hideF){showF=Math.min(showF+STEP_F,CYCLE_F);phaseS="show";subF=0;}
      }
      requestAnimationFrame(anim);
    }
    requestAnimationFrame(anim);

    function trigger(e){
      if(e instanceof KeyboardEvent && e.code!=="Space") return;
      if(e instanceof PointerEvent) e.preventDefault();
      if(!active) return;
      active=false;
      removeEventListener('keydown',trigger);
      if(CFG.TOUCH_TRIGGER) removeEventListener('pointerdown',trigger);
      promptAnswer(Math.round(performance.now()-t0));
    }
    addEventListener('keydown',trigger);
    if(CFG.TOUCH_TRIGGER) addEventListener('pointerdown',trigger,{passive:false});
  }

  function promptAnswer(rt){
    scr.textContent="";
    ans.value="";ans.style.display="block";
    if(IS_TOUCH){ans.readOnly=true;buildVK();vk.style.display="flex";}
    else{ans.readOnly=false;setTimeout(()=>ans.focus(),40);}
    resizeAll();
    function keyEnter(ev){if(ev.key==="Enter"){ev.preventDefault();finishAnswer();}}
    addEventListener('keydown',keyEnter);
    finishAnswer=function(){
      removeEventListener('keydown',keyEnter);
      ans.style.display="none";vk.style.display="none";
      results.push({word:w,rt_ms:rt,response:ans.value.trim(),phase});
      trial++;nextTrial();
    };
  }
}

function fin(){
  if(phase==="practice"){
    scr.textContent="Fin de la familiarisation. Touchez / ESPACE pour commencer le test";
    function go(e){
      if(e instanceof KeyboardEvent && e.code!=="Space") return;
      if(e instanceof PointerEvent) e.preventDefault();
      removeEventListener('keydown',go);removeEventListener('pointerdown',go);
      document.documentElement.requestFullscreen?.();
      setWords(shuffled(window.sheet80.map(r=>r.ortho)),"main");
    }
    addEventListener('keydown',go);
    addEventListener('pointerdown',go,{passive:false});
  }else{
    scr.style.fontSize="min(6vw,48px)";
    scr.textContent="Merci !";
    const csv=["word;rt_ms;response;phase",...results.map(r=>
      `${r.word};${r.rt_ms};${r.response};${r.phase}`)].join("\n");
    const a=document.createElement('a');
    a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
    a.download="results.csv";a.textContent="Télécharger les résultats";
    a.style.fontSize="min(6vw,32px)";a.style.marginTop="30px";
    document.body.appendChild(a);

    // Sauvegarde dans Testable.org
    if(typeof testableSubmit==="function"){
      testableSubmit({csv});
    }else if(typeof parent!=="undefined"){
      parent.postMessage({type:"SAVE_DATA",data:csv},"*");
    }
  }
}

/**********************************************************************
 * 7. LANCEMENT
 *********************************************************************/
intro();
