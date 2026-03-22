(function () {
  function clear() {
    localStorage.removeItem("technova_access");
    localStorage.removeItem("technova_refresh");
    localStorage.removeItem("technova_usuario_id");
    localStorage.removeItem("technova_usuario_rol");
  }

  function csrfToken() {
    var el = document.querySelector("input[name=csrfmiddlewaretoken]");
    if (el && el.value) return el.value;
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  window.TechnovaAuth = {
    isLoggedIn() {
      return !!localStorage.getItem("technova_access");
    },
    getUsuarioId() {
      return localStorage.getItem("technova_usuario_id");
    },
    getRol() {
      return localStorage.getItem("technova_usuario_rol");
    },
    logout() {
      clear();
      var token = csrfToken();
      if (token) {
        var form = document.createElement("form");
        form.method = "POST";
        form.action = "/logout/";
        var input = document.createElement("input");
        input.type = "hidden";
        input.name = "csrfmiddlewaretoken";
        input.value = token;
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
        return;
      }
      window.location.href = "/login/";
    },
    setSessionFromLogin(data) {
      if (data.access) localStorage.setItem("technova_access", data.access);
      if (data.refresh) localStorage.setItem("technova_refresh", data.refresh);
      if (data.usuario && data.usuario.id != null) {
        localStorage.setItem("technova_usuario_id", String(data.usuario.id));
        if (data.usuario.rol) localStorage.setItem("technova_usuario_rol", data.usuario.rol);
      }
    },
    clear,
  };
})();
