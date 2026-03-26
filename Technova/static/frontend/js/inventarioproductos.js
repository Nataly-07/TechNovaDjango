document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formAgregarProducto");

    // Agregar producto via AJAX
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.textContent = "Agregando...";
            submitButton.disabled = true;

            const formData = new FormData(form);

            // Agregar imágenes adicionales al FormData
            const imagenesAdicionales = obtenerImagenesAdicionales();
            imagenesAdicionales.forEach((imagen, index) => {
                formData.append(`imagenes_adicionales[${index}]`, imagen);
            });

            try {
                const response = await fetch(window.TECHNOVA_ADMIN_PRODUCTO_CREAR_URL || "/admin/productos/crear/", {
                    method: "POST",
                    headers: {
                        "X-CSRF-TOKEN": document.querySelector('[name="csrfmiddlewaretoken"]').value,
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success !== false) {
                    // Mostrar mensaje de éxito
                    Swal.fire({
                        icon: 'success',
                        title: '¡Producto Agregado!',
                        text: result.message || 'El producto ha sido agregado correctamente',
                        timer: 3000,
                        showConfirmButton: false
                    });

                    // Limpiar formulario
                    form.reset();

                    // Recargar página para mostrar el nuevo producto
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);

                } else {
                    // Mostrar mensaje de error
                    const errorMessage = result.message || result.error || "Error al agregar el producto";
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: errorMessage
                    });

                    // Mostrar errores de validación específicos
                    if (result.errors) {
                        let errorText = "Errores de validación:\n";
                        for (const [field, messages] of Object.entries(result.errors)) {
                            errorText += `• ${field}: ${messages.join(', ')}\n`;
                        }
                        Swal.fire({
                            icon: 'error',
                            title: 'Errores de Validación',
                            text: errorText
                        });
                    }
                }
            } catch (error) {
                console.error("Error al enviar formulario:", error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error de Conexión',
                    text: "No se pudo conectar con el servidor. Verifica tu conexión a internet."
                });
            } finally {
                // Restaurar botón
                submitButton.textContent = originalText;
                submitButton.disabled = false;
            }
        });
    }

    // La confirmación de eliminación ahora se maneja con el modal personalizado en el HTML

    // Cálculo automático del precio de venta
    const precioCompraInput = document.getElementById('precio_compra');
    const porcentajeGananciaInput = document.getElementById('porcentaje_ganancia');
    const precioVentaInput = document.getElementById('precio_venta');

    function calcularPrecioVenta() {
        const precioCompra = parseFloat(precioCompraInput.value) || 0;
        const porcentajeGanancia = parseFloat(porcentajeGananciaInput.value) || 0;
        
        if (precioCompra > 0 && porcentajeGanancia >= 0) {
            const ganancia = (precioCompra * porcentajeGanancia) / 100;
            const precioVenta = precioCompra + ganancia;
            precioVentaInput.value = precioVenta.toFixed(2);
        } else {
            precioVentaInput.value = '';
        }
    }

    // Agregar event listeners para el cálculo automático
    if (precioCompraInput && porcentajeGananciaInput && precioVentaInput) {
        precioCompraInput.addEventListener('input', calcularPrecioVenta);
        porcentajeGananciaInput.addEventListener('input', calcularPrecioVenta);
        
        // Calcular al cargar la página si ya hay valores
        calcularPrecioVenta();
    }

    // ---------- Funciones para manejar imágenes adicionales ----------
    let indiceImagenActual = 1;

    function agregarCampoImagen() {
        const contenedor = document.getElementById('contenedorImagenesAdicionales');
        const nuevoDiv = document.createElement('div');
        nuevoDiv.className = 'imagen-adicional-row';
        nuevoDiv.setAttribute('data-imagen-index', indiceImagenActual);
        
        nuevoDiv.innerHTML = `
            <input type="url" name="imagenes_adicionales[]" maxlength="500" 
                   placeholder="https://ejemplo.com/imagen${indiceImagenActual}.jpg" 
                   class="imagen-adicional-input">
            <button type="button" class="btn-eliminar-imagen" 
                    onclick="eliminarImagenAdicional(${indiceImagenActual})" 
                    title="Eliminar imagen">
                <i class="bx bx-trash"></i>
            </button>
        `;
        
        contenedor.appendChild(nuevoDiv);
        indiceImagenActual++;
        
        // Agregar animación
        setTimeout(() => {
            nuevoDiv.style.animation = 'slideIn 0.3s ease-out';
        }, 10);
    }

    function eliminarImagenAdicional(indice) {
        const fila = document.querySelector(`[data-imagen-index="${indice}"]`);
        if (fila) {
            // Animación de salida
            fila.style.transition = 'all 0.3s ease-out';
            fila.style.opacity = '0';
            fila.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                fila.remove();
                // Reordenar los índices restantes
                reordenarIndicesImagenes();
            }, 300);
        }
    }

    function reordenarIndicesImagenes() {
        const filas = document.querySelectorAll('.imagen-adicional-row');
        filas.forEach((fila, index) => {
            const input = fila.querySelector('.imagen-adicional-input');
            const boton = fila.querySelector('.btn-eliminar-imagen');
            
            fila.setAttribute('data-imagen-index', index);
            input.placeholder = `https://ejemplo.com/imagen${index + 1}.jpg`;
            boton.setAttribute('onclick', `eliminarImagenAdicional(${index})`);
        });
        indiceImagenActual = filas.length;
    }

    function obtenerImagenesAdicionales() {
        const inputs = document.querySelectorAll('.imagen-adicional-input');
        const imagenes = [];
        
        inputs.forEach(input => {
            const url = input.value.trim();
            if (url) {
                imagenes.push(url);
            }
        });
        
        return imagenes;
    }

    // Validación para imágenes adicionales
    function validarImagenesAdicionales() {
        const imagenes = obtenerImagenesAdicionales();
        const feedbackElement = document.getElementById('feed-imagenes_adicionales');
        const fieldWrap = document.querySelector('[data-field-wrap="imagenes_adicionales"]');
        
        // Limpiar estado anterior
        fieldWrap.classList.remove('field-ok', 'field-err');
        feedbackElement.textContent = '';
        feedbackElement.className = 'field-feedback';
        
        if (imagenes.length === 0) {
            return true; // Las imágenes adicionales son opcionales
        }
        
        // Validar que cada URL sea válida
        for (let imagen of imagenes) {
            try {
                new URL(imagen);
            } catch (e) {
                fieldWrap.classList.add('field-err');
                feedbackElement.textContent = 'URL de imagen inválida: ' + imagen;
                feedbackElement.classList.add('is-err');
                return false;
            }
        }
        
        // Validar duplicados
        const imagenesUnicas = [...new Set(imagenes)];
        if (imagenesUnicas.length !== imagenes.length) {
            fieldWrap.classList.add('field-err');
            feedbackElement.textContent = 'Hay URLs de imagen duplicadas';
            feedbackElement.classList.add('is-err');
            return false;
        }
        
        // Todo válido
        fieldWrap.classList.add('field-ok');
        feedbackElement.textContent = `${imagenes.length} imagen(es) válida(s)`;
        feedbackElement.classList.add('is-ok');
        return true;
    }

    // Hacer las funciones globales para que puedan ser llamadas desde los onclick del HTML
    window.agregarCampoImagen = agregarCampoImagen;
    window.eliminarImagenAdicional = eliminarImagenAdicional;
    window.validarImagenesAdicionales = validarImagenesAdicionales;

    console.log("JavaScript de inventario cargado correctamente");
});
