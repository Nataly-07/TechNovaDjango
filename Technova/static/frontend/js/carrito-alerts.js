/**
 * Sistema de alertas mejoradas para el carrito de compras
 * Proporciona una experiencia visual consistente y moderna
 */

console.log('🎨 CarritoAlerts.js cargado correctamente');

window.CarritoAlerts = {
    /**
     * Muestra una alerta de éxito cuando un producto se agrega al carrito
     * @param {string} nombreProducto - Nombre del producto agregado
     * @param {Object} options - Opciones adicionales
     */
    success: function(nombreProducto, options = {}) {
        console.log('🎯 CarritoAlerts.success llamado con:', nombreProducto);
        const defaults = {
            timer: 2300,
            showConfirmButton: false,
            toast: true,
            position: 'top-end'
        };
        
        const config = { ...defaults, ...options };
        
        return Swal.fire({
            icon: false,
            html: `
                <div class="tn-cart-toast">
                  <div class="tn-cart-toast__iconWrap" aria-hidden="true">
                    <i class="bx bx-check tn-cart-toast__icon"></i>
                  </div>
                  <div class="tn-cart-toast__body">
                    <div class="tn-cart-toast__title">¡Agregado al carrito!</div>
                    <div class="tn-cart-toast__product">${nombreProducto}</div>
                    <div class="tn-cart-toast__meta">
                      <span class="tn-cart-toast__chip">
                        <i class="bx bx-cart"></i>
                        Carrito actualizado
                      </span>
                    </div>
                  </div>
                </div>
            `,
            showConfirmButton: config.showConfirmButton,
            timer: config.timer,
            toast: config.toast,
            position: config.position,
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
    },

    /**
     * Muestra una alerta de éxito con opción de ir al carrito
     * @param {string} message - Mensaje personalizado
     * @param {string} cartUrl - URL del carrito
     */
    successWithCartOption: function(message, cartUrl) {
        return Swal.fire({
            icon: false,
            html: `
                <div style="text-align: center; padding: 30px 20px;">
                    <div style="margin-bottom: 20px;">
                        <div style="width: 100px; height: 100px; margin: 0 auto; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; animation: scaleIn 0.5s ease-out;">
                            <i class="bx bx-check" style="font-size: 50px; color: white;"></i>
                        </div>
                    </div>
                    <h3 style="color: #0f172a; font-size: 1.8rem; font-weight: 700; margin-bottom: 12px;">¡Agregado al carrito!</h3>
                    <p style="color: #64748b; font-size: 1.1rem; margin: 0 0 20px 0; font-weight: 500;">${message || "Tu producto ya está en el carrito."}</p>
                    <div style="margin-bottom: 25px; display: flex; justify-content: center; gap: 10px;">
                        <span style="background: #f1f5f9; color: #334155; padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                            <i class="bx bx-cart" style="margin-right: 6px;"></i>Carrito actualizado
                        </span>
                        <span style="background: #dcfce7; color: #15803d; padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                            <i class="bx bx-check-circle" style="margin-right: 6px;"></i>Disponible
                        </span>
                    </div>
                </div>
            `,
            showCancelButton: true,
            showConfirmButton: true,
            confirmButtonText: '<i class="bx bx-shopping-bag" style="margin-right: 8px;"></i>Ir al carrito',
            cancelButtonText: '<i class="bx bx-arrow-back" style="margin-right: 8px;"></i>Seguir comprando',
            confirmButtonColor: '#10b981',
            cancelButtonColor: '#64748b',
            customClass: {
                popup: 'custom-swal-popup',
                confirmButton: 'custom-swal-confirm',
                cancelButton: 'custom-swal-cancel'
            },
            backdrop: 'rgba(0, 0, 0, 0.4)',
            showClass: {
                popup: 'animate__animated animate__zoomIn'
            },
            hideClass: {
                popup: 'animate__animated animate__zoomOut'
            }
        }).then(function (result) {
            if (result.isConfirmed && cartUrl) {
                window.location.href = cartUrl;
            }
            return result;
        });
    },

    /**
     * Muestra una alerta de error
     * @param {string} message - Mensaje de error
     */
    error: function(message) {
        return Swal.fire({
            icon: false,
            html: `
                <div style="text-align: center; padding: 20px 0;">
                    <div style="margin-bottom: 15px;">
                        <div style="width: 80px; height: 80px; margin: 0 auto; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; animation: scaleIn 0.5s ease-out;">
                            <i class="bx bx-x" style="font-size: 40px; color: white;"></i>
                        </div>
                    </div>
                    <h3 style="color: #0f172a; font-size: 1.5rem; font-weight: 700; margin-bottom: 8px;">¡Error!</h3>
                    <p style="color: #64748b; font-size: 1rem; margin: 0; font-weight: 500;">${message}</p>
                </div>
            `,
            confirmButtonText: 'Entendido',
            confirmButtonColor: '#ef4444',
            customClass: {
                popup: 'custom-swal-popup',
                confirmButton: 'custom-swal-error'
            },
            backdrop: 'rgba(0, 0, 0, 0.4)',
            showClass: {
                popup: 'animate__animated animate__zoomIn'
            },
            hideClass: {
                popup: 'animate__animated animate__zoomOut'
            }
        });
    },

    /**
     * Muestra una alerta de producto agotado
     * @param {string} nombreProducto - Nombre del producto agotado
     */
    outOfStock: function(nombreProducto) {
        return Swal.fire({
            icon: false,
            html: `
                <div style="text-align: center; padding: 20px 0;">
                    <div style="margin-bottom: 15px;">
                        <div style="width: 80px; height: 80px; margin: 0 auto; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; animation: scaleIn 0.5s ease-out;">
                            <i class="bx bx-package" style="font-size: 40px; color: white;"></i>
                        </div>
                    </div>
                    <h3 style="color: #0f172a; font-size: 1.5rem; font-weight: 700; margin-bottom: 8px;">¡Producto agotado!</h3>
                    <p style="color: #64748b; font-size: 1rem; margin: 0; font-weight: 500;">${nombreProducto}</p>
                    <div style="margin-top: 15px;">
                        <span style="background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                            <i class="bx bx-time-five" style="margin-right: 4px;"></i>No disponible
                        </span>
                    </div>
                </div>
            `,
            confirmButtonText: 'Entendido',
            confirmButtonColor: '#f59e0b',
            customClass: {
                popup: 'custom-swal-popup',
                confirmButton: 'custom-swal-warning'
            },
            backdrop: 'rgba(0, 0, 0, 0.4)',
            showClass: {
                popup: 'animate__animated animate__zoomIn'
            },
            hideClass: {
                popup: 'animate__animated animate__zoomOut'
            }
        });
    }
};

// Estilos adicionales para botones de error y advertencia
const additionalStyles = `
.custom-swal-error {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
    transition: all 0.3s ease !important;
}

.custom-swal-error:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4) !important;
}

.custom-swal-warning {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3) !important;
    transition: all 0.3s ease !important;
}

.custom-swal-warning:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
}
`;

// Agregar estilos al documento
if (typeof document !== 'undefined') {
    const styleSheet = document.createElement('style');
    styleSheet.textContent = additionalStyles;
    document.head.appendChild(styleSheet);
}
