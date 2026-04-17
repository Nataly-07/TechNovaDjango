/**
 * Ficha de producto en ventana modal (sin salir del catálogo).
 * Requiere window.TechnovaApi.
 */
(function () {
  var rootEl = null;

  function escapeHtml(texto) {
    return String(texto || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function imgProductoUrl(p) {
    var im = p && p.imagen ? p.imagen : "";
    if (im.indexOf("http") === 0) return im;
    if (im) {
      if (im.indexOf("/") === 0) return im;
      return "/static/frontend/imagenes/" + im;
    }
    return "/static/frontend/imagenes/placeholder.svg";
  }

  function formatPrecioCOP(val) {
    var raw = String(val ?? "").replace(",", ".").trim();
    var n = Number(raw);
    if (Number.isNaN(n)) return escapeHtml(String(val));
    return escapeHtml(
      n.toLocaleString("es-CO", { maximumFractionDigits: n % 1 === 0 ? 0 : 2 })
    );
  }

  function specDtDd(label, value) {
    var v =
      value != null && String(value).trim() !== "" ? String(value).trim() : "—";
    return (
      '<div class="producto-detalle-spec-item"><dt>' +
      escapeHtml(label) +
      '</dt><dd class="producto-detalle-spec-val">' +
      escapeHtml(v) +
      "</dd></div>"
    );
  }

  function buildInnerHtml(data) {
    var c = data.caracteristica || {};
    var precioRaw =
      c.precio_venta || data.precio_venta || data.costo_unitario || "—";
    var desc = (c.descripcion && String(c.descripcion).trim()) || "";
    var stockNum =
      data.stock != null && !Number.isNaN(Number(data.stock))
        ? Number(data.stock)
        : null;
    var cantidadTxt = "—";
    var stockClass = "";
    if (stockNum !== null) {
      if (stockNum <= 0) {
        cantidadTxt = "Agotado (0 unidades)";
        stockClass = " producto-detalle-spec-val--agotado";
      } else {
        cantidadTxt =
          stockNum === 1
            ? "1 unidad disponible"
            : stockNum + " unidades disponibles";
        if (stockNum <= 7) {
          stockClass = " producto-detalle-spec-val--bajo";
        } else if (stockNum <= 20) {
          stockClass = " producto-detalle-spec-val--medio";
        } else {
          stockClass = " producto-detalle-spec-val--alto";
        }
      }
    }
    var descHtml = desc
      ? '<p class="producto-detalle-descripcion-texto">' +
        escapeHtml(desc).replaceAll("\n", "<br/>") +
        "</p>"
      : '<p class="producto-detalle-descripcion-vacio">Sin descripción para este producto.</p>';
    return (
      '<div class="producto-detalle-layout producto-detalle-layout--modal">' +
      '<div class="producto-detalle-imagen">' +
      '<div class="producto-detalle-imagen-inner" data-tn-gallery-host></div>' +
      "</div>" +
      '<div class="producto-detalle-info">' +
      '<p class="producto-detalle-eyebrow">Ficha de producto</p>' +
      '<h1 id="producto-modal-title" class="producto-detalle-titulo">' +
      escapeHtml(data.nombre) +
      "</h1>" +
      '<dl class="producto-detalle-specs">' +
      specDtDd("Marca", c.marca) +
      specDtDd("Categoría", c.categoria) +
      specDtDd("Color", c.color) +
      '<div class="producto-detalle-spec-item"><dt>Cantidad</dt><dd class="producto-detalle-spec-val' +
      stockClass +
      '">' +
      escapeHtml(cantidadTxt) +
      "</dd></div>" +
      "</dl>" +
      '<div class="producto-detalle-descripcion-bloque">' +
      '<h2 class="producto-detalle-subtitulo">Descripción</h2>' +
      descHtml +
      "</div>" +
      '<div class="producto-detalle-precio-caja">' +
      '<span class="producto-detalle-precio-label">Precio</span>' +
      '<span class="producto-detalle-precio-monto">$ ' +
      formatPrecioCOP(precioRaw) +
      "</span>" +
      "</div>" +
      "</div></div>"
    );
  }

  function ensureRoot() {
    if (rootEl) return rootEl;
    rootEl = document.createElement("div");
    rootEl.id = "producto-modal-root";
    rootEl.className = "producto-modal-root";
    rootEl.setAttribute("aria-hidden", "true");
    rootEl.innerHTML =
      '<div class="producto-modal-backdrop" tabindex="-1"></div>' +
      '<div class="producto-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="producto-modal-title">' +
      '<button type="button" class="producto-modal-cerrar" aria-label="Cerrar">&times;</button>' +
      '<div class="producto-modal-body" id="producto-modal-body"></div>' +
      "</div>";
    document.body.appendChild(rootEl);
    var b = rootEl.querySelector(".producto-modal-backdrop");
    var c = rootEl.querySelector(".producto-modal-cerrar");
    b.addEventListener("click", close);
    c.addEventListener("click", close);
    return rootEl;
  }

  var prevOverflow = "";

  function onKey(ev) {
    if (ev.key === "Escape") close();
  }

  function open(id) {
    if (!window.TechnovaApi || typeof window.TechnovaApi.get !== "function") {
      window.location.href = "/producto/" + id + "/";
      return Promise.resolve();
    }
    var root = ensureRoot();
    var body = root.querySelector("#producto-modal-body");
    body.innerHTML =
      '<div class="producto-modal-cargando">Cargando…</div>';
    root.classList.add("is-open");
    root.setAttribute("aria-hidden", "false");
    prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);

    return window.TechnovaApi
      .get("/producto/" + id + "/")
      .then(function (data) {
        body.innerHTML =
          '<article class="producto-detalle-flotante producto-detalle-flotante--modal">' +
          buildInnerHtml(data) +
          "</article>";
        var gh = body.querySelector("[data-tn-gallery-host]");
        if (gh) {
          if (window.TechnovaProductoGallery) {
            var urls = [];
            if (data.imagen && String(data.imagen).trim()) {
              urls.push(imgProductoUrl(data));
            }
            (data.imagenes_adicionales || []).forEach(function (x) {
              if (x && x.url && String(x.url).trim()) {
                urls.push(imgProductoUrl({ imagen: x.url }));
              }
            });
            window.TechnovaProductoGallery.mount(gh, urls, {
              alt: data.nombre || "",
              placeholder: "/static/frontend/imagenes/placeholder.svg",
            });
          } else {
            gh.innerHTML =
              '<div class="tn-pg__stage tn-pg__stage--solo">' +
              '<img src="' +
              escapeHtml(imgProductoUrl(data)) +
              '" alt="' +
              escapeHtml(data.nombre) +
              '" class="tn-pg__img tn-pg__img--solo" loading="lazy" decoding="async" onerror="this.src=\'/static/frontend/imagenes/placeholder.svg\'"/>' +
              "</div>";
          }
        }
      })
      .catch(function (e) {
        body.innerHTML =
          '<p class="producto-modal-error">' +
          escapeHtml(e.message || "No se pudo cargar el producto.") +
          "</p>";
      });
  }

  function close() {
    if (window.TECHNOVA_PRODUCTO_DETALLE_STANDALONE) {
      var dest =
        (typeof window.TECHNOVA_URL_ROOT === "string" &&
          window.TECHNOVA_URL_ROOT.trim()) ||
        "/";
      window.location.href = dest;
      return;
    }
    var root = document.getElementById("producto-modal-root");
    if (!root) return;
    root.classList.remove("is-open");
    root.setAttribute("aria-hidden", "true");
    document.body.style.overflow = prevOverflow || "";
    document.removeEventListener("keydown", onKey);
  }

  document.addEventListener("click", function (ev) {
    var a = ev.target.closest(
      "a.js-producto-modal-link, a[data-producto-modal]"
    );
    if (!a) return;
    var id =
      a.getAttribute("data-producto-id") || a.getAttribute("data-producto-modal");
    if (!id) return;
    ev.preventDefault();
    open(parseInt(id, 10));
  });

  window.TechnovaProductoModal = {
    open: open,
    close: close,
  };
})();
