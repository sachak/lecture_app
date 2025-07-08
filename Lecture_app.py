import streamlit as st
from streamlit import components

st.set_page_config(page_title="Test plein-écran", layout="centered")

st.write("Cliquez dans la zone grisée pour demander le plein-écran :")

html = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;">
<div id="zone" style="
     height:300px;border:3px dashed #888;display:flex;
     align-items:center;justify-content:center;cursor:pointer;
     font-family:Arial,Helvetica,sans-serif;font-size:28px;">
  Cliquez ici
</div>

<script>
const zone = document.getElementById('zone');
zone.addEventListener('click', () => {
  if (!document.fullscreenElement &&
      document.documentElement.requestFullscreen){
      document.documentElement.requestFullscreen()
        .then(()=> zone.textContent =
                'Plein-écran actif !  (Esc pour quitter)')
        .catch(err => zone.textContent =
                'Refusé : ' + err.name);
  }
});
</script>
</body>
</html>
"""

components.v1.html(html, height=320, scrolling=False)
