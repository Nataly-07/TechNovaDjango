/**
 * Oculta automáticamente los avisos de éxito del panel admin tras 4 s.
 */
(function () {
  var DELAY_MS = 4000;
  var FADE_MS = 350;

  function ocultarAlerta(el) {
    if (!el || !el.parentNode) return;
    el.style.transition =
      "opacity " + FADE_MS / 1000 + "s ease, transform " + FADE_MS / 1000 + "s ease";
    el.style.opacity = "0";
    el.style.transform = "translateY(-6px)";
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, FADE_MS);
  }

  function programarCierre() {
    document.querySelectorAll(".alert-success").forEach(function (el) {
      setTimeout(function () {
        ocultarAlerta(el);
      }, DELAY_MS);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", programarCierre);
  } else {
    programarCierre();
  }
})();
