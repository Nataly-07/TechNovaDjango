/**
 * Inicio: catálogo y búsqueda avanzada contra /api/v1/producto/ (proyecto Java adaptado).
 */
(function () {
  var catalogoItemsCache = [];
  /** Sincronizado con el servidor al agregar líneas; usado por el panel Carrito del header. */
  var carritoPreviewItems = [];

  function escapeHtml(texto) {
    return String(texto || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function csrfToken() {
    var el = document.querySelector("input[name=csrfmiddlewaretoken]");
    if (el && el.value) return el.value;
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /** True si esta pagina incluyo endpoints web de catalogo (sesion Django + CSRF). */
  function catalogoTieneEndpointsSesion() {
    return (
      typeof window.TECHNOVA_URL_CATALOGO_CARRITO === "string" &&
      window.TECHNOVA_URL_CATALOGO_CARRITO.length > 0
    );
  }

  async function postJsonSesion(url, body) {
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
      throw new Error(j.message || "Respuesta invalida del servidor.");
    }
    return j;
  }

  function imgUrl(p) {
    const im = p.imagen || "";
    if (im.startsWith("http")) return im;
    if (im) return "/static/frontend/imagenes/" + im;
    return "/static/frontend/imagenes/placeholder.svg";
  }

  function toNumber(v) {
    if (v === null || v === undefined) return NaN;
    const s = String(v).replace(",", ".");
    const n = Number(s);
    return Number.isFinite(n) ? n : NaN;
  }

  function format0(n) {
    const x = toNumber(n);
    if (!Number.isFinite(x)) return "0";
    return Math.round(x).toLocaleString("es-CO");
  }

  function precioHtml(p) {
    const c = p.caracteristica || {};
    const promoActiva = p.promocion_activa ?? c.promocion_activa ?? false;
    const baseRaw =
      p.precio_base ??
      c.precio_base ??
      c.precio_venta ??
      p.precio_venta ??
      p.costo_unitario;
    const promoRaw = p.precio_promocion ?? c.precio_promocion ?? p.precioPromocion;

    const base = toNumber(baseRaw);
    const promo = toNumber(promoRaw);

    const hasPromo =
      !!promoActiva && Number.isFinite(base) && Number.isFinite(promo) && promo > 0 && promo < base;

    if (hasPromo) {
      const pct = Math.round(((base - promo) * 100.0) / base);
      return (
        '<p class="precio-original">$<span>' +
        format0(base) +
        '</span></p>' +
        '<p class="precio-descuento">$<span>' +
        format0(promo) +
        "</span>" +
        (pct > 0 ? '<span class="descuento">-' + pct + "%</span>" : "") +
        "</p>"
      );
    }

    return (
      '<p><strong>$<span>' + format0(base) + "</span></strong></p>"
    );
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
      escapeHtml(imgUrl(p)) +
      '" alt="' +
      escapeHtml(p.nombre || "") +
      '" onerror="this.src=\'/static/frontend/imagenes/placeholder.svg\'"/>' +
      '<a href="/producto/' +
      p.id +
      '/" class="js-producto-modal-link" data-producto-id="' +
      p.id +
      '"><span class="detalles">Ver más detalles</span></a>' +
      "<h3>" +
      escapeHtml(p.nombre || "") +
      "</h3>" +
      '<div style="margin:5px 0;">' +
      disp +
      "</div>" +
      "<p>4.5 ⭐</p>" +
      precioHtml(p) +
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
    const firstTrack = document.querySelector(".carrusel-track");
    if (!firstTrack) return;
    /** Solo respetar SSR si el servidor ya pintó tarjetas; si vino vacío, la API sigue siendo la fuente (como antes del SSR). */
    var servidorTieneTarjetas = !!firstTrack.querySelector(".producto[data-id]");
    var marcarSsr =
      firstTrack.getAttribute("data-ssr") === "1" ||
      window.TECHNOVA_HOME_SSR === true;
    var usarSsrSinSobrescribir = marcarSsr && servidorTieneTarjetas;
    try {
      const data = await window.TechnovaApi.get("/producto/");
      const items = data.items || [];
      catalogoItemsCache = items;
      poblarSelectsFiltros(items);
      if (!usarSsrSinSobrescribir) {
        firstTrack.innerHTML =
          items.map(cardHtml).join("") || "<p>No hay productos.</p>";
      }
      document.dispatchEvent(new CustomEvent("technova:productos-cargados"));
    } catch (e) {
      if (!usarSsrSinSobrescribir) {
        firstTrack.innerHTML =
          '<p style="padding:20px;color:#e63946;">No se pudo cargar el catálogo. ' +
          (e.message || "") +
          "</p>";
      }
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
    document.getElementById("resultadosBusqueda")?.classList.remove("show");
    const o = document.getElementById("productosOriginales");
    if (o) o.style.display = "";
  }

  function uniqueSorted(values) {
    return Array.from(new Set(values.filter(Boolean))).sort(function (a, b) {
      return a.localeCompare(b, "es", { sensitivity: "base" });
    });
  }

  function poblarSelect(selectId, values) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    var current = sel.value || "";
    sel.innerHTML = '<option value="">Todas</option>';
    values.forEach(function (val) {
      var opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      sel.appendChild(opt);
    });
    sel.value = values.includes(current) ? current : "";
  }

  function poblarSelectsFiltros(items) {
    var marcas = uniqueSorted(
      items.map(function (p) {
        return (p.marca || (p.caracteristica && p.caracteristica.marca) || "").trim();
      })
    );
    var categorias = uniqueSorted(
      items.map(function (p) {
        return (p.categoria || (p.caracteristica && p.caracteristica.categoria) || "").trim();
      })
    );
    poblarSelect("filtroMarca", marcas);
    poblarSelect("filtroCategoria", categorias);
  }

  function getJsonScriptData(id) {
    try {
      var el = document.getElementById(id);
      if (!el) return [];
      return JSON.parse(el.textContent || "[]");
    } catch (_err) {
      return [];
    }
  }

  function precioFormato(raw) {
    var n = Number(String(raw || "0").replace(",", "."));
    if (!Number.isFinite(n)) return "$0";
    return "$" + n.toLocaleString("es-CO");
  }

  function escapeHtml(texto) {
    return String(texto || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function postFormJson(url, body) {
    var r = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken(),
      },
      body: new URLSearchParams(body),
    });
    var data = await r.json().catch(function () {
      return {};
    });
    if (!r.ok || data.ok === false) {
      throw new Error(data.message || "No se pudo completar la acción.");
    }
    return data;
  }

  function panelResumenInit() {
    var panel = document.getElementById("panelResumenCliente");
    var body = document.getElementById("panelResumenBody");
    var title = document.getElementById("panelResumenTitulo");
    var closeBtn = document.getElementById("panelResumenCerrar");
    if (!panel || !body || !title) return;

    var favoritosData = getJsonScriptData("favoritosPreviewData");
    carritoPreviewItems = getJsonScriptData("carritoPreviewData") || [];
    var currentPanel = "favoritos";

    function renderFavoritos() {
      title.textContent = "Favoritos";
      if (!favoritosData.length) {
        body.innerHTML = '<p class="cliente-panel-item-sub">No tienes favoritos aún.</p><a href="' + window.TECHNOVA_URL_FAVORITOS + '" class="cliente-panel-link" style="display:inline-block;margin-top:8px;">Ir a favoritos</a>';
        return;
      }
      body.innerHTML = favoritosData
        .map(function (p) {
          return (
            '<div class="cliente-panel-row">' +
            '<div><div class="cliente-panel-item-title">' + escapeHtml(p.nombre) + '</div><div class="cliente-panel-item-sub">' + precioFormato(p.precio) + "</div></div>" +
            '<button type="button" class="cliente-panel-btn cliente-panel-btn--remove" data-act="quitar-favorito" data-id="' + p.id + '">Quitar</button>' +
            '<a href="' + window.TECHNOVA_URL_FAVORITOS + '" class="cliente-panel-link">Ir a favoritos</a>' +
            "</div>"
          );
        })
        .join("");
    }

    function renderCarrito() {
      title.textContent = "Carrito";
      if (!carritoPreviewItems.length) {
        body.innerHTML = '<p class="cliente-panel-item-sub">Tu carrito está vacío.</p><a href="' + window.TECHNOVA_URL_CARRITO + '" class="cliente-panel-link" style="display:inline-block;margin-top:8px;">Ir a carrito</a>';
        return;
      }
      body.innerHTML = carritoPreviewItems
        .map(function (it) {
          var canDec = Number(it.cantidad || 1) > 1;
          var disabledAttr = canDec ? "" : " disabled";
          return (
            '<div class="cliente-panel-row">' +
            '<div><div class="cliente-panel-item-title">' + escapeHtml(it.nombre_producto) + '</div><div class="cliente-panel-item-sub">Cant: ' + it.cantidad + " - " + precioFormato(it.precio_unitario) + "</div></div>" +
            '<div class="cliente-panel-qty-wrap">' +
            '<button type="button" class="cliente-panel-btn cliente-panel-btn--qty" data-act="restar-carrito" data-detalle-id="' + it.detalle_id + '" data-cantidad="' + it.cantidad + '"' + disabledAttr + '>-</button>' +
            '<span class="cliente-panel-qty">' + it.cantidad + "</span>" +
            '<button type="button" class="cliente-panel-btn cliente-panel-btn--qty" data-act="sumar-carrito" data-detalle-id="' + it.detalle_id + '" data-cantidad="' + it.cantidad + '">+</button>' +
            "</div>" +
            '<button type="button" class="cliente-panel-btn cliente-panel-btn--remove" data-act="quitar-carrito" data-detalle-id="' + it.detalle_id + '">Quitar</button>' +
            '<a href="' + window.TECHNOVA_URL_CARRITO + '" class="cliente-panel-link">Ir a carrito</a>' +
            "</div>"
          );
        })
        .join("");
    }

    function showPanel(which) {
      currentPanel = which || currentPanel;
      panel.style.display = "block";
      if (currentPanel === "favoritos") renderFavoritos();
      if (currentPanel === "carrito") renderCarrito();
    }

    document.querySelectorAll(".js-panel-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        showPanel(btn.getAttribute("data-panel"));
      });
    });
    closeBtn?.addEventListener("click", function () {
      panel.style.display = "none";
    });

    body.addEventListener("click", async function (ev) {
      var el = ev.target.closest("button[data-act]");
      if (!el) return;
      el.disabled = true;
      try {
        var action = el.getAttribute("data-act");
        var detalleId = parseInt(el.getAttribute("data-detalle-id") || "0", 10);
        var productoId = parseInt(el.getAttribute("data-id") || "0", 10);
        if (action === "quitar-favorito") {
          await postFormJson(window.TECHNOVA_URL_FAVORITO_QUITAR, {
            producto_id: el.getAttribute("data-id"),
          });
          favoritosData = favoritosData.filter(function (p) {
            return Number(p.id) !== productoId;
          });
          showPanel("favoritos");
        } else if (action === "sumar-carrito") {
          var qty = parseInt(el.getAttribute("data-cantidad") || "1", 10) + 1;
          await postFormJson(window.TECHNOVA_URL_CARRITO_ACTUALIZAR, {
            detalle_id: el.getAttribute("data-detalle-id"),
            cantidad: qty,
          });
          carritoPreviewItems = carritoPreviewItems.map(function (it) {
            if (Number(it.detalle_id) === detalleId) {
              it.cantidad = qty;
            }
            return it;
          });
          showPanel("carrito");
        } else if (action === "restar-carrito") {
          var qtyDec = parseInt(el.getAttribute("data-cantidad") || "1", 10) - 1;
          if (qtyDec < 1) {
            qtyDec = 1;
          }
          await postFormJson(window.TECHNOVA_URL_CARRITO_ACTUALIZAR, {
            detalle_id: el.getAttribute("data-detalle-id"),
            cantidad: qtyDec,
          });
          carritoPreviewItems = carritoPreviewItems.map(function (it) {
            if (Number(it.detalle_id) === detalleId) {
              it.cantidad = qtyDec;
            }
            return it;
          });
          showPanel("carrito");
        } else if (action === "quitar-carrito") {
          await postFormJson(window.TECHNOVA_URL_CARRITO_ELIMINAR, {
            detalle_id: el.getAttribute("data-detalle-id"),
          });
          carritoPreviewItems = carritoPreviewItems.filter(function (it) {
            return Number(it.detalle_id) !== detalleId;
          });
          showPanel("carrito");
        }
      } catch (e) {
        if (window.TechnovaUi) {
          await window.TechnovaUi.error(e.message || "No se pudo completar la acción.");
        } else {
          window.alert(e.message || "No se pudo completar la acción.");
        }
      } finally {
          el.disabled = false;
      }
    });

    document.addEventListener("technova:carrito-preview-synced", function () {
      if (panel.style.display !== "none" && currentPanel === "carrito") renderCarrito();
    });
  }

  /** El clic puede caer en un nodo #text (p. ej. emoji dentro del boton); esos nodos no tienen .closest(). */
  function clickTargetElement(ev) {
    var t = ev.target;
    if (t && t.nodeType === 1) return t;
    if (t && t.parentElement) return t.parentElement;
    return null;
  }

  function scrollToCatalogoInicio() {
    var el = document.getElementById("catalogo-publico");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function aplicarFiltroCategoriaInicio(val) {
    var sel = document.getElementById("filtroCategoria");
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (sel) sel.value = val || "";
    if (fc) {
      fc.style.display = "block";
      if (toggle) toggle.classList.add("active");
    }
    scrollToCatalogoInicio();
    buscarAvanzado();
  }

  function aplicarFiltroMarcaInicio(val) {
    var sel = document.getElementById("filtroMarca");
    var fc = document.getElementById("filtrosContainer");
    var toggle = document.getElementById("btnFiltrosToggle");
    if (sel) sel.value = val || "";
    if (fc) {
      fc.style.display = "block";
      if (toggle) toggle.classList.add("active");
    }
    scrollToCatalogoInicio();
    buscarAvanzado();
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.TECHNOVA_API_PREFIX = window.TECHNOVA_API_PREFIX || "/api/v1";
    cargarCatalogo();

    document.addEventListener(
      "click",
      function (ev) {
        var el = clickTargetElement(ev);
        var b = el && el.closest ? el.closest(".js-carrito") : null;
        var f = el && el.closest ? el.closest(".js-favorito") : null;
        if (!b && !f) return;
        if (b) {
          ev.preventDefault();
          importarCarrito(b.getAttribute("data-producto-id"));
          return;
        }
        if (f) {
          ev.preventDefault();
          toggleFavorito(f.getAttribute("data-producto-id"));
        }
      },
      true
    );

    document.querySelectorAll(".index-sub-cat").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        aplicarFiltroCategoriaInicio(btn.getAttribute("data-categoria") || "");
      });
    });

    document.querySelectorAll(".index-sub-marca").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        aplicarFiltroMarcaInicio(btn.getAttribute("data-marca") || "");
      });
    });

    panelResumenInit();
    if (Array.isArray(catalogoItemsCache) && catalogoItemsCache.length) {
      poblarSelectsFiltros(catalogoItemsCache);
    }
  });

  async function importarCarrito(productoId) {
    /* /inicio/ solo es accesible con sesion Django: priorizar POST con CSRF (no JWT). */
    if (catalogoTieneEndpointsSesion()) {
      try {
        var j = await postJsonSesion(window.TECHNOVA_URL_CATALOGO_CARRITO, {
          producto_id: parseInt(productoId, 10),
        });
        if (Array.isArray(j.carrito_preview)) {
          carritoPreviewItems.length = 0;
          j.carrito_preview.forEach(function (it) {
            carritoPreviewItems.push(it);
          });
          document.dispatchEvent(new CustomEvent("technova:carrito-preview-synced"));
        }
        if (window.TechnovaUi) {
          var pid = parseInt(productoId, 10);
          var prod = (catalogoItemsCache || []).find(function (p) {
            return Number(p.id) === pid;
          });
          var nombre = (prod && prod.nombre) || "Producto agregado al carrito";
          if (window.CarritoAlerts && typeof window.CarritoAlerts.success === "function") {
            await window.CarritoAlerts.success(nombre);
          } else {
            await window.TechnovaUi.toastOk("Producto agregado al carrito");
          }
        }
      } catch (e) {
        if (window.TechnovaUi) {
          await window.TechnovaUi.error(e.message || "No se pudo agregar al carrito.");
        }
      }
      return;
    }
    if (!window.TechnovaAuth.isLoggedIn()) {
      if (window.TechnovaUi) {
        await window.TechnovaUi.needLogin("Inicia sesión para usar el carrito.");
      } else {
        window.location.href = "/login/";
      }
      return;
    }
    const uid = window.TechnovaAuth.getUsuarioId();
    try {
      await window.TechnovaApi.post("/carrito/" + uid + "/agregar/", {
        producto_id: parseInt(productoId, 10),
        cantidad: 1,
      });
      if (window.TechnovaUi) {
        var pid2 = parseInt(productoId, 10);
        var prod2 = (catalogoItemsCache || []).find(function (p) {
          return Number(p.id) === pid2;
        });
        var nombre2 = (prod2 && prod2.nombre) || "Producto agregado al carrito";
        if (window.CarritoAlerts && typeof window.CarritoAlerts.success === "function") {
          await window.CarritoAlerts.success(nombre2);
        } else {
          await window.TechnovaUi.toastOk("Producto agregado al carrito");
        }
      }
    } catch (e) {
      if (window.TechnovaUi) {
        await window.TechnovaUi.error(e.message || "No se pudo agregar.");
      }
    }
  }

  async function toggleFavorito(productoId) {
    if (
      typeof window.TECHNOVA_URL_CATALOGO_FAVORITO === "string" &&
      window.TECHNOVA_URL_CATALOGO_FAVORITO.length > 0
    ) {
      try {
        await postJsonSesion(window.TECHNOVA_URL_CATALOGO_FAVORITO, {
          producto_id: parseInt(productoId, 10),
        });
        if (window.TechnovaUi) {
          await window.TechnovaUi.toastOk("Favoritos actualizados");
        }
      } catch (e) {
        if (window.TechnovaUi) {
          await window.TechnovaUi.error(e.message || "No se pudo actualizar favoritos.");
        }
      }
      return;
    }
    if (!window.TechnovaAuth.isLoggedIn()) {
      if (window.TechnovaUi) {
        await window.TechnovaUi.needLogin("Inicia sesión para usar favoritos.");
      } else {
        window.location.href = "/login/";
      }
      return;
    }
    const uid = window.TechnovaAuth.getUsuarioId();
    try {
      await window.TechnovaApi.post(
        "/favoritos/usuario/" + uid + "/producto/" + productoId + "/toggle/",
        {}
      );
      if (window.TechnovaUi) {
        await window.TechnovaUi.toastOk("Favoritos actualizados");
      }
    } catch (e) {
      if (window.TechnovaUi) {
        await window.TechnovaUi.error(e.message || "Error en favoritos.");
      }
    }
  }

  window.buscarProductos = buscarAvanzado;
  window.limpiarFiltros = limpiarFiltros;
  window.toggleFiltros = function () {
    const el = document.getElementById("filtrosContainer");
    const btn = document.getElementById("btnFiltrosToggle");
    if (!el) return;
    var shouldOpen = el.style.display === "none";
    el.style.display = shouldOpen ? "block" : "none";
    if (btn) btn.classList.toggle("active", shouldOpen);
  };
  document.addEventListener("click", function (ev) {
    var filtros = document.getElementById("filtrosContainer");
    var btn = document.getElementById("btnFiltrosToggle");
    if (!filtros || filtros.style.display === "none") return;
    var clickedInside = filtros.contains(ev.target) || (btn && btn.contains(ev.target));
    if (!clickedInside) {
      filtros.style.display = "none";
      btn?.classList.remove("active");
    }
  });
})();
