import streamlit as st
from streamlit import components

st.set_page_config(page_title="Auto-FS", layout="centered")

html = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/></head>
<body style="margin:0;display:flex;align-items:center;justify-content:center;
             height:100vh;background:#000;color:#fff;font-family:sans-serif;
             font-size:36px;text-align:center">
<span id="msg">Tentative plein-écran…</span>

<script>
const msg = document.getElementById('msg');

/* 1) tentative immédiate (peut réussir si la navigation est
      considérée comme « user-activation » par le navigateur) */
requestFS();

/* 2) si refus -> on retente au premier clic */
document.addEventListener('click', requestFS, {once:true});

function requestFS(){
  if (document.fullscreenElement) {msg.textContent="Déjà plein-écran"; return;}
  const el=document.documentElement;
  if (!el.requestFullscreen){msg.textContent="API non disponible"; return;}

  el.requestFullscreen()
    .then(()=> msg.textContent="Plein-écran actif  (Esc pour quitter)")
    .catch(err=>{
        console.log(err.name);
        msg.textContent="Refusé : "+err.name+" (cliquez pour réessayer)";
    });
}
</script>
</body>
</html>
"""

components.v1.html(html, height=600, scrolling=False)
