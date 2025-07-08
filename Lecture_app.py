import streamlit as st
from streamlit import components

st.set_page_config(page_title="Test plein-écran", layout="wide")

html = """
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"/></head>
<body style="margin:0;display:flex;align-items:center;justify-content:center;
             height:100vh;background:#000;color:#fff;font-size:48px;
             font-family:Arial,Helvetica,sans-serif">
FULLSCREEN ?
<script>
(async ()=>{
  try{
    /* tentative plein-écran immédiate */
    await document.documentElement.requestFullscreen();
  }catch(e){
    console.log("requestFullscreen() bloqué :", e);
  }
})();
</script>
</body>
</html>
"""

components.v1.html(html, height=800, scrolling=False)
