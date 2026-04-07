/**
 * Módulo Mensajes — WebSocket + API sesión (admin / empleado), alineado con Spring Boot.
 * Configuración: window.TN_MENSAJES
 */
(function () {
  const CFG = window.TN_MENSAJES || window.TN_STAFF_CHAT;
  if (!CFG) return;

  const seenIds = new Set();
  let ws = null;
  let activeEmpId = null;

  function getCookie(name) {
    const m = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
    return m ? decodeURIComponent(m[2]) : null;
  }

  function csrfHeaders() {
    const t = getCookie("csrftoken");
    return t ? { "X-CSRFToken": t } : {};
  }

  function relTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return "hace un momento";
    if (diff < 3600) return "hace " + Math.floor(diff / 60) + " min";
    if (diff < 86400) return "hace " + Math.floor(diff / 3600) + " h";
    return d.toLocaleString("es-CO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  function historialUrl(empId) {
    return CFG.urls.historialTpl.replace("999999", String(empId));
  }

  function reclamoUrl(rid) {
    return CFG.urls.reclamoTpl.replace("999999", String(rid));
  }

  async function fetchJson(url, opts) {
    const method = (opts && opts.method) || "GET";
    const headers = { ...csrfHeaders(), ...(opts && opts.headers) };
    if (method !== "GET" && method !== "HEAD") {
      headers["Content-Type"] = "application/json";
    }
    const r = await fetch(url, {
      credentials: "same-origin",
      headers,
      ...opts,
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.message || "Error de red");
    return j;
  }

  function el(sel) {
    return document.querySelector(sel);
  }

  function renderMessage(m) {
    if (seenIds.has(m.id)) return;
    seenIds.add(m.id);
    const out = m.remitenteUsuarioId === CFG.viewerId;
    const row = document.createElement("div");
    row.className = "tn-chat__row " + (out ? "tn-chat__row--out" : "tn-chat__row--in");
    const bubble = document.createElement("div");
    bubble.className = "tn-chat__bubble " + (out ? "tn-chat__bubble--out" : "tn-chat__bubble--in");
    bubble.textContent = m.mensaje || "";
    if (m.reclamoId) {
      const a = document.createElement("a");
      a.className = "tn-chat__chip";
      a.href = "#";
      a.textContent = "Ver reclamo #" + m.reclamoId;
      a.addEventListener("click", function (e) {
        e.preventDefault();
        loadReclamo(m.reclamoId);
      });
      bubble.appendChild(document.createElement("br"));
      bubble.appendChild(a);
    }
    const meta = document.createElement("div");
    meta.className = "tn-chat__meta";
    const checks = document.createElement("span");
    if (out) {
      checks.className = "tn-chat__checks" + (m.leido ? " tn-chat__checks--read" : "");
      checks.textContent = m.leido ? "✓✓" : "✓";
      checks.title = m.leido ? "Leído" : "Enviado";
    }
    const t = document.createElement("span");
    t.textContent = relTime(m.creadoEn);
    meta.appendChild(checks);
    meta.appendChild(t);
    row.appendChild(bubble);
    row.appendChild(meta);
    el("#tnChatMessages").appendChild(row);
    el("#tnChatMessages").scrollTop = el("#tnChatMessages").scrollHeight;
  }

  async function loadHistorial(empId) {
    seenIds.clear();
    el("#tnChatMessages").innerHTML = "";
    const url =
      CFG.modo === "empleado" ? CFG.urls.historial : historialUrl(empId);
    const data = await fetchJson(url);
    (data.items || []).forEach(renderMessage);
    const lastR = [...(data.items || [])].reverse().find(function (x) {
      return x.reclamoId;
    });
    if (lastR && lastR.reclamoId) loadReclamo(lastR.reclamoId);
    else clearCtx();
  }

  async function loadReclamo(rid) {
    const box = el("#tnChatCtxBody");
    if (!box) return;
    box.innerHTML = "<p>Cargando…</p>";
    try {
      const data = await fetchJson(reclamoUrl(rid));
      const r = data.reclamo;
      const compras = (r.comprasRecientes || [])
        .map(function (c) {
          return "<li>#" + c.id + " — " + c.fecha + " — $" + c.total + " (" + c.estado + ")</li>";
        })
        .join("");
      box.innerHTML =
        "<h4>RECLAMO #" +
        r.id +
        "</h4>" +
        "<dl>" +
        "<dt>Cliente</dt><dd>" +
        (r.clienteNombre || "") +
        "<br><small>" +
        (r.clienteCorreo || "") +
        "</small></dd>" +
        "<dt>Estado</dt><dd>" +
        r.estado +
        "</dd>" +
        "<dt>Prioridad</dt><dd>" +
        r.prioridad +
        "</dd>" +
        "<dt>Problema</dt><dd><strong>" +
        (r.titulo || "") +
        "</strong><br>" +
        (r.descripcion || "") +
        "</dd>" +
        (r.respuesta
          ? "<dt>Respuesta</dt><dd>" + r.respuesta + "</dd>"
          : "") +
        "</dl>" +
        "<p><strong>Compras recientes</strong></p><ul style='margin:0;padding-left:18px;'>" +
        (compras || "<li>Sin compras registradas</li>") +
        "</ul>" +
        "<p><a href='" +
        CFG.urls.reclamosWeb +
        "'>Ir a reclamos</a></p>";
    } catch (e) {
      box.innerHTML = "<p class='tn-chat__ctx--empty'>No se pudo cargar el reclamo.</p>";
    }
  }

  function clearCtx() {
    const box = el("#tnChatCtxBody");
    if (box) box.innerHTML = "<p class='tn-chat__ctx--empty'>Selecciona un reclamo en el hilo o envía uno vinculado.</p>";
  }

  function connectWs(empId) {
    if (ws) {
      try {
        ws.close();
      } catch (e) {}
    }
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = proto + "//" + location.host + "/ws/mensajes/" + empId + "/";
    ws = new WebSocket(url);
    ws.onmessage = function (ev) {
      try {
        const p = JSON.parse(ev.data);
        if (p.event === "new_message" && p.message) renderMessage(p.message);
      } catch (e) {}
    };
  }

  async function sendMessage() {
    const ta = el("#tnChatInput");
    const text = (ta && ta.value || "").trim();
    if (!text) return;
    if (CFG.modo === "admin" && !activeEmpId) return;
    const reclamoRaw = el("#tnChatReclamoId") && el("#tnChatReclamoId").value.trim();
    const body = { mensaje: text };
    if (CFG.modo === "admin") body.empleado_usuario_id = activeEmpId;
    if (reclamoRaw) {
      const rid = parseInt(reclamoRaw, 10);
      if (!Number.isNaN(rid)) body.reclamo_id = rid;
    }
    const btn = el("#tnChatSend");
    if (btn) btn.disabled = true;
    try {
      const data = await fetchJson(CFG.urls.enviar, { method: "POST", body: JSON.stringify(body) });
      if (data.message) renderMessage(data.message);
      ta.value = "";
      if (CFG.modo === "admin") refreshConversaciones().catch(function () {});
    } catch (e) {
      alert(e.message || "No se pudo enviar");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function refreshConversaciones() {
    if (CFG.modo !== "admin") return;
    const data = await fetchJson(CFG.urls.conversaciones);
    const list = el("#tnChatConvList");
    if (!list) return;
    list.innerHTML = "";
    (data.items || []).forEach(function (c) {
      const div = document.createElement("div");
      div.className = "tn-chat__conv" + (c.empleadoUsuarioId === activeEmpId ? " tn-chat__conv--active" : "");
      div.dataset.empId = c.empleadoUsuarioId;
      const ini = (c.empleadoNombre || "E").trim().slice(0, 2).toUpperCase();
      div.innerHTML =
        "<div class='tn-chat__avatar'>" +
        ini +
        "</div>" +
        "<div class='tn-chat__conv-body'><div class='tn-chat__conv-name'>" +
        (c.empleadoNombre || "") +
        "</div>" +
        "<div class='tn-chat__conv-preview'>" +
        (c.ultimoMensaje || "") +
        "</div></div>" +
        (c.noLeidosAdmin
          ? "<span class='tn-chat__badge'>" + c.noLeidosAdmin + "</span>"
          : "");
      div.addEventListener("click", function () {
        selectEmp(c.empleadoUsuarioId, c.empleadoNombre);
      });
      list.appendChild(div);
    });
  }

  function selectEmp(empId, nombre) {
    activeEmpId = empId;
    const head = el("#tnChatHeadTitle");
    if (head) head.textContent = nombre || "Empleado #" + empId;
    document.querySelectorAll(".tn-chat__conv").forEach(function (n) {
      n.classList.toggle("tn-chat__conv--active", parseInt(n.dataset.empId, 10) === empId);
    });
    const btn = el("#tnChatSend");
    if (btn) btn.disabled = false;
    loadHistorial(empId).catch(function () {
      alert("No se pudo cargar el historial");
    });
    connectWs(empId);
  }

  async function buscarEmpleados(q) {
    const data = await fetchJson(CFG.urls.buscar + encodeURIComponent(q || ""));
    const list = el("#tnChatSearchList");
    if (!list) return;
    list.innerHTML = "";
    (data.items || []).forEach(function (u) {
      const div = document.createElement("div");
      div.className = "tn-chat__conv";
      const ini = (u.nombre || "E").trim().slice(0, 2).toUpperCase();
      div.innerHTML =
        "<div class='tn-chat__avatar'>" +
        ini +
        "</div><div class='tn-chat__conv-body'><div class='tn-chat__conv-name'>" +
        (u.nombre || "") +
        "</div><div class='tn-chat__conv-preview'>" +
        (u.correo || "") +
        "</div></div>";
      div.addEventListener("click", function () {
        selectEmp(u.id, u.nombre);
        list.innerHTML = "";
        el("#tnChatSearch").value = "";
      });
      list.appendChild(div);
    });
  }

  function init() {
    const form = el("#tnChatForm");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        sendMessage();
      });
    }
    const search = el("#tnChatSearch");
    if (search && CFG.modo === "admin") {
      let t;
      search.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () {
          buscarEmpleados(search.value).catch(function () {});
        }, 280);
      });
    }
    if (CFG.modo === "admin") {
      const sb = el("#tnChatSend");
      if (sb) sb.disabled = true;
      refreshConversaciones().catch(function () {});
      activeEmpId = null;
    } else {
      activeEmpId = CFG.empleadoThreadId;
      const head = el("#tnChatHeadTitle");
      if (head) head.textContent = "Administración";
      const sb = el("#tnChatSend");
      if (sb) sb.disabled = false;
      loadHistorial(activeEmpId).catch(function () {});
      connectWs(activeEmpId);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
