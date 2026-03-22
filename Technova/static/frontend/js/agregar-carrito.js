// Interceptar formularios de agregar al carrito para mostrar mensaje en lugar de redirigir
document.addEventListener('DOMContentLoaded', function() {
    if (!usuarioId) {
        return; // Si no hay usuario, dejar que el formulario funcione normalmente
    }
    
    // Interceptar todos los formularios de agregar al carrito
    const formulariosCarrito = document.querySelectorAll('form[action*="/carrito/agregar/"]');
    
    formulariosCarrito.forEach(form => {
        form.addEventListener('submit', async function(e) {
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
                if (typeof Swal !== 'undefined') {
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
                
                // Mostrar mensaje de éxito
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: '¡Agregado al carrito!',
                        text: nombreProducto,
                        confirmButtonColor: '#00cc44',
                        timer: 2000,
                        showConfirmButton: false,
                        toast: true,
                        position: 'top-end'
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
                
                if (typeof Swal !== 'undefined') {
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

