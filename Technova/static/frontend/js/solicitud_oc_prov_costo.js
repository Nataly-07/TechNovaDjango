/**
 * Órdenes Compra Prov. (empleado): costo desde API con formato COP (tienda) y sin pérdida de precisión.
 * Formularios: data-producto-api-tpl="{% url ... producto_id=999999 %}" y #producto_id / #costo_unitario.
 */
(function () {
  var COP = "COP";

  /** Separa parte entera y centavos desde un decimal "limpio" (solo dígitos y un punto). */
  function splitDecimalCanonical(s) {
    s = String(s || "").trim();
    if (!s) return null;
    var neg = false;
    if (s.charAt(0) === "-") {
      neg = true;
      s = s.slice(1).trim();
    }
    var dot = s.indexOf(".");
    var intRaw;
    var fracRaw;
    if (dot === -1) {
      intRaw = s.replace(/\D/g, "");
      fracRaw = "00";
    } else {
      intRaw = s.slice(0, dot).replace(/\D/g, "");
      fracRaw = (s.slice(dot + 1).replace(/\D/g, "") + "00").slice(0, 2);
    }
    if (!intRaw && !fracRaw.replace(/0/g, "")) return neg ? "-0.00" : "0.00";
    intRaw = intRaw || "0";
    return (neg ? "-" : "") + intRaw + "." + fracRaw;
  }

  /**
   * Valor desde la API (str Django Decimal): sin usar parseFloat para no distorsionar montos grandes.
   */
  function canonicalFromApiString(apiStr) {
    if (apiStr == null || apiStr === "") return "0.00";
    var t = String(apiStr).trim().replace(",", ".");
    return splitDecimalCanonical(t);
  }

  /**
   * Visualización COP (tienda): Intl es-CO — miles con punto; centavos solo si no son ,00.
   * El valor numérico se arma desde enteros (sin parseFloat del string API).
   */
  function formatMonedaTienda(canonical) {
    var c = splitDecimalCanonical(canonical);
    if (!c) return "";
    var neg = c.charAt(0) === "-";
    var body = neg ? c.slice(1) : c;
    var hp = body.split(".");
    var wholeStr = hp[0];
    var frac = hp[1] || "00";
    var wholeNum = parseInt(wholeStr, 10);
    var fracNum = parseInt((frac + "00").slice(0, 2), 10);
    if (!Number.isFinite(wholeNum)) return "";
    var num = wholeNum + fracNum / 100;
    if (neg) num = -num;
    try {
      return new Intl.NumberFormat("es-CO", {
        style: "currency",
        currency: COP,
        minimumFractionDigits: frac === "00" ? 0 : 2,
        maximumFractionDigits: 2,
      }).format(num);
    } catch (_e) {
      var grouped = wholeStr.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
      var suffix = frac === "00" ? "" : "," + (frac + "00").slice(0, 2);
      return "$\u00a0" + (neg ? "-" : "") + grouped + suffix;
    }
  }

  /**
   * Interpreta lo que escribe el empleado (con o sin $, COP, puntos miles, coma decimal).
   * Devuelve canonical "12345678.99" o null si no es válido.
   */
  function parseMonedaLocalInput(raw) {
    if (raw == null) return null;
    var s = String(raw)
      .replace(/\u00a0/g, " ")
      .replace(/\$/g, " ")
      .replace(new RegExp(COP, "gi"), " ")
      .trim();
    if (!s) return null;

    s = s.replace(/\s+/g, "");

    if (s.indexOf(",") !== -1) {
      var p = s.split(",");
      var intPart = p[0].replace(/\./g, "").replace(/\D/g, "");
      var decPart = (p[1] || "").replace(/\D/g, "").slice(0, 2);
      if (p.length > 2) return null;
      if (!intPart && !decPart) return null;
      decPart = (decPart + "00").slice(0, 2);
      return splitDecimalCanonical(intPart + "." + decPart);
    }

    var dots = (s.match(/\./g) || []).length;
    if (dots === 0) {
      var digits = s.replace(/\D/g, "");
      return digits ? splitDecimalCanonical(digits + ".00") : null;
    }
    if (dots === 1) {
      var ps = s.split(".");
      var left = ps[0].replace(/\D/g, "");
      var right = ps[1].replace(/\D/g, "");
      if (right.length <= 2) {
        return splitDecimalCanonical(left + "." + (right + "00").slice(0, 2));
      }
      return splitDecimalCanonical(left + right);
    }
    return splitDecimalCanonical(s.replace(/\./g, ""));
  }

  /** Normaliza para POST: decimal con punto, sin símbolos (backend Django). */
  function canonicalToBackendField(canonical) {
    var c = splitDecimalCanonical(canonical);
    return c || "";
  }

  function bindForm(form) {
    var tpl = form.getAttribute("data-producto-api-tpl");
    var sel = form.querySelector("#producto_id");
    var cost = form.querySelector("#costo_unitario");
    if (!cost) return;

    function applyDisplayFromCanonical(canon) {
      var c = splitDecimalCanonical(canon);
      if (c) cost.value = formatMonedaTienda(c);
    }

    if (form.getAttribute("data-oc-format-initial") === "1" && cost.value) {
      var init = parseMonedaLocalInput(cost.value);
      if (!init) {
        init = canonicalFromApiString(cost.value.replace(/\$/g, "").replace(new RegExp(COP, "gi"), "").trim());
      }
      if (init) applyDisplayFromCanonical(init);
    }

    if (sel && tpl) {
      sel.addEventListener("change", function () {
        var pid = sel.value;
        if (!pid) return;
        var url = tpl.replace("999999", String(pid));
        fetch(url, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        })
          .then(function (r) {
            if (!r.ok) throw new Error("http");
            return r.json();
          })
          .then(function (d) {
            var canon = canonicalFromApiString(d.costo_unitario);
            applyDisplayFromCanonical(canon);
            var dp = document.getElementById("disp-prov");
            var dm = document.getElementById("disp-marca");
            var dc = document.getElementById("disp-color");
            var ds = document.getElementById("disp-stock");
            if (dp) dp.textContent = d.proveedor_nombre || "—";
            if (dm) dm.textContent = d.marca || "—";
            if (dc) dc.textContent = d.color || "—";
            if (ds) ds.textContent = d.stock != null ? d.stock : "—";
          })
          .catch(function () {});
      });
    }

    cost.addEventListener("blur", function () {
      var t = cost.value.trim();
      if (!t) {
        cost.removeAttribute("aria-invalid");
        return;
      }
      var canon = parseMonedaLocalInput(t);
      if (!canon) {
        cost.setAttribute("aria-invalid", "true");
        cost.title = "Usa números con formato colombiano: miles con punto y decimales con coma (ej. $ 9.700.000 COP).";
        return;
      }
      cost.removeAttribute("aria-invalid");
      cost.title = "";
      applyDisplayFromCanonical(canon);
    });

    cost.addEventListener("focus", function () {
      cost.removeAttribute("aria-invalid");
    });

    form.addEventListener("submit", function () {
      var t = cost.value.trim();
      if (!t) return;
      var canon = parseMonedaLocalInput(t);
      cost.value = canon ? canonicalToBackendField(canon) : "";
    });
  }

  function init() {
    document.querySelectorAll("form[data-producto-api-tpl]").forEach(bindForm);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
