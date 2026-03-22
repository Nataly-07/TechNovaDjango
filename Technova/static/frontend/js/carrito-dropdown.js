// Manejo del dropdown del carrito
document.addEventListener('DOMContentLoaded', function() {
    const carritoToggle = document.querySelector('.carrito-toggle-btn');
    const carritoDropdown = document.getElementById('carritoDropdown');
    const carritoContent = document.getElementById('carritoDropdownContent');
    
    if (!carritoToggle || !carritoDropdown || !usuarioId) {
        return; // Si no hay elementos necesarios, salir
    }
    
    // Toggle del dropdown
    carritoToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const isOpen = carritoDropdown.style.display === 'block';
        carritoDropdown.style.display = isOpen ? 'none' : 'block';
        
        if (!isOpen) {
            cargarCarrito();
        }
    });
    
    // Cerrar dropdown al hacer click fuera
    document.addEventListener('click', function(e) {
        if (!carritoDropdown.contains(e.target) && !carritoToggle.contains(e.target)) {
            carritoDropdown.style.display = 'none';
        }
    });
    
    // Cargar productos del carrito (función global para que otros scripts puedan usarla)
    window.cargarCarrito = async function() {
        try {
            const response = await fetch(`/api/carrito/${usuarioId}`);
            if (!response.ok) {
                throw new Error('Error al cargar el carrito');
            }
            
            const items = await response.json();
            mostrarCarrito(items);
        } catch (error) {
            console.error('Error al cargar carrito:', error);
            carritoContent.innerHTML = '<p style="text-align: center; padding: 20px; color: #e63946;">Error al cargar el carrito</p>';
        }
    };
    
    // Mostrar productos en el dropdown
    function mostrarCarrito(items) {
        if (!items || items.length === 0) {
            carritoContent.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">Tu carrito está vacío</p>';
            return;
        }
        
        // Separar productos disponibles de agotados
        const productosDisponibles = items.filter(item => (item.stock || 0) > 0);
        const productosAgotados = items.filter(item => (item.stock || 0) === 0);
        
        let html = '<ul style="list-style: none; padding: 0; margin: 0; max-height: 300px; overflow-y: auto;">';
        
        // Mostrar productos disponibles primero
        productosDisponibles.forEach(item => {
            const cantidad = item.cantidad || 1;
            const disabledStyle = cantidad <= 1 ? 'opacity: 0.5; cursor: not-allowed;' : '';
            html += `
                <li style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; background: #f9f9f9; margin-bottom: 8px; border-radius: 8px;">
                    <div style="flex: 1;">
                        <p style="margin: 0; font-weight: bold; font-size: 14px; color: #333;">${item.nombreProducto || 'Producto'}</p>
                        <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px;">
                            <span style="font-size: 12px; color: #666;">Cantidad:</span>
                            <div style="display: flex; align-items: center; gap: 5px; background: white; border: 1px solid #ddd; border-radius: 20px; padding: 2px 5px;">
                                <button class="decrementar-cantidad" data-detalle-id="${item.detalleId}" data-cantidad="${cantidad}" ${cantidad <= 1 ? 'disabled' : ''} style="background: #f0f0f0; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; color: #333; transition: all 0.2s ease; ${disabledStyle}" title="Disminuir">−</button>
                                <span class="cantidad-display" data-detalle-id="${item.detalleId}" style="min-width: 30px; text-align: center; font-weight: bold; font-size: 14px; color: #333;">${cantidad}</span>
                                <button class="incrementar-cantidad" data-detalle-id="${item.detalleId}" data-cantidad="${cantidad}" style="background: #f0f0f0; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; color: #333; transition: all 0.2s ease;" title="Aumentar">+</button>
                            </div>
                        </div>
                    </div>
                    <button class="eliminar-carrito-item" data-detalle-id="${item.detalleId}" style="background: #e63946; color: white; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; margin-left: 10px;" title="Eliminar">
                        ×
                    </button>
                </li>
            `;
        });
        
        // Mostrar productos agotados al final
        if (productosAgotados.length > 0) {
            html += '<li style="padding: 10px 0; border-top: 2px solid #ddd; margin-top: 10px;"><p style="margin: 0; font-size: 12px; color: #999; font-weight: 600; text-transform: uppercase;">Productos Agotados</p></li>';
            productosAgotados.forEach(item => {
                html += `
                    <li style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; background: #fff5f5; margin-bottom: 8px; border-radius: 8px; opacity: 0.7;">
                        <div style="flex: 1;">
                            <p style="margin: 0; font-weight: bold; font-size: 14px; color: #721c24;">${item.nombreProducto || 'Producto'}</p>
                            <p style="margin: 5px 0 0 0; font-size: 12px; color: #dc3545; display: flex; align-items: center; gap: 5px;">
                                <i class='bx bx-x-circle'></i>
                                <span>Agotado</span>
                            </p>
                        </div>
                        <button class="eliminar-carrito-item" data-detalle-id="${item.detalleId}" style="background: #e63946; color: white; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; margin-left: 10px;" title="Eliminar">
                            ×
                        </button>
                    </li>
                `;
            });
        }
        
        html += '</ul>';
        carritoContent.innerHTML = html;
        
        // Agregar event listeners a los botones de eliminar
        document.querySelectorAll('.eliminar-carrito-item').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                const detalleId = this.getAttribute('data-detalle-id');
                if (detalleId) {
                    await eliminarDelCarrito(detalleId);
                }
            });
        });
        
        // Agregar event listeners a los botones de incrementar cantidad
        document.querySelectorAll('.incrementar-cantidad').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                const detalleId = this.getAttribute('data-detalle-id');
                const cantidadActual = parseInt(this.getAttribute('data-cantidad')) || 1;
                const nuevaCantidad = cantidadActual + 1;
                if (detalleId) {
                    await actualizarCantidad(detalleId, nuevaCantidad);
                }
            });
        });
        
        // Agregar event listeners a los botones de decrementar cantidad
        document.querySelectorAll('.decrementar-cantidad').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                const detalleId = this.getAttribute('data-detalle-id');
                const cantidadActual = parseInt(this.getAttribute('data-cantidad')) || 1;
                if (cantidadActual > 1) {
                    const nuevaCantidad = cantidadActual - 1;
                    if (detalleId) {
                        await actualizarCantidad(detalleId, nuevaCantidad);
                    }
                }
            });
        });
    }
    
    // Actualizar cantidad de un producto en el carrito
    async function actualizarCantidad(detalleId, nuevaCantidad) {
        try {
            const response = await fetch(`/api/carrito/${usuarioId}/actualizar?detalleId=${detalleId}&cantidad=${nuevaCantidad}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Error al actualizar la cantidad');
            }
            
            // Recargar el carrito para mostrar la cantidad actualizada
            await cargarCarrito();
            
        } catch (error) {
            console.error('Error al actualizar cantidad:', error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'No se pudo actualizar la cantidad del producto',
                    timer: 2000,
                    showConfirmButton: false
                });
            }
        }
    }
    
    // Eliminar producto del carrito
    async function eliminarDelCarrito(detalleId) {
        try {
            const response = await fetch(`/api/carrito/${usuarioId}/eliminar/${detalleId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Error al eliminar del carrito');
            }
            
            // Recargar el carrito
            await cargarCarrito();
            
            // Mostrar notificación
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'success',
                    title: 'Producto eliminado',
                    text: 'El producto ha sido eliminado del carrito',
                    timer: 1500,
                    showConfirmButton: false
                });
            }
            
            // Recargar la página para actualizar el contador
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (error) {
            console.error('Error al eliminar del carrito:', error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'No se pudo eliminar el producto del carrito'
                });
            }
        }
    }
});

