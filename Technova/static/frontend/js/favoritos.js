// Manejo de favoritos
document.addEventListener('DOMContentLoaded', function() {
    console.log('Script de favoritos cargado');
    
    // Verificar si usuarioId está definido
    if (typeof usuarioId === 'undefined' || usuarioId === null) {
        console.warn('usuarioId no está definido, los favoritos no funcionarán');
        return; // Si no hay usuario, salir
    }
    
    console.log('usuarioId:', usuarioId);
    
    const favoritoBtns = document.querySelectorAll('.favorito-btn');
    console.log('Botones de favoritos encontrados:', favoritoBtns.length);
    
    if (favoritoBtns.length === 0) {
        console.warn('No hay botones de favoritos en esta página');
        return; // No hay botones de favoritos en esta página
    }
    
    // Verificar estado inicial de favoritos
    async function verificarFavoritos() {
        try {
            const response = await fetch(`/api/favoritos/usuario/${usuarioId}`);
            if (!response.ok) {
                console.error('Error al obtener favoritos:', response.status, response.statusText);
                return;
            }
            
            const favoritos = await response.json();
            const favoritoIds = favoritos.map(f => f.productoId);
            
            favoritoBtns.forEach(btn => {
                const productoIdStr = btn.getAttribute('data-producto-id');
                if (!productoIdStr) {
                    console.warn('Botón de favorito sin data-producto-id');
                    return;
                }
                
                const productoId = parseInt(productoIdStr);
                if (isNaN(productoId)) {
                    console.warn('Producto ID inválido:', productoIdStr);
                    return;
                }
                
                if (favoritoIds.includes(productoId)) {
                    btn.style.background = '#e63946';
                    btn.textContent = '❤️';
                    btn.setAttribute('data-es-favorito', 'true');
                } else {
                    btn.style.background = '#ff6b9d';
                    btn.textContent = '🤍';
                    btn.setAttribute('data-es-favorito', 'false');
                }
            });
        } catch (error) {
            console.error('Error al verificar favoritos:', error);
        }
    }
    
    // Agregar/quitar favorito
    favoritoBtns.forEach((btn, index) => {
        console.log(`Agregando listener al botón ${index + 1}, productoId:`, btn.getAttribute('data-producto-id'));
        
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Click en botón de favorito');
            
            const productoIdStr = this.getAttribute('data-producto-id');
            if (!productoIdStr) {
                console.error('Botón de favorito sin data-producto-id');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: 'No se pudo identificar el producto'
                    });
                }
                return;
            }
            
            const productoId = parseInt(productoIdStr);
            if (isNaN(productoId)) {
                console.error('Producto ID inválido:', productoIdStr);
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: 'ID de producto inválido'
                    });
                }
                return;
            }
            
            console.log('Toggle favorito para producto:', productoId);
            
            // Deshabilitar el botón mientras se procesa
            this.disabled = true;
            this.style.opacity = '0.6';
            this.style.cursor = 'not-allowed';
            
            await toggleFavorito(productoId, this);
        });
    });
    
    console.log('Listeners de favoritos agregados');
    
    async function toggleFavorito(productoId, btn) {
        try {
            console.log(`Llamando a API: /api/favoritos/usuario/${usuarioId}/producto/${productoId}/toggle`);
            
            // Preparar headers
            const headers = {
                'Content-Type': 'application/json'
            };
            
            // Agregar CSRF token si está disponible
            if (typeof csrfToken !== 'undefined' && csrfToken && typeof csrfHeaderName !== 'undefined' && csrfHeaderName) {
                headers[csrfHeaderName] = csrfToken;
            }
            
            const url = `/api/favoritos/usuario/${usuarioId}/producto/${productoId}/toggle`;
            console.log('URL:', url);
            console.log('Headers:', headers);
            
            const response = await fetch(url, {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin'
            });
            
            console.log('Respuesta recibida:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Error en la respuesta:', response.status, errorText);
                throw new Error(`Error al actualizar favorito: ${response.status} - ${errorText}`);
            }
            
            const esFavorito = await response.json();
            
            // Actualizar el botón visualmente
            if (esFavorito) {
                btn.style.background = '#e63946';
                btn.textContent = '❤️';
                btn.setAttribute('data-es-favorito', 'true');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Agregado a favoritos',
                        timer: 1500,
                        showConfirmButton: false,
                        toast: true,
                        position: 'top-end'
                    });
                }
            } else {
                btn.style.background = '#ff6b9d';
                btn.textContent = '🤍';
                btn.setAttribute('data-es-favorito', 'false');
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'info',
                        title: 'Eliminado de favoritos',
                        timer: 1500,
                        showConfirmButton: false,
                        toast: true,
                        position: 'top-end'
                    });
                }
            }
            
            // Recargar la página para actualizar el contador
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (error) {
            console.error('Error al actualizar favorito:', error);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'No se pudo actualizar el favorito. Por favor, intenta nuevamente.'
                });
            }
            
            // Rehabilitar el botón
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        }
    }
    
    // Verificar favoritos al cargar
    verificarFavoritos();
});

