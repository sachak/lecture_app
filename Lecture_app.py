def hidden_screen_test() -> None:
    """
    Mesure automatique et invisible ; arrête l’appli si ≠ 60 Hz ±1,5 Hz.
    S’exécute avant toute interface « utile ».
    """
    if p.hz_ok is not None:                 # déjà testé
        if p.hz_ok:
            return                          # OK : on poursuit
        st.error("Votre écran n’affiche pas à 60 Hz ; "
                 "l’expérience ne peut pas démarrer.")
        st.stop()

    # 1ʳᵉ passe : on lance la mesure (composant 1 px de haut, quasi invisible)
    st.info("Initialisation de l’expérience …")

    TEST_HTML = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;overflow:hidden}</style></head><body>
<script>
Streamlit.setComponentReady();              // ← IMPORTANT
(function measure(){
  let f = 0, t0 = performance.now();
  (function loop(){
    f++; if (f < 120) {requestAnimationFrame(loop);}
    else {
      const hz = f * 1000 / (performance.now() - t0);
      Streamlit.setComponentValue(hz.toFixed(1));       // envoi Python
    }
  })();
})();
</script></body></html>"""

    html_args = dict(height=1, scrolling=False)
    if "key" in inspect.signature(components.html).parameters:
        html_args["key"] = "auto_hz_test"
    val = components.html(TEST_HTML, **html_args)

    # Dès qu’on reçoit la fréquence on la traite puis on relance le script
    if isinstance(val, (int, float, str)):
        try:
            hz = float(val)
            p.hz_val = hz
            p.hz_ok  = (nearest_hz(hz) == 60)
        finally:
            do_rerun()                       # relance pour poursuivre / bloquer
    else:
        st.stop()                            # on attend la fin de la mesure
