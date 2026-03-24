/**
 * Index público `/`: búsqueda avanzada (API Django) y carrito → login (misma idea que Spring).
 */
(function () {
  function loginUrl() {
    return (
      (typeof window.TECHNOVA_URL_LOGIN === "string" && window.TECHNOVA_URL_LOGIN) ||
      "/login/"
    );
  }

  function escapeHtml(texto) {
    return String(texto || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function imgUrl(p) {
    var im = p.imagen || "";
    if (im.indexOf("http") === 0) return im;
    if (im) {
      if (im.indexOf("/") === 0) return im;
      return "/static/frontend/imagenes/" + im;
    }
    return "/static/frontend/imagenes/placeholder.svg";
  }

  function cardHtml(p) {
    var stock = p.stock != null ? p.stock : 0;
    var dispOk =
      stock > 0
        ? '<span class="producto-stock-badge producto-stock-badge--ok"><span>✓</span><span>Disponible</span></span>'
        : '<span class="producto-stock-badge producto-stock-badge--no"><span>✗</span><span>Agotado</span></span>';
    var c = p.caracteristica || {};
    var pv = c.precio_venta || p.precio_venta;
    var precioNum = pv ? Number(String(pv).replace(",", ".")) : NaN;
    var costo = p.costo_unitario ? Number(String(p.costo_unitario).replace(",", ".")) : NaN;
    var effective = !isNaN(precioNum) ? precioNum : !isNaN(costo) ? costo : null;
    var precioPart = "";
    if (effective != null) {
      var orig = Math.round(effective * 1.05);
      var desc = Math.round(effective);
      precioPart =
        '<p class="precio-original">$<span>' +
        orig +
        "</span></p>" +
        '<p class="precio-descuento">$<span>' +
        desc +
        '</span><span class="descuento">-5%</span></p>';
    }
    return (
      '<div class="producto" data-id="' +
      p.id +
      '">' +
      '<img src="' +
      escapeHtml(imgUrl(p)) +
      '" alt="' +
      escapeHtml(p.nombre) +
      '" onerror="this.src=\'/static/frontend/imagenes/placeholder.svg\'"/>' +
      '<a href="/producto/' +
      p.id +
      '/" class="js-producto-modal-link" data-producto-id="' +
      p.id +
      '"><span class="detalles">Ver Más Detalles</span></a>' +
      "<h3>" +
      escapeHtml(p.nombre) +
      "</h3>" +
      '<div class="producto-stock">' +
      dispOk +
      "</div>" +
      "<p>4.5 ⭐</p>" +
      precioPart +
      '<a href="' +
      loginUrl() +
      '" class="carrito-btn carrito-btn--carrusel">&#128722;</a>' +
      "</div>"
    );
  }

  async function buscarAvanzado() {
    var params = new URLSearchParams();
    var termino = document.getElementById("busquedaTermino")?.value?.trim();
    var marca = document.getElementById("filtroMarca")?.value?.trim();
    var categoria = document.getElementById("filtroCategoria")?.value?.trim();
    var precioMin = document.getElementById("filtroPrecioMin")?.value?.trim();
    var precioMax = document.getElementById("filtroPrecioMax")?.value?.trim();
    var disponibilidad = document.getElementById("filtroDisponibilidad")?.value?.trim();
    if (termino) params.append("termino", termino);
    if (marca) params.append("marca", marca);
    if (categoria) params.append("categoria", categoria);
    if (precioMin) params.append("precioMin", precioMin);
    if (precioMax) params.append("precioMax", precioMax);
    if (disponibilidad) params.append("disponibilidad", disponibilidad);

    var resultadosDiv = document.getElementById("resultadosBusqueda");
    var productosFiltradosDiv = document.getElementById("productosFiltrados");
    var productosOriginalesDiv = document.getElementById("productosOriginales");

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
      if (productosFiltradosDiv) productosFiltradosDiv.innerHTML = "<p>Buscando...</p>";

      var data = await window.TechnovaApi.get(
        "/producto/buscar-avanzado/?" + params.toString()
      );
      var items = data.items || [];
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
    var marca = document.getElementById("filtroMarca");
    var categoria = document.getElementById("filtroCategoria");
    var min = document.getElementById("filtroPrecioMin");
    var max = document.getElementById("filtroPrecioMax");
    var disp = document.getElementById("filtroDisponibilidad");
    var term = document.getElementById("busquedaTermino");
    if (marca) marca.value = "";
    if (categoria) categoria.value = "";
    if (min) min.value = "";
    if (max) max.value = "";
    if (disp) disp.value = "";
    if (term) term.value = "";
    document.getElementById("resultadosBusqueda")?.classList.remove("show");
    var o = document.getElementById("productosOriginales");
    if (o) o.style.display = "";
  }

  function needLoginGuest(msg) {
    if (window.TechnovaUi && window.TechnovaUi.needLogin) {
      return window.TechnovaUi.needLogin(
        msg || "Debes iniciar sesión primero para agregar productos al carrito."
      );
    }
    window.location.href = loginUrl();
    return Promise.resolve();
  }

  function onCarritoLink(ev) {
    if (ev.target.closest && ev.target.closest(".acciones-usuario")) {
      return;
    }
    var a = ev.target.closest && ev.target.closest("a.carrito-btn");
    if (!a || !window.TECHNOVA_INDEX_PUBLIC) return;
    ev.preventDefault();
    ev.stopPropagation();
    needLoginGuest();
  }

  function scrollToCatalogo() {
    var el = document.getElementById("catalogo-publico");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function aplicarFiltroCategoria(val) {
    var sel = document.getElementById("filtroCategoria");
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (sel) sel.value = val || "";
    if (fc) {
      fc.style.display = "block";
      if (toggle) toggle.classList.add("active");
    }
    scrollToCatalogo();
    buscarAvanzado();
  }

  function aplicarFiltroMarca(val) {
    var sel = document.getElementById("filtroMarca");
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (sel) sel.value = val || "";
    if (fc) {
      fc.style.display = "block";
      if (toggle) toggle.classList.add("active");
    }
    scrollToCatalogo();
    buscarAvanzado();
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.TECHNOVA_API_PREFIX = window.TECHNOVA_API_PREFIX || "/api/v1";

    document.addEventListener("click", onCarritoLink, true);

    document.querySelectorAll(".index-sub-cat").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        aplicarFiltroCategoria(btn.getAttribute("data-categoria") || "");
      });
    });

    document.querySelectorAll(".index-sub-marca").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        aplicarFiltroMarca(btn.getAttribute("data-marca") || "");
      });
    });
  });

  window.buscarProductos = buscarAvanzado;
  window.limpiarFiltros = limpiarFiltros;
  window.toggleFiltros = function () {
    var el = document.getElementById("filtrosContainer");
    var btn = document.getElementById("btnFiltrosToggle");
    if (!el) return;
    var shouldOpen = el.style.display === "none";
    el.style.display = shouldOpen ? "block" : "none";
    if (btn) btn.classList.toggle("active", shouldOpen);
  };

  document.addEventListener("click", function (ev) {
    var filtros = document.getElementById("filtrosContainer");
    var btn = document.getElementById("btnFiltrosToggle");
    if (!filtros || filtros.style.display === "none") return;
    var clickedInside =
      filtros.contains(ev.target) || (btn && btn.contains(ev.target));
    if (!clickedInside) {
      filtros.style.display = "none";
      if (btn) btn.classList.remove("active");
    }
  });
})();
