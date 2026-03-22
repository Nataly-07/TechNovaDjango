const tbody = document.getElementById("tablaEmpleados");
let inventario = JSON.parse(localStorage.getItem("inventarioTech")) || [];

// Mostrar productos en vista solo lectura
function renderEmpleadoInventario() {
  tbody.innerHTML = "";
  inventario.forEach((item) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td class="nombre">${item.nombre}</td>
      <td>$${Number(item.precioVenta).toLocaleString()}</td>
      <td>${item.unidades}</td>
      <td>
        <span class="estado ${item.unidades > 0 ? 'disponible' : 'agotado'}">
          ${item.unidades > 0 ? "Disponible" : "Agotado"}
        </span>
      </td>
    `;
    tbody.appendChild(fila);
  });
}

renderEmpleadoInventario();
