/**
 * Index público `/`: búsqueda avanzada (API Django) y carrito de invitado (sesión Django + CSRF).
 * Enter: envío del formulario. Texto: búsqueda reactiva con debounce al escribir.
 */
(function () {
  var debounceTimer = null;
  var BUSQUEDA_DEBOUNCE_MS = 320;
  /** Evita que `change` del panel dispare búsqueda duplicada al sincronizar selects desde el menú. */
  var _filtroIndexSilenciaChange = false;

  function clearBusquedaDebounce() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }

  function buscarProductosDebounced() {
    clearBusquedaDebounce();
    debounceTimer = setTimeout(function () {
      debounceTimer = null;
      buscarAvanzado();
    }, BUSQUEDA_DEBOUNCE_MS);
  }

  function buscarProductosInmediato() {
    clearBusquedaDebounce();
    return buscarAvanzado();
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
    function toNumber(v) {
      if (v === null || v === undefined) return NaN;
      var s = String(v).replace(",", ".");
      var n = Number(s);
      return Number.isFinite(n) ? n : NaN;
    }

    function format0(v) {
      var x = toNumber(v);
      if (!Number.isFinite(x)) return "0";
      return Math.round(x).toLocaleString("es-CO");
    }

    var c = p.caracteristica || {};
    var promoActiva = p.promocion_activa ?? c.promocion_activa ?? false;
    var baseRaw =
      p.precio_base ??
      c.precio_base ??
      c.precio_venta ??
      p.precio_venta ??
      p.costo_unitario;
    var promoRaw = p.precio_promocion ?? c.precio_promocion ?? p.precioPromocion;
    var base = toNumber(baseRaw);
    var promo = toNumber(promoRaw);

    var precioPart = "";
    var hasPromo =
      !!promoActiva &&
      Number.isFinite(base) &&
      Number.isFinite(promo) &&
      promo > 0 &&
      promo < base;

    if (hasPromo) {
      var pct = Math.round(((base - promo) * 100.0) / base);
      precioPart =
        '<p class="precio-original">$<span>' +
        format0(base) +
        "</span></p>" +
        '<p class="precio-descuento">$<span>' +
        format0(promo) +
        "</span>" +
        (pct > 0 ? '<span class="descuento">-' + pct + "%</span>" : "") +
        "</p>";
    } else {
      precioPart =
        '<p><strong>$<span>' +
        format0(base) +
        '</span></strong></p>';
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
      '<button type="button" class="carrito-btn carrito-btn--carrusel js-carrito-index" data-producto-id="' +
      p.id +
      '" title="Agregar al carrito">&#128722;</button>' +
      "</div>"
    );
  }

  function csrfToken() {
    var el = document.querySelector("input[name=csrfmiddlewaretoken]");
    if (el && el.value) return el.value;
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function catalogoTieneEndpointCarrito() {
    return (
      typeof window.TECHNOVA_URL_CATALOGO_CARRITO === "string" &&
      window.TECHNOVA_URL_CATALOGO_CARRITO.length > 0
    );
  }

  async function postJsonCarritoSesion(url, body) {
    var t = csrfToken();
    var r = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": t,
      },
      body: JSON.stringify(body),
    });
    var j = await r.json().catch(function () {
      return {};
    });
    if (!r.ok) {
      throw new Error(j.message || r.statusText || "Error");
    }
    if (j.ok !== true) {
      throw new Error(j.message || "Respuesta inválida del servidor.");
    }
    return j;
  }

  async function agregarCarritoIndexProducto(productoId, nombre) {
    if (!catalogoTieneEndpointCarrito()) {
      throw new Error("Carrito no disponible en esta página.");
    }
    var j = await postJsonCarritoSesion(window.TECHNOVA_URL_CATALOGO_CARRITO, {
      producto_id: parseInt(productoId, 10),
    });
    if (Array.isArray(j.carrito_preview)) {
      document.dispatchEvent(
        new CustomEvent("technova:carrito-preview-update", {
          detail: { items: j.carrito_preview },
        })
      );
    }
    var label = nombre || "Producto agregado al carrito";
    if (window.CarritoAlerts && typeof window.CarritoAlerts.success === "function") {
      await window.CarritoAlerts.success(label);
    } else if (window.Swal) {
      await window.Swal.fire({
        icon: "success",
        title: "Listo",
        text: label,
        timer: 2000,
        showConfirmButton: false,
      });
    }
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

  function cerrarPanelFiltrosIndex() {
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (fc) {
      fc.style.display = "none";
      fc.setAttribute("aria-hidden", "true");
    }
    if (toggle) toggle.classList.remove("active");
  }

  function abrirPanelFiltrosIndex() {
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (fc) {
      fc.style.display = "block";
      fc.setAttribute("aria-hidden", "false");
    }
    if (toggle) toggle.classList.add("active");
  }

  /** Solo campos del panel (marca, categoría, precios, disponibilidad); no borra el texto del buscador. */
  function limpiarTodoPanelFiltros() {
    clearBusquedaDebounce();
    _filtroIndexSilenciaChange = true;
    try {
      var marca = document.getElementById("filtroMarca");
      var categoria = document.getElementById("filtroCategoria");
      var min = document.getElementById("filtroPrecioMin");
      var max = document.getElementById("filtroPrecioMax");
      var disp = document.getElementById("filtroDisponibilidad");
      if (marca) marca.value = "";
      if (categoria) categoria.value = "";
      if (min) min.value = "";
      if (max) max.value = "";
      if (disp) disp.value = "";
    } finally {
      _filtroIndexSilenciaChange = false;
    }
    cerrarPanelFiltrosIndex();
    buscarProductosInmediato();
  }

  function limpiarFiltros() {
    clearBusquedaDebounce();
    _filtroIndexSilenciaChange = true;
    try {
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
    } finally {
      _filtroIndexSilenciaChange = false;
    }
    cerrarPanelFiltrosIndex();
    document.getElementById("resultadosBusqueda")?.classList.remove("show");
    var o = document.getElementById("productosOriginales");
    if (o) o.style.display = "";
  }

  function onCarritoInvitadoClick(ev) {
    var btn = ev.target.closest && ev.target.closest(".js-carrito-index");
    if (!btn || !window.TECHNOVA_INDEX_PUBLIC) return;
    if (btn.disabled) return;
    ev.preventDefault();
    ev.stopPropagation();
    var pid = btn.getAttribute("data-producto-id");
    if (!pid) return;
    var wrap = btn.closest(".producto, .producto-card");
    var h3 = wrap && wrap.querySelector("h3");
    var nombre = h3 ? h3.textContent.trim() : "Producto";
    agregarCarritoIndexProducto(pid, nombre).catch(function (e) {
      var msg = e.message || "No se pudo agregar al carrito.";
      if (window.Swal) {
        window.Swal.fire({ icon: "error", title: "Error", text: msg });
      } else {
        window.alert(msg);
      }
    });
  }

  function alturaBandaSuperiorIndex() {
    var shell = document.querySelector(".tecn-header-shell");
    if (!shell) return 20;
    return Math.round(shell.getBoundingClientRect().height) + 16;
  }

  /** Desplaza la vista al bloque de resultados filtrados (arriba), tras pintar el grid. */
  function scrollVistaResultadosProductos() {
    var el = document.getElementById("resultadosBusqueda");
    if (!el || !el.classList.contains("show")) return;
    var y =
      el.getBoundingClientRect().top +
      window.scrollY -
      alturaBandaSuperiorIndex();
    window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
  }

  function despuesFiltroCatalogoScroll(promiseBusqueda) {
    Promise.resolve(promiseBusqueda).then(function () {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          scrollVistaResultadosProductos();
        });
      });
    });
  }

  function aplicarFiltroCategoria(val) {
    _filtroIndexSilenciaChange = true;
    try {
      var sel = document.getElementById("filtroCategoria");
      if (sel) sel.value = val || "";
    } finally {
      _filtroIndexSilenciaChange = false;
    }
    cerrarPanelFiltrosIndex();
    despuesFiltroCatalogoScroll(buscarProductosInmediato());
  }

  function aplicarFiltroMarca(val) {
    _filtroIndexSilenciaChange = true;
    try {
      var sel = document.getElementById("filtroMarca");
      if (sel) sel.value = val || "";
    } finally {
      _filtroIndexSilenciaChange = false;
    }
    cerrarPanelFiltrosIndex();
    despuesFiltroCatalogoScroll(buscarProductosInmediato());
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.TECHNOVA_API_PREFIX = window.TECHNOVA_API_PREFIX || "/api/v1";

    var formBusqueda = document.getElementById("indexFormBusqueda");
    if (formBusqueda) {
      formBusqueda.addEventListener("submit", function (ev) {
        ev.preventDefault();
        buscarProductosInmediato();
      });
    }

    var inputTerm = document.getElementById("busquedaTermino");
    if (inputTerm) {
      inputTerm.addEventListener("input", function () {
        buscarProductosDebounced();
      });
    }

    ["filtroMarca", "filtroCategoria", "filtroDisponibilidad"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener("change", function () {
          if (_filtroIndexSilenciaChange) return;
          buscarProductosInmediato();
          cerrarPanelFiltrosIndex();
        });
      }
    });
    ["filtroPrecioMin", "filtroPrecioMax"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener("input", function () {
          buscarProductosDebounced();
        });
        el.addEventListener("change", function () {
          if (_filtroIndexSilenciaChange) return;
          buscarProductosInmediato();
          cerrarPanelFiltrosIndex();
        });
      }
    });

    var btnLimpiarTodo = document.getElementById("btnLimpiarTodoFiltros");
    if (btnLimpiarTodo) {
      btnLimpiarTodo.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        limpiarTodoPanelFiltros();
      });
    }

    document.addEventListener("click", onCarritoInvitadoClick, true);

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

  window.buscarProductos = buscarProductosInmediato;
  window.limpiarFiltros = limpiarFiltros;
  window.limpiarTodoPanelFiltros = limpiarTodoPanelFiltros;
  window.toggleFiltros = function () {
    var el = document.getElementById("filtrosContainer");
    var btn = document.getElementById("btnFiltrosToggle");
    if (!el) return;
    var hidden =
      el.style.display === "none" ||
      window.getComputedStyle(el).display === "none";
    if (hidden) {
      abrirPanelFiltrosIndex();
    } else {
      cerrarPanelFiltrosIndex();
    }
  };

  document.addEventListener("click", function (ev) {
    var filtros = document.getElementById("filtrosContainer");
    var btn = document.getElementById("btnFiltrosToggle");
    if (!filtros || window.getComputedStyle(filtros).display === "none") return;
    var clickedInside =
      filtros.contains(ev.target) || (btn && btn.contains(ev.target));
    if (!clickedInside) {
      cerrarPanelFiltrosIndex();
    }
  });
})();
