from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
from datetime import date, datetime

from web.adapters.http.decorators import admin_login_required, admin_o_empleado_login_required
from orden.application.orden_compra_service import OrdenCompraService
from orden.dto.orden_compra_dto import OrdenCompraDto, DetalleOrdenDto


# Instancia del servicio (singleton)
orden_compra_service = OrdenCompraService()


def _get_usuario_autenticado(request):
    """Obtener usuario autenticado - Equivalente a SecurityUtil.getUsuarioAutenticado()"""
    # Usar sesión directamente como hace el decorador
    from usuario.adapters.web.session_views import SESSION_USUARIO_ID
    from usuario.infrastructure.models.usuario_model import Usuario
    
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return None
    
    try:
        usuario = Usuario.objects.get(pk=uid)
        if usuario.rol != Usuario.Rol.ADMIN:
            return None
        return usuario
    except Usuario.DoesNotExist:
        return None


@require_GET
def listar_ordenes(request):
    """
    GET /admin/ordenes/
    Equivalente a: @GetMapping public String listarOrdenes(Model model)
    """
    # Verificación manual de admin (temporal para depuración)
    from usuario.adapters.web.session_views import SESSION_USUARIO_ID
    from usuario.infrastructure.models.usuario_model import Usuario
    
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return redirect('web_login')
    
    try:
        usuario = Usuario.objects.get(pk=uid)
        if usuario.rol != Usuario.Rol.ADMIN:
            return redirect('inicio_autenticado')
    except Usuario.DoesNotExist:
        return redirect('web_login')
    
    try:
        # List<OrdenCompraDto> ordenes = ordenCompraService.listarOrdenes();
        ordenes = orden_compra_service.listar_ordenes()
        
        from orden.infrastructure.models import SolicitudOrdenCompraProv

        solicitudes_oc_prov_pendientes = SolicitudOrdenCompraProv.objects.filter(
            estado=SolicitudOrdenCompraProv.Estado.PENDIENTE
        ).count()

        context = {
            'ordenes': ordenes,
            'usuario': usuario,
            'solicitudes_oc_prov_pendientes': solicitudes_oc_prov_pendientes,
        }
        
        # return "frontend/admin/ordenes/lista";
        return render(request, 'frontend/admin/ordenes/lista.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar las órdenes: {str(e)}')
        return render(request, 'frontend/admin/ordenes/lista.html', {
            'ordenes': [],
            'usuario': usuario,
            'solicitudes_oc_prov_pendientes': 0,
        })


@require_GET
def mostrar_formulario_crear(request):
    """
    GET /admin/ordenes/crear/
    Equivalente a: @GetMapping("/crear") public String mostrarFormularioCrear(Model model)
    """
    # Verificación manual de admin (temporal para depuración)
    from usuario.adapters.web.session_views import SESSION_USUARIO_ID
    from usuario.infrastructure.models.usuario_model import Usuario
    
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return redirect('web_login')
    
    try:
        usuario = Usuario.objects.get(pk=uid)
        if usuario.rol != Usuario.Rol.ADMIN:
            return redirect('inicio_autenticado')
    except Usuario.DoesNotExist:
        return redirect('web_login')
    
    try:
        # List<ProveedorDto> proveedores = proveedorService.listarProveedores();
        from proveedor.models import Proveedor
        proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
        
        # List<ProductoDto> productos = productoService.listarProductos();
        from producto.models import Producto
        productos = Producto.objects.filter(activo=True).order_by('nombre')
        
        # OrdenCompraDto ordenDto = new OrdenCompraDto();
        orden_dto = OrdenCompraDto()
        
        context = {
            'orden': orden_dto,
            'proveedores': proveedores,
            'productos': productos,
            'usuario': usuario
        }
        
        # return "frontend/admin/ordenes/form";
        return render(request, 'frontend/admin/ordenes/form_working.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar el formulario: {str(e)}')
        return redirect('web_admin_ordenes_compra')


@admin_login_required
@require_POST
def guardar_orden(request):
    """
    POST /admin/ordenes/guardar/
    Equivalente a: @PostMapping("/guardar") public String guardarOrden(@ModelAttribute OrdenCompraDto ordenDto, RedirectAttributes redirectAttributes)
    """
    usuario = _get_usuario_autenticado(request)
    if usuario is None:
        return redirect('web_login')
    
    try:
        # Crear DTO desde los datos del formulario
        orden_dto = _crear_dto_desde_formulario(request)
        
        # Eliminar detalles vacíos o con cantidad 0
        # if (ordenDto.getDetalles() != null) {
        #     ordenDto.getDetalles().removeIf(d -> d.getProductoId() == null || d.getCantidad() == null || d.getCantidad() <= 0);
        # }
        orden_dto.limpiar_detalles_vacios()
        
        # if (ordenDto.getDetalles() == null || ordenDto.getDetalles().isEmpty()) {
        #     redirectAttributes.addFlashAttribute("error", "Debe agregar al menos un producto a la orden.");
        #     return "redirect:/admin/ordenes/crear";
        # }
        if not orden_dto.tiene_detalles_validos():
            messages.error(request, "Debe agregar al menos un producto a la orden.")
            return redirect('web_admin_orden_compra_crear')
        
        # ordenCompraService.crearOrden(ordenDto);
        orden_creada = orden_compra_service.crear_orden(orden_dto)
        
        # redirectAttributes.addFlashAttribute("mensaje", "Orden creada exitosamente.");
        messages.success(request, "Orden creada exitosamente.")
        
        # return "redirect:/admin/ordenes";
        return redirect('web_admin_ordenes_compra')
        
    except Exception as e:
        # redirectAttributes.addFlashAttribute("error", "Error al guardar la orden: " + e.getMessage());
        messages.error(request, f"Error al guardar la orden: {str(e)}")
        return redirect('web_admin_orden_compra_crear')


@admin_login_required
@require_POST
def recibir_orden(request, orden_id):
    """
    POST /admin/ordenes/recibir/{id}/
    Equivalente a: @PostMapping("/recibir/{id}") public String recibirOrden(@PathVariable Integer id, RedirectAttributes redirectAttributes)
    """
    usuario = _get_usuario_autenticado(request)
    if usuario is None:
        return redirect('web_login')
    
    try:
        # ordenCompraService.recibirOrden(id);
        orden_compra_service.recibir_orden(orden_id)
        
        # redirectAttributes.addFlashAttribute("mensaje", "Orden recibida y stock actualizado.");
        messages.success(request, "Orden recibida y stock actualizado.")
        
    except Exception as e:
        # redirectAttributes.addFlashAttribute("error", "Error al recibir la orden: " + e.getMessage());
        messages.error(request, f"Error al recibir la orden: {str(e)}")
    
    # return "redirect:/admin/ordenes";
    return redirect('web_admin_ordenes_compra')


@admin_o_empleado_login_required
@require_GET
def obtener_detalle_orden_api(request, orden_id):
    """
    GET /admin/ordenes/api/{id}/
    Detalle de orden (modelo) con datos de recepción para modal y validaciones.
    """
    from orden.infrastructure.models import OrdenCompra

    try:
        orden = OrdenCompra.objects.select_related("proveedor", "recepcion_validada_por").prefetch_related(
            "detalles__producto"
        ).get(pk=orden_id)
    except OrdenCompra.DoesNotExist:
        return JsonResponse({"error": "Orden no encontrada"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(
        {
            "id": orden.id,
            "proveedor_id": orden.proveedor_id,
            "proveedor_nombre": orden.proveedor.nombre,
            "fecha": orden.fecha.strftime("%Y-%m-%d") if orden.fecha else None,
            "total": float(orden.total) if orden.total else 0,
            "estado": orden.estado,
            "observaciones_recepcion": orden.observaciones_recepcion or "",
            "recepcion_resumen": orden.texto_resumen_recepcion_inventario(),
            "detalles": [
                {
                    "detalle_id": d.id,
                    "producto_id": d.producto_id,
                    "producto_nombre": d.producto.nombre,
                    "cantidad": d.cantidad,
                    "cantidad_recibida": d.cantidad_recibida,
                    "precio_unitario": float(d.precio_unitario) if d.precio_unitario else 0,
                    "subtotal": float(d.subtotal) if d.subtotal else 0,
                }
                for d in orden.detalles.all()
            ],
        }
    )


def _crear_dto_desde_formulario(request) -> OrdenCompraDto:
    """Crear DTO desde los datos del formulario POST"""
    # Datos principales
    proveedor_id = int(request.POST.get('proveedor_id', 0))
    fecha_str = request.POST.get('fecha', date.today().strftime('%Y-%m-%d'))
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    
    orden_dto = OrdenCompraDto(
        proveedor_id=proveedor_id,
        fecha=fecha,
        estado='pendiente'
    )
    
    # Procesar detalles dinámicos
    productos_ids = request.POST.getlist('producto_id[]')
    cantidades = request.POST.getlist('cantidad[]')
    precios = request.POST.getlist('precio_unitario[]')
    
    for i, producto_id in enumerate(productos_ids):
        if producto_id and i < len(cantidades) and i < len(precios):
            try:
                producto_id = int(producto_id)
                cantidad = int(cantidades[i])
                precio_unitario = Decimal(precios[i])
                
                if cantidad > 0 and precio_unitario > 0:
                    orden_dto.agregar_detalle(producto_id, cantidad, precio_unitario)
            except (ValueError, TypeError):
                continue
    
    return orden_dto
