/**
 * Carrusel nativo: cinta flex dentro de viewport con overflow:hidden;
 * flechas y contador en .tn-pg__stage (overflow visible) para no recortarlas.
 */
(function () {
  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function uniqueUrls(urls) {
    var out = [];
    var seen = {};
    (urls || []).forEach(function (u) {
      if (u == null) return;
      var t = String(u).trim();
      if (!t || seen[t]) return;
      seen[t] = true;
      out.push(t);
    });
    return out;
  }

  function resolveHost(host) {
    if (host && host.nodeType === 1) return host;
    return document.querySelector(".tn-pg--carousel");
  }

  function applyTransform(track, idx, n) {
    if (!track || n < 1) return;
    var pct = (idx / n) * 100;
    track.style.transform = "translateX(-" + pct + "%)";
  }

  function moverCarrusel(direccion, hostEl) {
    var host = resolveHost(hostEl);
    if (!host) return;
    var track = host.querySelector(".tn-pg__track");
    var n = parseInt(host.getAttribute("data-tn-slides") || "0", 10);
    if (!track || n < 2) return;

    var delta =
      direccion === "prev" || direccion === -1 || direccion === "<"
        ? -1
        : direccion === "next" || direccion === 1 || direccion === ">"
          ? 1
          : 0;
    if (!delta) return;

    var idx = parseInt(host.getAttribute("data-tn-idx") || "0", 10);
    idx = (idx + delta + n) % n;
    host.setAttribute("data-tn-idx", String(idx));
    applyTransform(track, idx, n);

    var counter = host.querySelector(".tn-pg__counter");
    if (counter) {
      counter.textContent = idx + 1 + " / " + n;
    }
  }

  function mount(host, urls, options) {
    if (!host) return;
    var alt = (options && options.alt) || "";
    var ph = (options && options.placeholder) || "/static/frontend/imagenes/placeholder.svg";
    var list = uniqueUrls(urls);
    if (!list.length) list = [ph];

    host.innerHTML = "";
    host.classList.add("tn-pg");
    host.removeAttribute("data-tn-slides");
    host.removeAttribute("data-tn-idx");

    /* Carrusel solo con 2+ URLs distintas (uniqueUrls elimina duplicados; si queda 1, no hay flechas). */
    if (list.length < 2) {
      host.innerHTML =
        '<div class="tn-pg__stage tn-pg__stage--solo">' +
        '<img class="tn-pg__img tn-pg__img--solo" src="' +
        esc(list[0]) +
        '" alt="' +
        esc(alt) +
        '" loading="lazy" decoding="async"/>' +
        "</div>";
      var img0 = host.querySelector(".tn-pg__img");
      if (img0) {
        img0.addEventListener("error", function () {
          this.onerror = null;
          this.src = ph;
        });
      }
      return;
    }

    var n = list.length;
    var slidesHtml = list
      .map(function (url, i) {
        return (
          '<div class="tn-pg__slide">' +
          '<img class="tn-pg__slide-img" src="' +
          esc(url) +
          '" alt="' +
          esc(alt + (n > 1 ? " (" + (i + 1) + ")" : "")) +
          '" loading="' +
          (i === 0 ? "eager" : "lazy") +
          '" decoding="async"/>' +
          "</div>"
        );
      })
      .join("");

    host.classList.add("tn-pg--carousel");
    host.setAttribute("data-tn-slides", String(n));
    host.setAttribute("data-tn-idx", "0");
    /* Ancho de la cinta: lo define el flex (cada slide = 100cqw del viewport en CSS). */
    host.innerHTML =
      '<div class="tn-pg__stage">' +
      '<div class="tn-pg__viewport">' +
      '<div class="tn-pg__track">' +
      slidesHtml +
      "</div></div>" +
      '<button type="button" class="tn-pg__nav tn-pg__nav--prev" aria-label="Imagen anterior" onclick="window.moverCarrusel(-1, this.closest(\'.tn-pg--carousel\'))">' +
      "&lt;</button>" +
      '<button type="button" class="tn-pg__nav tn-pg__nav--next" aria-label="Imagen siguiente" onclick="window.moverCarrusel(1, this.closest(\'.tn-pg--carousel\'))">' +
      "&gt;</button>" +
      '<div class="tn-pg__counter" aria-live="polite">1 / ' +
      n +
      "</div>" +
      "</div>";

    var track = host.querySelector(".tn-pg__track");
    var slides = host.querySelectorAll(".tn-pg__slide");
    var useCqw =
      typeof CSS !== "undefined" &&
      CSS.supports &&
      CSS.supports("width", "1cqw");
    if (!useCqw) {
      track.style.width = n * 100 + "%";
      var pctEach = 100 / n;
      slides.forEach(function (slide) {
        slide.style.flex = "0 0 " + pctEach + "%";
        slide.style.minWidth = pctEach + "%";
        slide.style.width = pctEach + "%";
      });
    }
    slides.forEach(function (slide) {
      var im = slide.querySelector(".tn-pg__slide-img");
      if (im) {
        im.addEventListener("error", function () {
          this.onerror = null;
          this.src = ph;
        });
      }
    });

    applyTransform(track, 0, n);
  }

  window.moverCarrusel = moverCarrusel;

  window.TechnovaProductoGallery = {
    mount: mount,
    uniqueUrls: uniqueUrls,
    moverCarrusel: moverCarrusel,
  };
})();
