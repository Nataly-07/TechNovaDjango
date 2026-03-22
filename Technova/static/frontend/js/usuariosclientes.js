const body = document.getElementById("clientesBody");
const buscador = document.getElementById("buscarCliente");
const contador = document.getElementById("contadorClientes");


let usuarios = JSON.parse(localStorage.getItem("usuariosTech"));

// Cargar usuarios de ejemplo si no hay
if (!usuarios || usuarios.length === 0) {
  usuarios = [
    {
      nombre: "Laura Rodríguez",
      correo: "laura@gmail.com",
      imagen: "imagenes/perfil1.png",
      rol: "cliente"
    },
    {
      nombre: "Andrés Pineda",
      correo: "andres@correo.com",
      imagen: "imagenes/perfil2.png",
      rol: "cliente"
    },
    {
      nombre: "Camila Ruiz",
      correo: "camiruiz@correo.com",
      imagen: "imagenes/perfil3.png",
      rol: "cliente"
    },
    {
      nombre: "Mauricio Gómez",
      correo: "mauro@correo.com",
      imagen: "imagenes/perfil4.png",
      rol: "empleado"
    },
    {
      nombre: "Julián Duarte",
      correo: "admin@technova.com",
      imagen: "imagenes/perfil5.png",
      rol: "admin"
    }
  ];
  localStorage.setItem("usuariosTech", JSON.stringify(usuarios));
}

function renderClientes(filtro = "") {
  const clientes = usuarios.filter(u =>
    u.rol === "cliente" &&
    u.nombre.toLowerCase().includes(filtro.toLowerCase())
  );

  body.innerHTML = "";
  clientes.forEach(cliente => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td><img src="${cliente.imagen || 'imagenes/default.png'}" class="usuario-img" alt="${cliente.nombre}"></td>
      <td>${cliente.nombre}</td>
      <td>${cliente.correo}</td>
      <td><span class="rol-tag cliente">Cliente</span></td>
    `;
    body.appendChild(fila);
  });
  contador.textContent = `Total de clientes: ${clientes.length}`;

}

buscador.addEventListener("input", () => renderClientes(buscador.value));
renderClientes();
