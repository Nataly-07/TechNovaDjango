// Funciones para búsqueda y filtrado de productos

let productosOriginales = null;

// Función para buscar productos con filtros
async function buscarProductos() {
    const termino = document.getElementById('busquedaTermino')?.value?.trim() || '';
    const marca = document.getElementById('filtroMarca')?.value?.trim() || '';
    const categoria = document.getElementById('filtroCategoria')?.value?.trim() || '';
    const precioMin = document.getElementById('filtroPrecioMin')?.value?.trim() || '';
    const precioMax = document.getElementById('filtroPrecioMax')?.value?.trim() || '';
    const disponibilidad = document.getElementById('filtroDisponibilidad')?.value?.trim() || '';
    
    // Construir parámetros de búsqueda
    const params = new URLSearchParams();
    if (termino) params.append('termino', termino);
    if (marca) params.append('marca', marca);
    if (categoria) params.append('categoria', categoria);
    if (precioMin) params.append('precioMin', precioMin);
    if (precioMax) params.append('precioMax', precioMax);
    if (disponibilidad) params.append('disponibilidad', disponibilidad);
    
    // Si no hay ningún filtro, mostrar productos originales
    if (!termino && !marca && !categoria && !precioMin && !precioMax && !disponibilidad) {
        limpiarFiltros();
        return;
    }
    
    try {
        // Mostrar indicador de carga
        const resultadosDiv = document.getElementById('resultadosBusqueda');
        const productosFiltradosDiv = document.getElementById('productosFiltrados');
        const productosOriginalesDiv = document.getElementById('productosOriginales');
        
        if (resultadosDiv) {
            resultadosDiv.classList.add('show');
            productosFiltradosDiv.innerHTML = '<p style="text-align: center; padding: 20px;">Buscando productos...</p>';
        }
        
        // Ocultar productos originales
        if (productosOriginalesDiv) {
            productosOriginalesDiv.style.display = 'none';
        }
        
        // Llamar al endpoint de búsqueda avanzada
        const response = await fetch(`/api/productos/buscar-avanzado?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error('Error al buscar productos');
        }
        
        const productos = await response.json();
        
        // Mostrar resultados
        if (productosFiltradosDiv) {
            if (productos.length === 0) {
                productosFiltradosDiv.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">No se encontraron productos con los filtros seleccionados.</p>';
            } else {
                productosFiltradosDiv.innerHTML = productos.map(producto => crearTarjetaProducto(producto)).join('');
            }
        }
        
        // Mostrar contenedor de resultados
        if (resultadosDiv) {
            resultadosDiv.classList.add('show');
        }
        
        // Inicializar eventos de favoritos y carrito después de renderizar
        setTimeout(() => {
            inicializarEventosProductos();
        }, 100);
        
    } catch (error) {
        console.error('Error al buscar productos:', error);
        const productosFiltradosDiv = document.getElementById('productosFiltrados');
        if (productosFiltradosDiv) {
            productosFiltradosDiv.innerHTML = '<p style="text-align: center; padding: 20px; color: #e63946;">Error al buscar productos. Por favor, intenta de nuevo.</p>';
        }
    }
}

// Función para crear tarjeta de producto
function crearTarjetaProducto(producto) {
    const imagenUrl = producto.imagen && producto.imagen.startsWith('http') 
        ? producto.imagen 
        : (producto.imagen ? `/frontend/imagenes/${producto.imagen}` : '/frontend/imagenes/placeholder.png');
    
    const stock = producto.stock != null ? producto.stock : 0;
    const disponible = stock > 0;
    const disponibilidadBadge = disponible 
        ? '<span style="display: inline-flex; align-items: center; gap: 3px; background: #d4edda; color: #155724; padding: 4px 8px; border-radius: 15px; font-size: 11px; font-weight: 600;"><span>✓</span><span>Disponible</span></span>'
        : '<span style="display: inline-flex; align-items: center; gap: 3px; background: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 15px; font-size: 11px; font-weight: 600;"><span>✗</span><span>Agotado</span></span>';
    
    const precioOriginal = producto.precioOriginal || (producto.caracteristica?.precioVenta ? producto.caracteristica.precioVenta * 1.05 : null);
    const precioDescuento = producto.precioDescuento || producto.caracteristica?.precioVenta || null;
    
    const precioHtml = (precioOriginal && precioDescuento) 
        ? `
            <p class="precio-original" style="text-decoration: line-through; color: gray; margin: 8px 0; font-size: 0.9em;">
                $${Math.round(precioOriginal)}
            </p>
            <p class="precio-descuento" style="color: #006600; font-weight: bold; margin: 8px 0; font-size: 1.1em;">
                $${Math.round(precioDescuento)}
                <span class="descuento" style="background-color: #cce5cc; color: #006600; padding: 3px 8px; border-radius: 6px; font-size: 0.9em; margin-left: 8px;">-5%</span>
            </p>
        `
        : (precioDescuento ? `<p style="color: #006600; font-weight: bold; margin: 8px 0; font-size: 1.1em;">$${Math.round(precioDescuento)}</p>` : '');
    
    // Determinar si el usuario está autenticado (verificar si existe el formulario de carrito)
    const isAuthenticated = document.querySelector('form[action*="/carrito/agregar"]') !== null;
    
    const botonesHtml = isAuthenticated 
        ? `
            <form action="/carrito/agregar/${producto.id}" method="POST" style="display: inline;">
                <input type="hidden" name="${document.querySelector('input[name*="_csrf"]')?.name || '_csrf'}" value="${document.querySelector('input[name*="_csrf"]')?.value || ''}" />
                <button type="submit" class="carrito-btn" style="background: var(--gradient-secondary); border: none; border-radius: 50%; width: 40px; height: 40px; color: white; font-size: 18px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">&#128722;</button>
            </form>
            <button class="favorito-btn" data-producto-id="${producto.id}" style="background: #ff6b9d; border: none; border-radius: 50%; width: 40px; height: 40px; color: white; font-size: 18px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all 0.3s ease;">❤️</button>
        `
        : `
            <a href="/login" class="carrito-btn" style="text-decoration: none; color: white; display: inline-flex; align-items: center; justify-content: center; background: var(--gradient-secondary); border: none; border-radius: 50%; width: 40px; height: 40px; font-size: 18px; cursor: pointer;">&#128722;</a>
        `;
    
    return `
        <div class="producto-card" style="background: white; border-radius: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 15px; text-align: center; position: relative; display: flex; flex-direction: column; align-items: center;">
            <img src="${imagenUrl}" alt="${producto.nombre || 'Producto'}" 
                 style="width: 140px; height: auto; margin: 0 auto; display: block; border-radius: 10px; margin-bottom: 10px;">
            <a href="/producto/${producto.id}" style="display: inline-block; margin: 12px 0; background: var(--gradient-secondary); color: white; padding: 6px 12px; border-radius: 12px; font-weight: bold; font-size: 0.9em; text-decoration: none;">Ver Más Detalles</a>
            <h3 style="font-weight: bold; margin: 10px 0 6px; font-size: 1em;">${producto.nombre || 'Producto'}</h3>
            <div style="margin: 5px 0;">
                ${disponibilidadBadge}
            </div>
            <p style="margin: 6px 0; font-size: 0.9em;">4.5 ⭐</p>
            ${precioHtml}
            <div style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 10px;">
                ${botonesHtml}
            </div>
        </div>
    `;
}

// Función para mostrar/ocultar filtros
function toggleFiltros() {
    const filtrosContainer = document.getElementById('filtrosContainer');
    const btnToggle = document.getElementById('btnFiltrosToggle');
    
    if (filtrosContainer && btnToggle) {
        const isVisible = filtrosContainer.style.display === 'flex' || 
                         filtrosContainer.classList.contains('show');
        
        if (isVisible) {
            filtrosContainer.style.display = 'none';
            filtrosContainer.classList.remove('show');
            btnToggle.classList.remove('active');
        } else {
            filtrosContainer.style.display = 'flex';
            filtrosContainer.classList.add('show');
            btnToggle.classList.add('active');
        }
    }
}

// Función para limpiar filtros y mostrar productos originales
function limpiarFiltros() {
    // Limpiar campos de búsqueda
    const busquedaTermino = document.getElementById('busquedaTermino');
    const filtroMarca = document.getElementById('filtroMarca');
    const filtroCategoria = document.getElementById('filtroCategoria');
    const filtroPrecioMin = document.getElementById('filtroPrecioMin');
    const filtroPrecioMax = document.getElementById('filtroPrecioMax');
    const filtroDisponibilidad = document.getElementById('filtroDisponibilidad');
    
    if (busquedaTermino) busquedaTermino.value = '';
    if (filtroMarca) filtroMarca.value = '';
    if (filtroCategoria) filtroCategoria.value = '';
    if (filtroPrecioMin) filtroPrecioMin.value = '';
    if (filtroPrecioMax) filtroPrecioMax.value = '';
    if (filtroDisponibilidad) filtroDisponibilidad.value = '';
    
    // Ocultar resultados de búsqueda
    const resultadosDiv = document.getElementById('resultadosBusqueda');
    if (resultadosDiv) {
        resultadosDiv.classList.remove('show');
    }
    
    // Mostrar productos originales
    const productosOriginalesDiv = document.getElementById('productosOriginales');
    if (productosOriginalesDiv) {
        productosOriginalesDiv.style.display = 'block';
    }
}

// Función para inicializar eventos de productos (favoritos, carrito)
function inicializarEventosProductos() {
    // Inicializar botones de favoritos si existe el script
    if (typeof window.inicializarFavoritos === 'function') {
        window.inicializarFavoritos();
    }
    
    // Los formularios de carrito ya funcionan automáticamente con el submit
}

// Agregar event listeners cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Permitir búsqueda al cambiar filtros automáticamente (opcional)
    const filtros = ['filtroMarca', 'filtroCategoria', 'filtroPrecioMin', 'filtroPrecioMax', 'filtroDisponibilidad'];
    filtros.forEach(filtroId => {
        const elemento = document.getElementById(filtroId);
        if (elemento) {
            elemento.addEventListener('change', function() {
                // Solo buscar si hay algún filtro activo
                const tieneFiltros = Array.from(document.querySelectorAll('#filtroMarca, #filtroCategoria, #filtroPrecioMin, #filtroPrecioMax, #filtroDisponibilidad, #busquedaTermino'))
                    .some(el => el.value && el.value.trim() !== '');
                if (tieneFiltros) {
                    buscarProductos();
                }
            });
        }
    });
});

