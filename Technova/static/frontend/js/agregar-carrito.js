// Interceptar formularios de agregar al carrito para mostrar mensaje en lugar de redirigir
// Señal global para desactivar scripts "de emergencia" que duplican alertas.
window.TECHNOVA_CARRITO_BACKEND_INTERCEPT = true;
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 agregar-carrito.js cargado correctamente');
    console.log('🔍 CarritoAlerts disponible:', typeof CarritoAlerts !== 'undefined');
    console.log('🔍 Swal disponible:', typeof Swal !== 'undefined');
    
    if (!usuarioId) {
        console.log('❌ No hay usuarioId, saliendo...');
        return; // Si no hay usuario, dejar que el formulario funcione normalmente
    }
    
    console.log('✅ usuarioId encontrado:', usuarioId);
    
    // Interceptar todos los formularios de agregar al carrito
    const formulariosCarrito = document.querySelectorAll('form[action*="/carrito/agregar/"]');
    console.log('🔍 Formularios de carrito encontrados:', formulariosCarrito.length);
    
    formulariosCarrito.forEach((form, index) => {
        console.log(`📋 Formulario ${index + 1}:`, form.getAttribute('action'));
        form.addEventListener('submit', async function(e) {
            console.log('🎯 Formulario de carrito submit interceptado');
            e.preventDefault();
            e.stopPropagation();
            
            // Obtener el productoId de la acción del formulario
            const action = this.getAttribute('action');
            const productoIdMatch = action.match(/\/carrito\/agregar\/(\d+)/);
            
            if (!productoIdMatch) {
                // Si no se puede obtener el ID, dejar que el formulario funcione normalmente
                return;
            }
            
            const productoId = parseInt(productoIdMatch[1]);
            const boton = this.querySelector('button[type="submit"]');
            const nombreProducto = this.closest('.producto')?.querySelector('h3')?.textContent?.trim() || 
                                  this.closest('.producto-card')?.querySelector('h3')?.textContent?.trim() || 
                                  'Producto';
            
            // Verificar si el botón está deshabilitado (producto agotado)
            if (boton && boton.disabled) {
                if (typeof CarritoAlerts !== 'undefined') {
                    CarritoAlerts.outOfStock(nombreProducto);
                } else if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Producto Agotado',
                        text: 'Este producto no está disponible en este momento.',
                        confirmButtonColor: '#e63946'
                    });
                } else {
                    alert('Este producto está agotado');
                }
                return;
            }
            
            // Deshabilitar el botón mientras se procesa
            if (boton) {
                boton.disabled = true;
                boton.style.opacity = '0.6';
                boton.style.cursor = 'not-allowed';
            }
            
            try {
                // Usar la API para agregar al carrito
                const formData = new URLSearchParams();
                formData.append('productoId', productoId);
                formData.append('cantidad', '1');
                
                const response = await fetch(`/api/carrito/${usuarioId}/agregar?productoId=${productoId}&cantidad=1`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    const errorMessage = errorData.message || 'Error al agregar al carrito';
                    throw new Error(errorMessage);
                }
                
                // Mostrar mensaje de éxito mejorado
                console.log('🎉 Producto agregado exitosamente, mostrando alerta...');
                console.log('🔍 CarritoAlerts disponible:', typeof CarritoAlerts !== 'undefined');
                console.log('🔍 Swal disponible:', typeof Swal !== 'undefined');
                
                if (typeof CarritoAlerts !== 'undefined') {
                    console.log('✅ Usando CarritoAlerts.success');
                    CarritoAlerts.success(nombreProducto);
                } else if (typeof Swal !== 'undefined') {
                    console.log('⚠️ CarritoAlerts no disponible, usando Swal fallback');
                    const swalAlert = Swal.fire({
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
                        showCancelButton: false,
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
                    alert('¡Producto agregado al carrito!');
                }
                
                // Actualizar el dropdown del carrito si está abierto
                if (typeof cargarCarrito === 'function') {
                    cargarCarrito();
                }
                
                // Recargar la página después de un breve delay para actualizar contadores
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
                
            } catch (error) {
                console.error('Error al agregar al carrito:', error);
                
                // Mostrar mensaje de error específico
                let mensajeError = 'No se pudo agregar el producto al carrito. Por favor, intenta nuevamente.';
                if (error.message && (error.message.includes('agotado') || error.message.includes('stock'))) {
                    mensajeError = error.message;
                }
                
                if (typeof CarritoAlerts !== 'undefined') {
                    CarritoAlerts.error(mensajeError);
                } else if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'No se pudo agregar',
                        text: mensajeError,
                        confirmButtonColor: '#e63946'
                    });
                } else {
                    alert(mensajeError);
                }
                
                // Rehabilitar el botón
                if (boton) {
                    boton.disabled = false;
                    boton.style.opacity = '1';
                    boton.style.cursor = 'pointer';
                }
            }
        });
    });
});

