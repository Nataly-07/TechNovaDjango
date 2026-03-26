/**
 * Sistema mejorado de alertas para el carrito - Versión Simplificada
 * Intercepta directamente los clics en botones de carrito
 */

console.log('🚀 carrito-mejorado.js cargado');
window.TECHNOVA_CARRITO_MEJORADO_ACTIVE = true;

// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Si el flujo oficial del carrito backend está activo, no intervenir (evita doble alerta)
    if (window.TECHNOVA_CARRITO_BACKEND_INTERCEPT) {
        console.log('🛑 carrito-mejorado.js desactivado (backend intercept activo)');
        return;
    }

    console.log('📋 DOM listo, buscando botones de carrito...');
    
    // Buscar todos los botones que puedan ser de carrito
    const botonesCarrito = document.querySelectorAll('button[type="submit"], .carrito-btn');
    console.log('🔍 Botones encontrados:', botonesCarrito.length);
    
    botonesCarrito.forEach((boton, index) => {
        const form = boton.closest('form');
        const esFormularioCarrito = form && form.getAttribute('action') && form.getAttribute('action').includes('/carrito/agregar/');
        
        if (esFormularioCarrito) {
            console.log(`🎯 Botón ${index + 1} es de carrito:`, form.getAttribute('action'));
            
            // Reemplazar el evento submit
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('🛒 Formulario de carrito interceptado');
                
                // Obtener nombre del producto
                const nombreProducto = obtenerNombreProducto(form);
                console.log('📦 Nombre del producto:', nombreProducto);
                
                // Mostrar alerta mejorada inmediatamente
                mostrarAlertaExito(nombreProducto);
                
                // Enviar el formulario normalmente después de un breve delay
                setTimeout(() => {
                    form.submit();
                }, 1000);
                
                return false;
            });
        }
    });
});

function obtenerNombreProducto(form) {
    // Intentar obtener el nombre del producto desde varios lugares
    const contenedor = form.closest('.producto, .producto-card, .card');
    
    if (contenedor) {
        const h3 = contenedor.querySelector('h3');
        if (h3) return h3.textContent.trim();
        
        const h2 = contenedor.querySelector('h2');
        if (h2) return h2.textContent.trim();
        
        const titulo = contenedor.querySelector('.titulo, .title, .name');
        if (titulo) return titulo.textContent.trim();
    }
    
    return 'Producto';
}

function mostrarAlertaExito(nombreProducto) {
    console.log('🎉 Mostrando alerta de éxito para:', nombreProducto);
    
    // Verificar si SweetAlert2 está disponible
    if (typeof Swal !== 'undefined') {
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
                    <p style="color: #64748b; font-size: 1rem; margin: 0; font-weight: 500;">${nombreProducto}</p>
                    <div style="margin-top: 15px; display: flex; justify-content: center; gap: 8px;">
                        <span style="background: #f1f5f9; color: #334155; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                            <i class="bx bx-cart" style="margin-right: 4px;"></i>Carrito actualizado
                        </span>
                    </div>
                </div>
            `,
            showConfirmButton: false,
            timer: 2500,
            toast: true,
            position: 'top-end',
            customClass: {
                popup: 'custom-swal-popup',
                container: 'custom-swal-container'
            },
            backdrop: false,
            showClass: {
                popup: 'animate__animated animate__fadeInRight'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutRight'
            }
        });
    } else {
        // Fallback a alerta simple
        alert(`¡${nombreProducto} agregado al carrito! 🛒`);
    }
}

// También interceptar clics directos en botones
document.addEventListener('click', function(e) {
    // Si el flujo oficial del carrito backend está activo, no intervenir (evita doble alerta)
    if (window.TECHNOVA_CARRITO_BACKEND_INTERCEPT) return;

    const boton = e.target.closest('button[type="submit"], .carrito-btn');
    
    if (boton) {
        const form = boton.closest('form');
        const esFormularioCarrito = form && form.getAttribute('action') && form.getAttribute('action').includes('/carrito/agregar/');
        
        if (esFormularioCarrito) {
            console.log('🖱️ Clic directo en botón de carrito interceptado');
            
            // Obtener nombre del producto
            const nombreProducto = obtenerNombreProducto(form);
            
            // Mostrar alerta
            mostrarAlertaExito(nombreProducto);
        }
    }
});

console.log('✅ carrito-mejorado.js inicializado');
