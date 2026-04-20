/**
 * Restricción de compra en tienda para perfiles Administrador / Empleado (sesión Django).
 * Requiere: window.TECHNOVA_COMPRA_BLOQUEADA_GESTION, TECHNOVA_ROL_COMPRA_BLOQUEADA_ETIQUETA (plantilla).
 * Tras cargar technova-swal.js: TechnovaUi.info para el aviso.
 */
(function () {
  function mensajeCompraNoPermitidaGestion() {
    var rol = String(window.TECHNOVA_ROL_COMPRA_BLOQUEADA_ETIQUETA || "").trim();
    if (!rol) rol = "este perfil";
    return (
      "Tu perfil de " +
      rol +
      " no está habilitado para realizar compras. Por favor, inicia sesión con una cuenta de Cliente para continuar."
    );
  }

  window.TechnovaCompraBloqueoGestion = {
    estaBloqueada: function () {
      return window.TECHNOVA_COMPRA_BLOQUEADA_GESTION === true;
    },
    mostrarAlerta: function () {
      var msg = mensajeCompraNoPermitidaGestion();
      if (window.TechnovaUi && typeof window.TechnovaUi.info === "function") {
        return window.TechnovaUi.info(msg, "Compra no disponible");
      }
      if (typeof Swal !== "undefined") {
        return Swal.fire({
          icon: "info",
          title: "Compra no disponible",
          text: msg,
          confirmButtonText: "Entendido",
        });
      }
      window.alert(msg);
      return Promise.resolve();
    },
  };
})();
