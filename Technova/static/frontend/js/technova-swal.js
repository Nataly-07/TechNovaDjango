/**
 * Alertas y confirmaciones con SweetAlert2 (tema Technova).
 * Requiere: sweetalert2@11 cargado antes que este archivo.
 */
(function () {
  function fallbackAlert(msg) {
    window.alert(msg);
  }

  if (typeof Swal === "undefined") {
    window.TechnovaUi = {
      success: function (title, text) {
        fallbackAlert(text || title);
        return Promise.resolve();
      },
      error: function (text) {
        fallbackAlert(text);
        return Promise.resolve();
      },
      toastOk: function (text) {
        fallbackAlert(text);
        return Promise.resolve();
      },
      needLogin: function (msg) {
        fallbackAlert(msg || "Inicia sesión.");
        window.location.href = "/login/";
        return Promise.resolve();
      },
      confirm: function (opts) {
        opts = opts || {};
        var msg = opts.text || opts.title || "";
        var ok = window.confirm(msg);
        return Promise.resolve({ isConfirmed: ok });
      },
      successChooseCart: function (msg, url) {
        fallbackAlert(msg || "Agregado.");
        if (window.confirm("¿Ir al carrito?") && url) window.location.href = url;
        return Promise.resolve({});
      },
    };
    bindConfirmForms();
    return;
  }

  Swal.mixin({
    confirmButtonColor: "#667eea",
    cancelButtonColor: "#94a3b8",
    confirmButtonText: "Aceptar",
    cancelButtonText: "Cancelar",
    reverseButtons: true,
    customClass: {
      popup: "technova-swal-popup",
      confirmButton: "technova-swal-confirm",
      cancelButton: "technova-swal-cancel",
    },
  });

  window.TechnovaUi = {
    /** Modal de éxito con icono */
    success: function (title, text) {
      return Swal.fire({
        icon: "success",
        title: title || "¡Listo!",
        text: text || "",
        confirmButtonText: "Entendido",
      });
    },

    /** Modal de error */
    error: function (text, title) {
      return Swal.fire({
        icon: "error",
        title: title || "Algo salió mal",
        text: text || "",
        confirmButtonText: "Entendido",
      });
    },

    /** Toast breve esquina superior derecha */
    toastOk: function (text) {
      // Si existe el sistema moderno de alertas del carrito, úsalo para el mensaje típico
      // (evita el toast simple con check verde que estás viendo en captura).
      try {
        var t = String(text || "");
        if (
          window.CarritoAlerts &&
          typeof window.CarritoAlerts.success === "function" &&
          /producto\s+agregado\s+al\s+carrito/i.test(t)
        ) {
          return window.CarritoAlerts.success("Producto agregado al carrito");
        }
      } catch (_ignore) {}
      return Swal.fire({
        toast: true,
        position: "top-end",
        icon: "success",
        title: text,
        showConfirmButton: false,
        timer: 2600,
        timerProgressBar: true,
        didOpen: function (el) {
          el.addEventListener("mouseenter", Swal.stopTimer);
          el.addEventListener("mouseleave", Swal.resumeTimer);
        },
      });
    },

    needLogin: function (msg) {
      return Swal.fire({
        icon: "info",
        title: "Inicia sesión",
        text: msg || "Necesitas una cuenta para usar esta función.",
        confirmButtonText: "Ir al inicio de sesión",
        showCancelButton: true,
        cancelButtonText: "Cerrar",
      }).then(function (r) {
        if (r.isConfirmed) window.location.href = "/login/";
      });
    },

    /**
     * Confirmación con dos botones.
     * opts: { title, text, confirmText, cancelText, icon }
     */
    confirm: function (opts) {
      opts = opts || {};
      return Swal.fire({
        icon: opts.icon || "question",
        title: opts.title || "¿Continuar?",
        text: opts.text || "",
        showCancelButton: true,
        confirmButtonText: opts.confirmText || "Sí",
        cancelButtonText: opts.cancelText || "No",
      });
    },

    /** Tras agregar al carrito: éxito y opción de ir al carrito en un solo paso */
    successChooseCart: function (message, cartUrl) {
      return Swal.fire({
        icon: false,
        html: `
          <div style="text-align: center; padding: 30px 20px;">
            <div style="margin-bottom: 20px;">
              <div style="width: 100px; height: 100px; margin: 0 auto; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; animation: scaleIn 0.5s ease-out;">
                <i class="bx bx-check" style="font-size: 50px; color: white;"></i>
              </div>
            </div>
            <h3 style="color: #0f172a; font-size: 1.8rem; font-weight: 700; margin-bottom: 12px;">¡Agregado al carrito!</h3>
            <p style="color: #64748b; font-size: 1.1rem; margin: 0 0 20px 0; font-weight: 500;">${message || "Tu producto ya está en el carrito."}</p>
            <div style="margin-bottom: 25px; display: flex; justify-content: center; gap: 10px;">
              <span style="background: #f1f5f9; color: #334155; padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                <i class="bx bx-cart" style="margin-right: 6px;"></i>Carrito actualizado
              </span>
              <span style="background: #dcfce7; color: #15803d; padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                <i class="bx bx-check-circle" style="margin-right: 6px;"></i>Disponible
              </span>
            </div>
          </div>
        `,
        showCancelButton: true,
        showConfirmButton: true,
        confirmButtonText: '<i class="bx bx-shopping-bag" style="margin-right: 8px;"></i>Ir al carrito',
        cancelButtonText: '<i class="bx bx-arrow-back" style="margin-right: 8px;"></i>Seguir comprando',
        confirmButtonColor: '#10b981',
        cancelButtonColor: '#64748b',
        customClass: {
          popup: 'custom-swal-popup',
          confirmButton: 'custom-swal-confirm',
          cancelButton: 'custom-swal-cancel'
        },
        backdrop: 'rgba(0, 0, 0, 0.4)',
        showClass: {
          popup: 'animate__animated animate__zoomIn'
        },
        hideClass: {
          popup: 'animate__animated animate__zoomOut'
        }
      }).then(function (r) {
        if (r.isConfirmed && cartUrl) window.location.href = cartUrl;
        return r;
      });
    },
  };

  bindConfirmForms();
})();

/**
 * Formularios con data-technova-confirm='{"title":"...","text":"...",...}' muestran confirmación antes de enviar.
 */
function bindConfirmForms() {
  function run() {
    document.querySelectorAll("form[data-technova-confirm]").forEach(function (form) {
      if (form.dataset.technovaConfirmBound) return;
      form.dataset.technovaConfirmBound = "1";
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var opts = {
          title: "¿Confirmar?",
          text: "",
          confirmText: "Sí",
          cancelText: "No",
          icon: "warning",
        };
        try {
          var raw = form.getAttribute("data-technova-confirm");
          if (raw) Object.assign(opts, JSON.parse(raw));
        } catch (ignore) {}
        var ui = window.TechnovaUi;
        function doSubmit() {
          if (typeof HTMLFormElement !== "undefined" && HTMLFormElement.prototype.submit) {
            HTMLFormElement.prototype.submit.call(form);
          } else {
            form.submit();
          }
        }
        if (ui && typeof ui.confirm === "function") {
          ui.confirm(opts).then(function (r) {
            if (r.isConfirmed) doSubmit();
          });
        } else if (window.confirm(opts.text || opts.title)) {
          doSubmit();
        }
      });
    });
  }
  if (typeof document === "undefined") return;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
}
