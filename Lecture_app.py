TEST60_HTML = r"""
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<style>
html,body{height:100%;margin:0;background:#000;color:#fff;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#res{font-size:48px;margin:30px 0}
button{font-size:24px;padding:8px 28px}
</style></head><body>
<h2>Test de fréquence (cible : 60 Hz)</h2>
<div id="res">--</div><button id="start">Démarrer</button>

<script>
// ---------- utilitaire d’envoi de messages à Streamlit ----------
const send=(type,val=null)=>
  window.parent.postMessage({isStreamlitMessage:true,type,value:val},"*");
send("streamlit:componentReady");
send("streamlit:setFrameHeight",document.body.scrollHeight);

// ---------- logique de mesure ----------
const res=document.getElementById("res");
document.getElementById("start").onclick=()=>{
  const btn=document.getElementById("start");
  btn.disabled=true;
  res.style.color="#fff";
  res.textContent="Mesure en cours…";

  let t=[], n=120;                       // 120 frames ≈ 2 s
  const step=k=>{
    t.push(k);
    if(t.length<n){ requestAnimationFrame(step); }
    else{
      const d=t.slice(1).map((v,i)=>v-t[i]);
      const hz=1000/(d.reduce((a,b)=>a+b,0)/d.length);
      res.textContent=`≈ ${hz.toFixed(1)} Hz`;
      const ok=hz>58&&hz<62;
      res.style.color= ok? "lime" : "red";
      btn.disabled=false;
      if(ok) send("streamlit:setComponentValue","ok");
    }
  };
  requestAnimationFrame(step);
};
</script></body></html>"""
