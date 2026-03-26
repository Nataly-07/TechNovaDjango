/**
 * Alertas inline para carrito - Versión de emergencia
 * Se activa inmediatamente al hacer clic en cualquier botón de carrito
 */

console.log('🚨 carrito-inline.js cargado - Versión de emergencia');

// Si SweetAlert/CarritoAlerts ya están disponibles, o si existe otro handler del carrito,
// esta versión de emergencia solo genera alertas duplicadas.
window.TECHNOVA_CARRITO_INLINE_DISABLED =
  !!window.TECHNOVA_CARRITO_BACKEND_INTERCEPT ||
  !!window.TECHNOVA_CARRITO_MEJORADO_ACTIVE ||
  (typeof window.CarritoAlerts !== 'undefined') ||
  (typeof window.Swal !== 'undefined');

// Función global para mostrar alerta
window.mostrarAlertaCarrito = function(nombreProducto) {
    console.log('🎉 ALERTA INLINE ACTIVADA para:', nombreProducto);
    
    // Crear elemento de alerta flotante
    const alerta = document.createElement('div');
    alerta.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
        z-index: 999999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 600;
        animation: slideInRight 0.5s ease-out;
        max-width: 350px;
    `;
    
    alerta.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 40px; height: 40px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <i class="bx bx-check" style="font-size: 24px;"></i>
            </div>
            <div>
                <div style="font-size: 14px; opacity: 0.9;">¡Agregado al carrito!</div>
                <div style="font-size: 16px; font-weight: 700;">${nombreProducto}</div>
            </div>
        </div>
    `;
    
    // Agregar animación CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    
    if (!document.querySelector('style[data-carrito-animations]')) {
        style.setAttribute('data-carrito-animations', 'true');
        document.head.appendChild(style);
    }
    
    document.body.appendChild(alerta);
    
    // Auto-eliminar después de 3 segundos
    setTimeout(() => {
        alerta.style.animation = 'slideOutRight 0.5s ease-out';
        setTimeout(() => {
            if (alerta.parentNode) {
                alerta.parentNode.removeChild(alerta);
            }
        }, 500);
    }, 3000);
};

// Interceptar todos los clics en botones
document.addEventListener('click', function(e) {
    if (window.TECHNOVA_CARRITO_INLINE_DISABLED) return;
    // Si el flujo oficial del carrito backend está activo, no intervenir (evita doble alerta)
    if (window.TECHNOVA_CARRITO_BACKEND_INTERCEPT) return;

    // Limitar a botones explícitos de carrito (evita disparar por cualquier botón del sitio)
    const boton = e.target.closest('.carrito-btn, [data-carrito-alert]');
    
    if (boton) {
        console.log('🖱️ Clic detectado en:', boton);
        
        // Buscar el nombre del producto
        let nombreProducto = 'Producto';
        
        // Intentar obtener desde el contenedor más cercano
        const contenedor = boton.closest('.producto, .producto-card, .card, .item');
        if (contenedor) {
            const h3 = contenedor.querySelector('h3, h2, .titulo, .title, .name');
            if (h3) {
                nombreProducto = h3.textContent.trim();
            }
        }
        
        // Mostrar alerta inmediatamente (solo modo emergencia)
        mostrarAlertaCarrito(nombreProducto);
        
        console.log('✅ Alerta inline mostrada para:', nombreProducto);
    }
});

// También interceptar formularios
document.addEventListener('submit', function(e) {
    if (window.TECHNOVA_CARRITO_INLINE_DISABLED) return;
    // Si el flujo oficial del carrito backend está activo, no intervenir (evita doble alerta)
    if (window.TECHNOVA_CARRITO_BACKEND_INTERCEPT) return;

    const form = e.target;
    const action = form.getAttribute('action');
    
    if (action && action.includes('/carrito/agregar/')) {
        console.log('📋 Formulario de carrito detectado');
        
        // Obtener nombre del producto
        let nombreProducto = 'Producto';
        const contenedor = form.closest('.producto, .producto-card, .card, .item');
        if (contenedor) {
            const h3 = contenedor.querySelector('h3, h2, .titulo, .title, .name');
            if (h3) {
                nombreProducto = h3.textContent.trim();
            }
        }
        
        // Mostrar alerta (solo modo emergencia)
        mostrarAlertaCarrito(nombreProducto);
    }
});

console.log('✅ carrito-inline.js inicializado completamente');
