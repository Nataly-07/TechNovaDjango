document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("iniciosesion");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    // Validación simple en cliente, pero se permite el submit al backend
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    function mostrarMsg(texto, tipo = "error") {
      const msgFlotante = document.getElementById("msg-flotante");
      if (!msgFlotante) return;
      msgFlotante.textContent = texto;
      msgFlotante.classList.remove("oculto");
      msgFlotante.classList.remove("error", "success");
      msgFlotante.classList.add(tipo);
      msgFlotante.classList.add("active");
      setTimeout(() => {
        msgFlotante.classList.remove("active");
        setTimeout(() => {
          msgFlotante.classList.add("oculto");
        }, 500);
      }, 3000);
    }

    if (email === '' || password === '') {
      e.preventDefault();
      mostrarMsg("Todos los campos son obligatorios.", "error");
      return;
    }

    if (password.length < 6) {
      e.preventDefault();
      mostrarMsg("La contraseña debe tener al menos 6 dígitos.", "error");
      return;
    }

    // No cancelar el submit: que Laravel procese el login y redireccione según rol
  });
});

