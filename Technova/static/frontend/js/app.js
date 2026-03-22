console.log("📦 Script cargado correctamente");

const toggle = document.querySelector(".toggle")
const menuDashboard = document.querySelector(".menu-dashboard")
const iconoMenu = toggle ? toggle.querySelector("i") : null
const enlacesMenu = document.querySelectorAll(".enlace")

if (toggle && menuDashboard && iconoMenu) {
    toggle.addEventListener("click", () => {
        menuDashboard.classList.toggle("open")

        if(iconoMenu.classList.contains("bx-menu")){
            iconoMenu.classList.replace("bx-menu", "bx-x")
        } else {
            iconoMenu.classList.replace("bx-x", "bx-menu")
        }
    })
}

enlacesMenu.forEach(enlace => {
    enlace.addEventListener("click", () => {
        if (menuDashboard) {
            menuDashboard.classList.add("open")
        }
        if (iconoMenu && iconoMenu.classList.contains("bx-menu")) {
            iconoMenu.classList.replace("bx-menu", "bx-x")
        }
    })
});

// Gráfica de ejemplo
const ctx = document.getElementById("ventasChart");

if (ctx && typeof Chart !== 'undefined') {
    new Chart(ctx, {
    type: "bar",
    data: {
        labels: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre' ],
        datasets: [{
            label: 'Valor de Ventas',
            data: [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000],
            backgroundColor:'rgba(255, 150, 127, 0.5)', 
            borderColor:'#ff967f',
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'top'
            },
            title: {
                display: true,
                text: 'Valor de Ventas Mensuales'
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
    });
}



document.addEventListener("DOMContentLoaded", cargarTabla);


let inventario = JSON.parse(localStorage.getItem("inventario")) || [
  {
    codigo: "CEL-101",
    nombre: "iPhone 14",
    imagen: "imagenes/iphone.png",
    compra: 2500000,
    venta: 3200000,
    unidades: 12
  },
  {
    codigo: "LAP-202",
    nombre: "HP Pavilion x360",
    imagen: "imagenes/hp.png",
    compra: 2800000,
    venta: 3500000,
    unidades: 5
  }
];

function guardarInventario() {
  localStorage.setItem("inventario", JSON.stringify(inventario));
}

function cargarTabla() {
  const tbody = document.querySelector(".table-inventario tbody");
  if (!tbody) return; // Si no existe el elemento, salir de la función
  tbody.innerHTML = "";

  inventario.forEach((item, i) => {
    const fila = document.createElement("tr");
    fila.innerHTML = `
      <td>${item.codigo}</td>
      <td>${item.nombre}</td>
      <td><img src="${item.imagen}" class="img-inventario" /></td>
      <td>$${item.compra.toLocaleString()}</td>
      <td>$${item.venta.toLocaleString()}</td>
      <td>${item.unidades}</td>
      <td><span class="estado ${item.unidades > 0 ? "disponible" : "agotado"}">
        ${item.unidades > 0 ? "Disponible" : "Agotado"}</span>
      </td>
      <td>
        <button class="accion editar" data-index="${i}">✏️</button>
        <button class="accion eliminar" data-index="${i}">🗑️</button>
      </td>
    `;
    tbody.appendChild(fila);
  });

  activarBotones();
}

function activarBotones() {
  document.querySelectorAll(".editar").forEach((btn) => {
    btn.onclick = () => {
      const i = btn.dataset.index;
      const item = inventario[i];

      Swal.fire({
        title: "Editar Producto",
        html: `
          <input id="codigo" class="swal2-input" placeholder="Código" value="${item.codigo}">
          <input id="nombre" class="swal2-input" placeholder="Nombre" value="${item.nombre}">
          <input id="imagen" class="swal2-input" placeholder="URL Imagen" value="${item.imagen}">
          <input id="compra" class="swal2-input" type="number" placeholder="Precio compra" value="${item.compra}">
          <input id="venta" class="swal2-input" type="number" placeholder="Precio venta" value="${item.venta}">
          <input id="unidades" class="swal2-input" type="number" placeholder="Unidades" value="${item.unidades}">
        `,
        showCancelButton: true,
        confirmButtonText: "Guardar",
        preConfirm: () => {
          const codigo = document.getElementById("codigo").value.trim();
          const nombre = document.getElementById("nombre").value.trim();
          const imagen = document.getElementById("imagen").value.trim();
          const compra = parseInt(document.getElementById("compra").value);
          const venta = parseInt(document.getElementById("venta").value);
          const unidades = parseInt(document.getElementById("unidades").value);

          if (!codigo || !nombre || !imagen || isNaN(compra) || isNaN(venta) || isNaN(unidades)) {
            Swal.showValidationMessage("Por favor completa todos los campos correctamente");
            return false;
          }

          return { codigo, nombre, imagen, compra, venta, unidades };
        }
      }).then((res) => {
        if (res.isConfirmed) {
          inventario[i] = res.value;
          guardarInventario();
          cargarTabla();
          Swal.fire("Actualizado", "El producto ha sido editado correctamente", "success");
        }
      });
    };
  });

  document.querySelectorAll(".eliminar").forEach((btn) => {
    btn.onclick = () => {
      const i = btn.dataset.index;
      Swal.fire({
        title: "¿Eliminar producto?",
        text: "Esta acción no se puede deshacer.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Eliminar",
        confirmButtonColor: "#d33"
      }).then((result) => {
        if (result.isConfirmed) {
          inventario.splice(i, 1);
          guardarInventario();
          cargarTabla();
          Swal.fire("Eliminado", "El producto fue eliminado del inventario", "success");
        }
      });
    };
  });
}

document.addEventListener("DOMContentLoaded", cargarTabla);
