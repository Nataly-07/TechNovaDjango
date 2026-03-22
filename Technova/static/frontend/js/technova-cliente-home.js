/**
 * Inicio: catálogo y búsqueda avanzada contra /api/v1/producto/ (proyecto Java adaptado).
 */
(function () {
  function imgUrl(p) {
    const im = p.imagen || "";
    if (im.startsWith("http")) return im;
    if (im) return "/static/frontend/imagenes/" + im;
    return "/static/frontend/imagenes/placeholder.svg";
  }

  function precioDisplay(p) {
    const c = p.caracteristica || {};
    const pv = c.precio_venta || p.precio_venta;
    if (pv) return "$" + Number(String(pv).replace(",", "")).toLocaleString("es-CO");
    const costo = p.costo_unitario || "0";
    return "$" + Number(String(costo).replace(",", "")).toLocaleString("es-CO");
  }

  function cardHtml(p) {
    const stock = p.stock != null ? p.stock : 0;
    const disp =
      stock > 0
        ? '<span style="background:#d4edda;color:#155724;padding:4px 8px;border-radius:15px;font-size:11px;">Disponible</span>'
        : '<span style="background:#f8d7da;color:#721c24;padding:4px 8px;border-radius:15px;font-size:11px;">Agotado</span>';
    return (
      '<div class="producto" data-id="' +
      p.id +
      '">' +
      '<img src="' +
      imgUrl(p) +
      '" alt="' +
      (p.nombre || "") +
      '" onerror="this.src=\'/static/frontend/imagenes/placeholder.svg\'"/>' +
      '<a href="/producto/' +
      p.id +
      '/"><span class="detalles">Ver más detalles</span></a>' +
      "<h3>" +
      (p.nombre || "") +
      "</h3>" +
      '<div style="margin:5px 0;">' +
      disp +
      "</div>" +
      "<p>4.5 ⭐</p>" +
      "<p><strong>" +
      precioDisplay(p) +
      "</strong></p>" +
      '<div style="display:flex;gap:8px;justify-content:center;align-items:center;">' +
      '<button type="button" class="carrito-btn js-carrito" data-producto-id="' +
      p.id +
      '" title="Agregar al carrito">&#128722;</button>' +
      '<button type="button" class="favorito-btn js-favorito" data-producto-id="' +
      p.id +
      '" title="Favorito">&#10084;&#65039;</button>' +
      "</div></div>"
    );
  }

  async function cargarCatalogo() {
    const track = document.querySelector(".carrusel-track");
    if (!track) return;
    try {
      const data = await window.TechnovaApi.get("/producto/");
      const items = data.items || [];
      track.innerHTML = items.map(cardHtml).join("") || "<p>No hay productos.</p>";
      document.dispatchEvent(new CustomEvent("technova:productos-cargados"));
    } catch (e) {
      track.innerHTML =
        '<p style="padding:20px;color:#e63946;">No se pudo cargar el catálogo. ' +
        (e.message || "") +
        "</p>";
    }
  }

  async function buscarAvanzado() {
    const params = new URLSearchParams();
    const termino = document.getElementById("busquedaTermino")?.value?.trim();
    const marca = document.getElementById("filtroMarca")?.value?.trim();
    const categoria = document.getElementById("filtroCategoria")?.value?.trim();
    const precioMin = document.getElementById("filtroPrecioMin")?.value?.trim();
    const precioMax = document.getElementById("filtroPrecioMax")?.value?.trim();
    const disponibilidad = document.getElementById("filtroDisponibilidad")?.value?.trim();
    if (termino) params.append("termino", termino);
    if (marca) params.append("marca", marca);
    if (categoria) params.append("categoria", categoria);
    if (precioMin) params.append("precioMin", precioMin);
    if (precioMax) params.append("precioMax", precioMax);
    if (disponibilidad) params.append("disponibilidad", disponibilidad);

    const resultadosDiv = document.getElementById("resultadosBusqueda");
    const productosFiltradosDiv = document.getElementById("productosFiltrados");
    const productosOriginalesDiv = document.getElementById("productosOriginales");

    if (
      !termino &&
      !marca &&
      !categoria &&
      !precioMin &&
      !precioMax &&
      !disponibilidad
    ) {
      if (resultadosDiv) resultadosDiv.classList.remove("show");
      if (productosOriginalesDiv) productosOriginalesDiv.style.display = "";
      return;
    }

    try {
      if (resultadosDiv) resultadosDiv.classList.add("show");
      if (productosOriginalesDiv) productosOriginalesDiv.style.display = "none";
      if (productosFiltradosDiv)
        productosFiltradosDiv.innerHTML = "<p>Buscando...</p>";

      const data = await window.TechnovaApi.get(
        "/producto/buscar-avanzado/?" + params.toString()
      );
      const items = data.items || [];
      if (productosFiltradosDiv) {
        productosFiltradosDiv.innerHTML = items.length
          ? items.map(cardHtml).join("")
          : "<p>No se encontraron productos.</p>";
      }
    } catch (e) {
      if (productosFiltradosDiv)
        productosFiltradosDiv.innerHTML =
          "<p style='color:#e63946;'>" + (e.message || "Error") + "</p>";
    }
  }

  function limpiarFiltros() {
    document.getElementById("resultadosBusqueda")?.classList.remove("show");
    const o = document.getElementById("productosOriginales");
    if (o) o.style.display = "";
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.TECHNOVA_API_PREFIX = window.TECHNOVA_API_PREFIX || "/api/v1";
    cargarCatalogo();

    document.querySelector(".carrusel-track")?.addEventListener("click", function (ev) {
      const b = ev.target.closest(".js-carrito");
      if (b) {
        ev.preventDefault();
        const pid = b.getAttribute("data-producto-id");
        importarCarrito(pid);
      }
      const f = ev.target.closest(".js-favorito");
      if (f) {
        ev.preventDefault();
        const pid = f.getAttribute("data-producto-id");
        toggleFavorito(pid);
      }
    });

    document.getElementById("productosFiltrados")?.addEventListener("click", function (ev) {
      const b = ev.target.closest(".js-carrito");
      if (b) {
        ev.preventDefault();
        importarCarrito(b.getAttribute("data-producto-id"));
      }
      const f = ev.target.closest(".js-favorito");
      if (f) {
        ev.preventDefault();
        toggleFavorito(f.getAttribute("data-producto-id"));
      }
    });
  });

  async function importarCarrito(productoId) {
    if (!window.TechnovaAuth.isLoggedIn()) {
      alert("Inicia sesión para usar el carrito.");
      window.location.href = "/login/";
      return;
    }
    const uid = window.TechnovaAuth.getUsuarioId();
    try {
      await window.TechnovaApi.post("/carrito/" + uid + "/agregar/", {
        producto_id: parseInt(productoId, 10),
        cantidad: 1,
      });
      alert("Producto agregado al carrito.");
    } catch (e) {
      alert(e.message || "No se pudo agregar.");
    }
  }

  async function toggleFavorito(productoId) {
    if (!window.TechnovaAuth.isLoggedIn()) {
      alert("Inicia sesión para favoritos.");
      window.location.href = "/login/";
      return;
    }
    const uid = window.TechnovaAuth.getUsuarioId();
    try {
      await window.TechnovaApi.post(
        "/favoritos/usuario/" + uid + "/producto/" + productoId + "/toggle/",
        {}
      );
      alert("Favorito actualizado.");
    } catch (e) {
      alert(e.message || "Error en favoritos.");
    }
  }

  window.buscarProductos = buscarAvanzado;
  window.limpiarFiltros = limpiarFiltros;
  window.toggleFiltros = function () {
    const el = document.getElementById("filtrosContainer");
    if (el) el.style.display = el.style.display === "none" ? "block" : "none";
  };
})();
