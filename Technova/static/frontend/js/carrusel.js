// Funcionalidad del carrusel de productos
document.addEventListener('DOMContentLoaded', function() {
    // Obtener todos los contenedores de carrusel
    const carruseles = document.querySelectorAll('.carrusel-productos-contenedor');
    
    carruseles.forEach(contenedor => {
        const track = contenedor.querySelector('.carrusel-track');
        const prevBtn = contenedor.querySelector('.carrusel-btn.prev');
        const nextBtn = contenedor.querySelector('.carrusel-btn.next');
        
        if (!track || !prevBtn || !nextBtn) {
            return; // Si no hay elementos necesarios, continuar con el siguiente
        }
        
        // Función para desplazar el carrusel
        function scrollCarrusel(direction) {
            const scrollAmount = 250; // Cantidad de píxeles a desplazar
            const currentScroll = track.scrollLeft;
            const newScroll = direction === 'next' 
                ? currentScroll + scrollAmount 
                : currentScroll - scrollAmount;
            
            track.scrollTo({
                left: newScroll,
                behavior: 'smooth'
            });
        }
        
        // Event listeners para los botones
        prevBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            scrollCarrusel('prev');
        });
        
        nextBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            scrollCarrusel('next');
        });
        
        // Actualizar visibilidad de botones según la posición del scroll
        function updateButtons() {
            const isAtStart = track.scrollLeft <= 10;
            const isAtEnd = track.scrollLeft >= track.scrollWidth - track.clientWidth - 10;
            
            prevBtn.style.opacity = isAtStart ? '0.5' : '1';
            prevBtn.style.cursor = isAtStart ? 'not-allowed' : 'pointer';
            prevBtn.disabled = isAtStart;
            
            nextBtn.style.opacity = isAtEnd ? '0.5' : '1';
            nextBtn.style.cursor = isAtEnd ? 'not-allowed' : 'pointer';
            nextBtn.disabled = isAtEnd;
        }
        
        // Actualizar botones cuando se hace scroll
        track.addEventListener('scroll', updateButtons);
        
        // Actualizar botones al cargar
        updateButtons();
        
        // Actualizar botones cuando cambia el tamaño de la ventana
        window.addEventListener('resize', updateButtons);
    });
});






