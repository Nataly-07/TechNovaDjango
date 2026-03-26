let carrito = JSON.parse(localStorage.getItem("carrito")) || [];

function guardarCarrito() {
  localStorage.setItem("carrito", JSON.stringify(carrito));
}

function actualizarCarrito() {
  const lista = document.querySelector("#lista-carrito");
  const totalElement = document.querySelector("#total");
  
  // Verificar que los elementos existan antes de usarlos
  if (!lista || !totalElement) {
    return; // Salir si los elementos no existen en esta página
  }
  
  lista.innerHTML = "";

  let total = 0;

  carrito.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.nombre} - $${item.precio.toLocaleString()}`;
    li.classList.add("agregado"); // animación CSS
    lista.appendChild(li);
    total += item.precio;
  });

  totalElement.textContent = total.toLocaleString();
  guardarCarrito();
}

document.addEventListener("DOMContentLoaded", () => {
  // Verificar si hay un usuario autenticado (si existe la variable usuarioId)
  const tieneUsuario = typeof usuarioId !== 'undefined' && usuarioId !== null;
  
  document.querySelectorAll(".carrito-btn").forEach((boton) => {
    // Si el botón es un enlace a /login o tiene href que incluye /login, es para usuarios no autenticados
    const href = boton.getAttribute('href') || boton.href || '';
    const esBotonNoAutenticado = href.includes('/login') || href === '/login';
    
    // Si el botón está dentro de un formulario con action que contiene "/carrito/agregar/", 
    // significa que usa el sistema de backend (agregar-carrito.js lo manejará)
    const formulario = boton.closest('form');
    const estaEnFormularioBackend = formulario !== null && 
                                     (formulario.getAttribute('action') || '').includes('/carrito/agregar/');
    
    // Si el botón está dentro de un formulario del backend, no interferir
    if (estaEnFormularioBackend) {
      return; // No hacer nada, dejar que agregar-carrito.js maneje el clic
    }
    
    // Solo agregar funcionalidad de carrito si hay usuario autenticado y no es botón de login
    if (!tieneUsuario || esBotonNoAutenticado) {
      return; // No hacer nada, dejar que el script de index.html maneje el clic
    }
    
    boton.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const producto = boton.closest(".producto");
      if (!producto) return;
      
      const nombreElement = producto.querySelector("h3");
      if (!nombreElement) return;
      
      const nombre = nombreElement.textContent.trim();

      const precioElement = producto.querySelector(".precio-descuento");
      if (!precioElement) return;
      
      let precio = precioElement.textContent.trim().replace("$", "");
      precio = parseInt(precio.split(".").join(""), 10);

      carrito.push({ nombre, precio });
      guardarCarrito();
      actualizarCarrito();

      // confirmación visual mejorada
      if (typeof CarritoAlerts !== 'undefined') {
        CarritoAlerts.success(nombre);
      } else if (typeof Swal !== 'undefined') {
        Swal.fire({
          icon: false,
          html: `
            <div style="text-align: center; padding: 20px 0;">
              <div style="margin-bottom: 15px;">
                <div style="width: 80px; height: 80px; margin: 0 auto; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; animation: scaleIn 0.5s ease-out;">
                  <i class="bx bx-check" style="font-size: 40px; color: white;"></i>
                </div>
              </div>
              <h3 style="color: #0f172a; font-size: 1.5rem; font-weight: 700; margin-bottom: 8px;">¡Agregado al carrito!</h3>
              <p style="color: #64748b; font-size: 1rem; margin: 0; font-weight: 500;">${nombre}</p>
              <div style="margin-top: 15px; display: flex; justify-content: center; gap: 8px;">
                <span style="background: #f1f5f9; color: #334155; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                  <i class="bx bx-cart" style="margin-right: 4px;"></i>Carrito actualizado
                </span>
              </div>
            </div>
          `,
          showConfirmButton: false,
          timer: 2000,
          customClass: {
            popup: 'custom-swal-popup'
          },
          backdrop: false,
          showClass: {
            popup: 'animate__animated animate__fadeInRight'
          },
          hideClass: {
            popup: 'animate__animated animate__fadeOutRight'
          }
        });
      }
    });
  });

  // Botón para vaciar el carrito
  const vaciarBtn = document.getElementById("vaciarCarritoBtn");
  if (vaciarBtn) {
    vaciarBtn.addEventListener("click", () => {
      Swal.fire({
        title: "¿Vaciar el carrito?",
        text: "Esta acción eliminará todos los productos",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#888",
        confirmButtonText: "Sí, vaciar",
      }).then((result) => {
        if (result.isConfirmed) {
          carrito = [];
          actualizarCarrito();

          Swal.fire({
            icon: "success",
            title: "Carrito vacío",
            showConfirmButton: false,
            timer: 1000,
          });
        }
      });
    });
  }

  actualizarCarrito();
});

