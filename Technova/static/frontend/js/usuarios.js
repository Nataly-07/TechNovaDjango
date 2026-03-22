let usuarios = JSON.parse(localStorage.getItem("usuarios")) || [
  { nombre: "Juan Pérez", correo: "juan.perez@technova.com", imagen: "./images.png", rol: "cliente" },
  { nombre: "María López", correo: "maria.lopez@technova.com", imagen: "./images.png", rol: "admin" },
  { nombre: "Carlos Rivera", correo: "carlos.rivera@technova.com", imagen: "./images.png", rol: "empleado" }
];

function guardarUsuarios() {
  localStorage.setItem("usuarios", JSON.stringify(usuarios));
}

function mostrarUsuarios() {
  const tabla = document.getElementById("usuarios-body");
  tabla.innerHTML = "";

  usuarios.forEach((user, index) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td><img src="${user.imagen}" class="usuario-img" alt="${user.nombre}"></td>
      <td>${user.nombre}</td>
      <td>${user.correo}</td>
      <td><span class="rol-tag ${user.rol.toLowerCase()}">${user.rol}</span></td>

      <td>
        <button class="accion editar" data-index="${index}">✏️ Editar</button>
        <button class="accion eliminar" data-index="${index}">🗑️ Eliminar</button>
      </td>
    `;
    tabla.appendChild(fila);
  });

  document.getElementById("contadorUsuarios").textContent = `Total de usuarios: ${usuarios.length}`;
  activarEventos();
}

function activarEventos() {
  document.querySelectorAll(".accion.editar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = btn.dataset.index;
      const usuario = usuarios[index];

      Swal.fire({
        title: "Editar Usuario",
        html: `
          <input id="nombreNuevo" class="swal2-input" value="${usuario.nombre}">
          <input id="correoNuevo" class="swal2-input" type="email" value="${usuario.correo}">
          <select id="rolNuevo" class="swal2-input">
            <option value="cliente" ${usuario.rol === "cliente" ? "selected" : ""}>Cliente</option>
            <option value="admin" ${usuario.rol === "admin" ? "selected" : ""}>Administrador</option>
            <option value="empleado" ${usuario.rol === "empleado" ? "selected" : ""}>Empleado</option>
          </select>
        `,
        showCancelButton: true,
        confirmButtonText: "Guardar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#00cc44",
        preConfirm: () => {
          const nombre = document.getElementById("nombreNuevo").value.trim();
          const correo = document.getElementById("correoNuevo").value.trim();
          const rol = document.getElementById("rolNuevo").value;
          if (!nombre || !correo) {
            Swal.showValidationMessage("Completa todos los campos");
            return false;
          }
          return { nombre, correo, rol };
        }
      }).then((result) => {
        if (result.isConfirmed) {
         usuarios[index].nombre = result.value.nombre;
usuarios[index].correo = result.value.correo;
usuarios[index].rol = result.value.rol;


          guardarUsuarios();
          mostrarUsuarios();

          Swal.fire({
            icon: "success",
            title: "Actualizado",
            showConfirmButton: false,
            timer: 1500
          });
        }
      });
    });
  });

  document.querySelectorAll(".accion.eliminar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = btn.dataset.index;

      Swal.fire({
        title: "¿Eliminar usuario?",
        text: "Esta acción no se puede deshacer.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, eliminar",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#d33"
      }).then((result) => {
        if (result.isConfirmed) {
          usuarios.splice(index, 1);
          guardarUsuarios();
          mostrarUsuarios();

          Swal.fire({
            icon: "success",
            title: "Usuario eliminado",
            showConfirmButton: false,
            timer: 1200
          });
        }
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", mostrarUsuarios);


document.getElementById("nuevoUsuarioForm").addEventListener("submit", (e) => {
  e.preventDefault();

  const nombre = document.getElementById("nuevoNombre").value.trim();
  const correo = document.getElementById("nuevoCorreo").value.trim();
  let imagen = document.getElementById("nuevaImagen").value.trim();
  const rol = document.getElementById("nuevoRol").value;

  const duplicado = usuarios.some((u) => u.correo.toLowerCase() === correo.toLowerCase());

  if (!nombre || !correo) {
    Swal.fire({
      icon: "warning",
      title: "Campos incompletos",
      text: "Por favor ingresa al menos nombre y correo.",
      confirmButtonColor: "#ff967f"
    });
    return;
  }

  if (duplicado) {
    Swal.fire({
      icon: "error",
      title: "Correo duplicado",
      text: "Ya existe un usuario con ese correo.",
      confirmButtonColor: "#d33"
    });
    return;
  }

  if (!imagen) {
    imagen = "./images.png";
  }

  usuarios.push({ nombre, correo, imagen, rol });
  guardarUsuarios();
  mostrarUsuarios();

  Swal.fire({
    icon: "success",
    title: "Usuario agregado",
    showConfirmButton: false,
    timer: 1500
  });

  e.target.reset();
});


document.getElementById("contadorUsuarios").textContent = `Total de usuarios: ${usuarios.length}`;

document.getElementById("buscadorUsuarios").addEventListener("input", function () {
  const texto = this.value.toLowerCase();
  const filas = document.querySelectorAll("#usuarios-body tr");

  filas.forEach((fila) => {
    const nombre = fila.children[1].textContent.toLowerCase();
    const correo = fila.children[2].textContent.toLowerCase();
    fila.style.display = nombre.includes(texto) || correo.includes(texto) ? "" : "none";
  });
});


document.getElementById("filtroRol").addEventListener("change", function () {
  const filtro = this.value;
  const filas = document.querySelectorAll("#usuarios-body tr");

  filas.forEach((fila) => {
    const rol = fila.children[3].textContent.trim().toLowerCase();
    fila.style.display = filtro === "todos" || rol === filtro ? "" : "none";
  });
});


