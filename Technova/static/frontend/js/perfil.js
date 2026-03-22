document.addEventListener("DOMContentLoaded", () => {
  const email = localStorage.getItem("email_usuario");

  if (!email) {
    
    window.location.href = "iniciosesion.html";
  } else {
    document.getElementById("email_usuario_perfil").innerHTML = email;

  
    document.getElementById("cerrar-sesion").addEventListener("click", (e) => {
      e.preventDefault();

      localStorage.removeItem("email_usuario");

      window.location.href = "iniciosesion.html";
    });
  }
});

