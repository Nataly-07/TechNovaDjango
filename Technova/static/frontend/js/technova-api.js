/**
 * Cliente HTTP para la API Django (/api/v1). Respuestas: { ok, message, data }.
 */
(function () {
  const prefix = window.TECHNOVA_API_PREFIX || "/api/v1";

  function buildHeaders(method, body) {
    const h = {};
    const t = localStorage.getItem("technova_access");
    if (t) h.Authorization = "Bearer " + t;
    if (body !== undefined && method !== "GET" && method !== "DELETE") {
      h["Content-Type"] = "application/json";
    }
    return h;
  }

  async function apiJson(method, path, body) {
    const r = await fetch(prefix + path, {
      method,
      headers: buildHeaders(method, body),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.ok === false) {
      const msg = j.message || r.statusText || "Error de API";
      throw new Error(msg);
    }
    return j.data !== undefined ? j.data : j;
  }

  window.TechnovaApi = {
    prefix,
    get(path) {
      return apiJson("GET", path);
    },
    post(path, body) {
      return apiJson("POST", path, body);
    },
    patch(path, body) {
      return apiJson("PATCH", path, body);
    },
    delete(path) {
      return apiJson("DELETE", path);
    },
    put(path, body) {
      return apiJson("PUT", path, body);
    },
  };
})();
