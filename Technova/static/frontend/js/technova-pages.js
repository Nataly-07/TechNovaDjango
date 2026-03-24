/**
 * Páginas internas del rol cliente (perfil, carrito, pedidos, etc.).
 */
(function () {
  function uid() {
    return window.TechnovaAuth.getUsuarioId();
  }

  function requireLogin() {
    /* Sesión Django (plantillas cliente) sin JWT en localStorage */
    if (window.TECHNOVA_SESION_SERVIDOR) {
      return true;
    }
    if (!window.TechnovaAuth.isLoggedIn()) {
      window.location.href = "/login/";
      return false;
    }
    return true;
  }

  async function perfil() {
    const el = document.getElementById("page-data");
    if (!el) return;
    if (!window.TechnovaAuth.isLoggedIn()) {
      el.innerHTML =
        "<p style='color:#64748b;font-size:.95rem'>Los datos de la cuenta se muestran arriba (sesión servidor). Para ver el JSON de <code>/auth/me/</code> hace falta token JWT (API).</p>";
      return;
    }
    if (!requireLogin()) return;
    try {
      const me = await window.TechnovaApi.get("/auth/me/");
      el.innerHTML =
        "<pre style='white-space:pre-wrap;background:#fff;padding:1rem;border-radius:12px;'>" +
        JSON.stringify(me, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function carrito() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get("/carrito/" + uid() + "/");
      const items = data.items || [];
      el.innerHTML =
        "<p>Ítems: " +
        items.length +
        "</p><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function favoritos() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get("/favoritos/usuario/" + uid() + "/");
      const items = data.items || [];
      el.innerHTML =
        "<p>Total: " +
        items.length +
        "</p><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function notificaciones() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get("/notificaciones/usuario/" + uid() + "/");
      const items = data.items || [];
      el.innerHTML =
        "<p>Total: " +
        items.length +
        "</p><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function pedidos() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get("/venta/mias/");
      const items = data.items || [];
      el.innerHTML =
        "<p>Ventas: " +
        items.length +
        "</p><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function misCompras() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get("/compra/mias/");
      const items = data.items || [];
      el.innerHTML =
        "<p>Compras: " +
        items.length +
        "</p><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  async function atencion() {
    if (!requireLogin()) return;
    const el = document.getElementById("page-data");
    try {
      const data = await window.TechnovaApi.get(
        "/atencion-cliente/solicitudes/?usuario_id=" + encodeURIComponent(uid())
      );
      const items = data.items || [];
      el.innerHTML =
        "<h3>Solicitudes</h3><pre style='white-space:pre-wrap;'>" +
        JSON.stringify(items, null, 2) +
        "</pre>";
    } catch (e) {
      el.textContent = e.message || "Error";
    }
  }

  function escapeHtml(texto) {
    return String(texto || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function productoDetalle(id) {
    if (window.TechnovaProductoModal && typeof window.TechnovaProductoModal.open === "function") {
      await window.TechnovaProductoModal.open(id);
      return;
    }
    const el = document.getElementById("page-data");
    if (el) {
      el.innerHTML =
        "<p style='color:#dc2626'>No se pudo cargar el visor de producto.</p>";
    }
  }

  window.TechnovaPages = {
    perfil,
    carrito,
    favoritos,
    notificaciones,
    pedidos,
    misCompras,
    atencion,
    productoDetalle,
  };
})();
