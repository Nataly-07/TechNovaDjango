/**
 * Formato moneda COP para lectura (es-CO).
 * Entrada: número; salida: cadena con separadores (ej. $9.600.000,00).
 */
(function () {
  function formatCOP(valor) {
    var n = Number(valor);
    if (!Number.isFinite(n)) {
      return "—";
    }
    try {
      return new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: "COP",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(n);
    } catch (_e) {
      return (
        "$" +
        n.toLocaleString("de-DE", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      );
    }
  }

  window.TechnovaFormatCOP = formatCOP;
})();
