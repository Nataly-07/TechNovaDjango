import json
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods

from compra.models import Compra, DetalleCompra
from envio.models import Envio
from mensajeria.models import MensajeDirecto, Notificacion
from pago.models import MedioPago, Pago
from producto.domain.entities import ProductoEntidad
from producto.models import Producto, ProductoCatalogoExtra
from common.container import get_producto_service, get_proveedor_service
from proveedor.domain.entities import ProveedorEntidad
from proveedor.models import Proveedor
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta

from web.application.admin_web_service import (
    EMAIL_ALTA_RE,
    PRODUCTO_CATEGORIAS_ALTA_WEB,
    PRODUCTO_COLORES_ALTA_WEB,
    PRODUCTO_MARCAS_ALTA_WEB,
    TELEFONO_PROV_RE,
    admin_usuario_sesion,
    categorias_alta_permitidas,
    decimal_desde_post,
    marcas_alta_permitidas,
    normalizar_nombre_catalogo,
    producto_modal_dict,
    proveedor_modal_dict,
    redirect_inventario_tab_marcas,
    usuario_modal_dict,
    validar_nombre_persona,
)
from web.application.pagos_admin_service import (
    badge_clase_estado_pago,
    etiqueta_medio_pago_mostrar,
    fecha_larga_es,
    filtrar_queryset_pagos_por_estado_get,
    lista_metodos_pago_display,
    parse_date_param,
    venta_cliente_desde_pago,
)
from web.adapters.http.decorators import admin_login_required


@admin_login_required
def perfil_admin(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    mensajes_pendientes = MensajeDirecto.objects.exclude(
        estado=MensajeDirecto.Estado.RESPONDIDO
    ).count()
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario_id=uid, leida=False
    ).count()
    
    # Importar y contar órdenes de compra con manejo de errores
    ordenes_compra_count = 0
    try:
        from orden.infrastructure.models import OrdenCompra
        ordenes_compra_count = OrdenCompra.objects.count()
    except ImportError:
        try:
            from orden.models import OrdenCompra
            ordenes_compra_count = OrdenCompra.objects.count()
        except ImportError:
            # El módulo de órdenes no está disponible
            pass
    
    ctx = {
        "usuario": usuario,
        "users_count": Usuario.objects.count(),
        "productos_count": Producto.objects.filter(activo=True).count(),
        "proveedores_count": Proveedor.objects.filter(activo=True).count(),
        "ordenes_compra_count": ordenes_compra_count,
        "reportes_disponibles": 3,
        "mensajes_pendientes": mensajes_pendientes,
        "notificaciones_no_leidas": notificaciones_no_leidas,
        "pedidos_procesados": Venta.objects.count(),
        "transacciones_procesadas": Pago.objects.count(),
        "categorias_donut_labels_json": mark_safe(
            json.dumps(["Celulares", "Computadores"], ensure_ascii=False)
        ),
        "categorias_donut_series_json": mark_safe(json.dumps([0, 0, 0], ensure_ascii=False)),
    }
    return render(request, "frontend/admin/perfil.html", ctx)


@admin_login_required
def admin_usuarios(request):
    usuario = admin_usuario_sesion(request)
    rol = (request.GET.get("rol") or "").strip().lower()
    busqueda = (request.GET.get("busqueda") or "").strip()

    qs = Usuario.objects.all().order_by("id")
    if rol in {Usuario.Rol.ADMIN, Usuario.Rol.CLIENTE, Usuario.Rol.EMPLEADO}:
        qs = qs.filter(rol=rol)
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda)
            | Q(apellidos__icontains=busqueda)
            | Q(correo_electronico__icontains=busqueda)
            | Q(numero_documento__icontains=busqueda)
        )

    usuarios = list(qs)
    usuarios_json = json.dumps(
        [usuario_modal_dict(u) for u in usuarios],
        ensure_ascii=False,
    )
    ctx = {
        "usuario": usuario,
        "usuarios": usuarios,
        "usuarios_json": mark_safe(usuarios_json),
        "rol": rol,
        "busqueda": busqueda,
        "total_usuarios": Usuario.objects.count(),
        "total_clientes": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
        "total_admin": Usuario.objects.filter(rol=Usuario.Rol.ADMIN).count(),
        "total_empleados": Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO).count(),
    }
    return render(request, "frontend/admin/usuarios.html", ctx)


@admin_login_required
@require_http_methods(["POST"])
def admin_usuario_crear(request):
    """Alta de administrador o empleado (misma regla que API + registro_usuario_service)."""
    admin = admin_usuario_sesion(request)
    if admin.rol != Usuario.Rol.ADMIN:
        messages.error(request, "Solo el administrador puede crear usuarios desde esta pantalla.")
        return redirect("web_admin_usuarios")

    role = (request.POST.get("role") or "").strip().lower()
    if role not in (Usuario.Rol.ADMIN, Usuario.Rol.EMPLEADO):
        messages.error(request, "Debes seleccionar rol Administrador o Empleado.")
        return redirect("web_admin_usuarios")

    first_name = (request.POST.get("firstName") or "").strip()
    last_name = (request.POST.get("lastName") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    confirm = request.POST.get("confirmPassword") or ""
    phone = (request.POST.get("phone") or "").strip()
    doc_type = (request.POST.get("documentType") or "").strip()
    doc_num = (request.POST.get("documentNumber") or "").strip()
    address = (request.POST.get("address") or "").strip()

    if not validar_nombre_persona(first_name):
        messages.error(
            request,
            "El primer nombre debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not validar_nombre_persona(last_name):
        messages.error(
            request,
            "El apellido debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not EMAIL_ALTA_RE.match(email):
        messages.error(request, "Ingresa un correo electrónico válido.")
        return redirect("web_admin_usuarios")
    if len(phone) != 10 or not phone.isdigit():
        messages.error(request, "El teléfono debe tener exactamente 10 dígitos.")
        return redirect("web_admin_usuarios")
    if not doc_type:
        messages.error(request, "Selecciona un tipo de documento.")
        return redirect("web_admin_usuarios")
    if len(address) < 8:
        messages.error(request, "La dirección debe tener al menos 8 caracteres.")
        return redirect("web_admin_usuarios")
    if password != confirm:
        messages.error(request, "Las contraseñas no coinciden.")
        return redirect("web_admin_usuarios")

    payload = {
        "email": email,
        "password": password,
        "firstName": first_name,
        "lastName": last_name,
        "documentType": doc_type,
        "documentNumber": doc_num,
        "phone": phone,
        "address": address,
        "role": role,
    }
    result = registrar_usuario_desde_payload(payload, admin_usuario=admin)
    if result.error:
        messages.error(request, result.error)
    else:
        messages.success(
            request,
            f"Usuario {result.usuario.correo_electronico} creado correctamente.",
        )
    return redirect("web_admin_usuarios")


@admin_login_required
@require_http_methods(["POST"])
def admin_usuario_estado(request, usuario_id: int):
    admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    u = get_object_or_404(Usuario, pk=usuario_id)
    u.activo = activar
    u.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Usuario activado correctamente." if activar else "Usuario desactivado correctamente.",
    )
    return redirect("web_admin_usuarios")


@admin_login_required
def admin_inventario(request):
    usuario = admin_usuario_sesion(request)
    categoria = (request.GET.get("categoria") or "").strip()
    busqueda = (request.GET.get("busqueda") or "").strip()

    qs = Producto.objects.select_related("proveedor").prefetch_related("imagenes").order_by("id")
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)
    if busqueda:
        qs = qs.filter(Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda))

    productos = list(qs)
    productos_json = json.dumps(
        [producto_modal_dict(p) for p in productos],
        ensure_ascii=False,
    )

    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(activo=True, stock__gt=0, stock__lt=10).count()
    productos_agotados = Producto.objects.filter(activo=True, stock=0).count()

    categorias_opts = sorted(
        set(Producto.objects.exclude(categoria="").values_list("categoria", flat=True).distinct())
        | categorias_alta_permitidas(),
        key=str.lower,
    )

    counts_cat = {
        row["categoria"]: row["cantidad"]
        for row in Producto.objects.exclude(categoria="")
        .values("categoria")
        .annotate(cantidad=Count("id"))
    }
    extras_cat = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.CATEGORIA).values_list(
            "nombre", flat=True
        )
    )
    categorias_info = [
        {"nombre": n, "cantidad": counts_cat.get(n, 0)}
        for n in sorted(set(counts_cat.keys()) | extras_cat, key=str.lower)
    ]

    counts_marca = {
        row["marca"]: row["cantidad"]
        for row in Producto.objects.exclude(marca="").values("marca").annotate(cantidad=Count("id"))
    }
    extras_marca = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.MARCA).values_list(
            "nombre", flat=True
        )
    )
    marcas_info = [
        {"nombre": n, "cantidad": counts_marca.get(n, 0)}
        for n in sorted(set(counts_marca.keys()) | extras_marca, key=str.lower)
    ]

    compras_recientes = []
    for c in Compra.objects.select_related("proveedor").order_by("-fecha_compra")[:15]:
        n_items = DetalleCompra.objects.filter(compra_id=c.id).count()
        compras_recientes.append(
            {
                "compra_id": c.id,
                "fecha_compra": c.fecha_compra,
                "total": c.total,
                "items": n_items,
            }
        )

    ventas_recientes = []
    for v in Venta.objects.select_related("usuario").order_by("-fecha_venta")[:15]:
        ventas_recientes.append(
            {
                "venta_id": v.id,
                "fecha_venta": v.fecha_venta,
                "usuario": v.usuario.correo_electronico if v.usuario_id else "",
            }
        )

    ctx = {
        "usuario": usuario,
        "productos": productos,
        "productos_json": mark_safe(productos_json),
        "categoria": categoria,
        "busqueda": busqueda,
        "categorias_opts": categorias_opts,
        "total_productos": total_productos,
        "productos_bajo_stock": productos_bajo_stock,
        "productos_agotados": productos_agotados,
        "categorias_info": categorias_info,
        "marcas_info": marcas_info,
        "compras_recientes": compras_recientes,
        "ventas_recientes": ventas_recientes,
        "proveedores": Proveedor.objects.filter(activo=True).order_by("nombre"),
        "categorias_alta_list": sorted(categorias_alta_permitidas(), key=str.lower),
        "marcas_alta_list": sorted(marcas_alta_permitidas(), key=str.lower),
    }
    return render(request, "frontend/admin/inventario.html", ctx)


@admin_login_required
@require_http_methods(["POST"])
def admin_producto_crear(request):
    """Alta de producto vía caso de uso (misma regla que API JSON)."""
    admin_usuario_sesion(request)

    codigo = (request.POST.get("codigo") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()
    marca = (request.POST.get("marca") or "").strip()
    color = (request.POST.get("color") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    imagen_url = (request.POST.get("imagen_url") or "").strip()
    
    # Procesar imágenes adicionales
    imagenes_adicionales = request.POST.getlist("imagenes_adicionales[]")
    imagenes_adicionales = [img.strip() for img in imagenes_adicionales if img.strip()]

    if not codigo or len(codigo) > 50:
        messages.error(request, "El código es obligatorio (máximo 50 caracteres).")
        return redirect("web_admin_inventario")
    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_inventario")
    if categoria not in categorias_alta_permitidas():
        messages.error(request, "Selecciona una categoría válida de la lista.")
        return redirect("web_admin_inventario")
    if marca not in marcas_alta_permitidas():
        messages.error(request, "Selecciona una marca válida de la lista.")
        return redirect("web_admin_inventario")
    if color not in PRODUCTO_COLORES_ALTA_WEB:
        messages.error(request, "Selecciona un color de la lista.")
        return redirect("web_admin_inventario")

    try:
        proveedor_id = int(request.POST.get("proveedor_id") or "0")
    except (TypeError, ValueError):
        messages.error(request, "Selecciona un proveedor válido.")
        return redirect("web_admin_inventario")

    if not Proveedor.objects.filter(pk=proveedor_id, activo=True).exists():
        messages.error(request, "El proveedor no existe o está inactivo.")
        return redirect("web_admin_inventario")

    try:
        stock = int(request.POST.get("stock") or "0")
        if stock < 0:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "El stock debe ser un entero mayor o igual a 0.")
        return redirect("web_admin_inventario")

    costo = decimal_desde_post(request.POST.get("costo_unitario"))
    if costo is None or costo < 0:
        messages.error(request, "El costo unitario debe ser un número mayor o igual a 0.")
        return redirect("web_admin_inventario")

    precio = decimal_desde_post(request.POST.get("precio_venta"))
    if precio is None or precio <= 0:
        messages.error(request, "El precio de venta debe ser un número mayor que 0.")
        return redirect("web_admin_inventario")

    if precio <= costo:
        messages.error(request, "El precio de venta debe ser mayor que el costo unitario.")
        return redirect("web_admin_inventario")

    if imagen_url:
        if len(imagen_url) > 500:
            messages.error(request, "La URL de imagen es demasiado larga.")
            return redirect("web_admin_inventario")
        if not (imagen_url.startswith("http://") or imagen_url.startswith("https://")):
            messages.error(
                request,
                "La imagen debe ser una URL que comience con http:// o https://",
            )
            return redirect("web_admin_inventario")
            
    # Validar imágenes adicionales
    for imagen in imagenes_adicionales:
        if len(imagen) > 500:
            messages.error(request, "Una URL de imagen adicional es demasiado larga.")
            return redirect("web_admin_inventario")
        if not (imagen.startswith("http://") or imagen.startswith("https://")):
            messages.error(
                request,
                "Las imágenes adicionales deben ser URLs que comiencen con http:// o https://",
            )
            return redirect("web_admin_inventario")

    entidad = ProductoEntidad(
        id=None,
        codigo=codigo,
        nombre=nombre,
        proveedor_id=proveedor_id,
        stock=stock,
        costo_unitario=costo,
        activo=True,
        imagen_url=imagen_url,
        categoria=categoria,
        marca=marca,
        color=color,
        descripcion=descripcion,
        precio_venta=precio,
    )
    service = get_producto_service()
    try:
        creado = service.crear(entidad)
        
        # Guardar imágenes adicionales si existen
        if imagenes_adicionales:
            from producto.models import ProductoImagen
            
            # Eliminar imágenes existentes para este producto (si las hubiera)
            ProductoImagen.objects.filter(producto_id=creado.id).delete()
            
            # Crear nuevas imágenes adicionales
            for orden, url in enumerate(imagenes_adicionales):
                ProductoImagen.objects.create(
                    producto_id=creado.id,
                    url=url,
                    orden=orden + 1,  # Empezar desde 1 para el usuario
                    activa=True
                )
                
    except IntegrityError:
        messages.error(request, "Ya existe un producto con ese código.")
        return redirect("web_admin_inventario")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_inventario")

    messages.success(request, f"Producto «{creado.nombre}» creado correctamente.")
    return redirect("web_admin_inventario")


@admin_login_required
@require_http_methods(["POST"])
def admin_producto_estado(request, producto_id: int):
    admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    p = get_object_or_404(Producto, pk=producto_id)
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Producto activado correctamente." if activar else "Producto desactivado correctamente.",
    )
    return redirect("web_admin_inventario")


@admin_login_required
@require_http_methods(["POST"])
def admin_catalogo_categoria_agregar(request):
    admin_usuario_sesion(request)
    nombre = normalizar_nombre_catalogo(request.POST.get("nombre") or "")
    if len(nombre) < 2:
        messages.error(request, "El nombre de categoría debe tener al menos 2 caracteres.")
        return redirect_inventario_tab_marcas()
    if len(nombre) > 120:
        messages.error(request, "El nombre es demasiado largo.")
        return redirect_inventario_tab_marcas()
    if nombre in PRODUCTO_CATEGORIAS_ALTA_WEB:
        messages.info(request, "Esa categoría ya está disponible en el sistema.")
        return redirect_inventario_tab_marcas()
    if ProductoCatalogoExtra.objects.filter(
        tipo=ProductoCatalogoExtra.Tipo.CATEGORIA, nombre__iexact=nombre
    ).exists():
        messages.warning(request, "Esa categoría ya fue registrada.")
        return redirect_inventario_tab_marcas()
    try:
        ProductoCatalogoExtra.objects.create(
            tipo=ProductoCatalogoExtra.Tipo.CATEGORIA, nombre=nombre
        )
    except IntegrityError:
        messages.warning(request, "Esa categoría ya existe.")
        return redirect_inventario_tab_marcas()
    messages.success(request, f"Categoría «{nombre}» agregada. Ya puedes usarla al crear productos.")
    return redirect_inventario_tab_marcas()


@admin_login_required
@require_http_methods(["POST"])
def admin_catalogo_marca_agregar(request):
    admin_usuario_sesion(request)
    nombre = normalizar_nombre_catalogo(request.POST.get("nombre") or "")
    if len(nombre) < 2:
        messages.error(request, "El nombre de marca debe tener al menos 2 caracteres.")
        return redirect_inventario_tab_marcas()
    if len(nombre) > 120:
        messages.error(request, "El nombre es demasiado largo.")
        return redirect_inventario_tab_marcas()
    if nombre in PRODUCTO_MARCAS_ALTA_WEB:
        messages.info(request, "Esa marca ya está disponible en el sistema.")
        return redirect_inventario_tab_marcas()
    if ProductoCatalogoExtra.objects.filter(
        tipo=ProductoCatalogoExtra.Tipo.MARCA, nombre__iexact=nombre
    ).exists():
        messages.warning(request, "Esa marca ya fue registrada.")
        return redirect_inventario_tab_marcas()
    try:
        ProductoCatalogoExtra.objects.create(tipo=ProductoCatalogoExtra.Tipo.MARCA, nombre=nombre)
    except IntegrityError:
        messages.warning(request, "Esa marca ya existe.")
        return redirect_inventario_tab_marcas()
    messages.success(request, f"Marca «{nombre}» agregada. Ya puedes usarla al crear productos.")
    return redirect_inventario_tab_marcas()


@admin_login_required
def admin_proveedores(request):
    usuario = admin_usuario_sesion(request)
    busqueda = (request.GET.get("busqueda") or "").strip()
    qs = Proveedor.objects.all().order_by("id")
    if busqueda:
        qs = qs.filter(
            Q(nombre__icontains=busqueda)
            | Q(identificacion__icontains=busqueda)
            | Q(correo_electronico__icontains=busqueda)
            | Q(empresa__icontains=busqueda)
        )
    proveedores = list(qs)
    proveedores_json = json.dumps(
        [proveedor_modal_dict(p) for p in proveedores],
        ensure_ascii=False,
    )
    ctx = {
        "usuario": usuario,
        "proveedores": proveedores,
        "proveedores_json": mark_safe(proveedores_json),
        "busqueda": busqueda,
        "total_proveedores": Proveedor.objects.count(),
        "total_activos": Proveedor.objects.filter(activo=True).count(),
        "total_inactivos": Proveedor.objects.filter(activo=False).count(),
    }
    return render(request, "frontend/admin/proveedores.html", ctx)


@admin_login_required
@require_http_methods(["POST"])
def admin_proveedor_crear(request):
    admin_usuario_sesion(request)

    identificacion = (request.POST.get("identificacion") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    correo = (request.POST.get("correo_electronico") or "").strip().lower()
    empresa = (request.POST.get("empresa") or "").strip()

    if not identificacion or len(identificacion) > 50:
        messages.error(request, "La identificación es obligatoria (máximo 50 caracteres).")
        return redirect("web_admin_proveedores")
    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_proveedores")
    digitos_tel = sum(1 for c in telefono if c.isdigit())
    if (
        not telefono
        or len(telefono) > 20
        or not TELEFONO_PROV_RE.match(telefono)
        or digitos_tel < 7
    ):
        messages.error(
            request,
            "El teléfono es obligatorio: al menos 7 dígitos, máximo 20 caracteres totales "
            "(puedes usar espacios, +, - o paréntesis).",
        )
        return redirect("web_admin_proveedores")
    if not EMAIL_ALTA_RE.match(correo):
        messages.error(request, "Ingresa un correo electrónico válido.")
        return redirect("web_admin_proveedores")
    if len(empresa) > 150:
        messages.error(request, "El nombre de empresa es demasiado largo (máx. 150).")
        return redirect("web_admin_proveedores")

    entidad = ProveedorEntidad(
        id=None,
        identificacion=identificacion,
        nombre=nombre,
        telefono=telefono,
        correo_electronico=correo,
        empresa=empresa,
        activo=True,
    )
    service = get_proveedor_service()
    try:
        creado = service.crear(entidad)
    except IntegrityError:
        messages.error(
            request,
            "Ya existe un proveedor con esa identificación o ese correo electrónico.",
        )
        return redirect("web_admin_proveedores")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_proveedores")

    messages.success(request, f"Proveedor «{creado.nombre}» creado correctamente.")
    return redirect("web_admin_proveedores")


@admin_login_required
@require_http_methods(["POST"])
def admin_proveedor_estado(request, proveedor_id: int):
    admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    p = get_object_or_404(Proveedor, pk=proveedor_id)
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Proveedor activado correctamente." if activar else "Proveedor desactivado correctamente.",
    )
    return redirect("web_admin_proveedores")


@admin_login_required
def admin_pagos(request):
    """Listado de pagos con filtros (equivalente a /admin/pagos en Spring)."""
    usuario = admin_usuario_sesion(request)
    estado = (request.GET.get("estado") or "").strip()
    fecha_desde = parse_date_param(request.GET.get("fechaDesde"))
    fecha_hasta = parse_date_param(request.GET.get("fechaHasta"))
    busqueda = (request.GET.get("busqueda") or "").strip()
    orden = (request.GET.get("orden") or "reciente").strip().lower()

    todos = Pago.objects.all()
    total_pagos = todos.count()
    agg = todos.aggregate(s=Sum("monto"))
    total_monto = agg["s"] or Decimal("0")
    pagos_confirmados = todos.filter(estado_pago=Pago.EstadoPago.APROBADO).count()

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    agg_mes = todos.filter(fecha_pago__gte=inicio_mes, fecha_pago__lte=hoy).aggregate(
        s=Sum("monto")
    )
    monto_este_mes = agg_mes["s"] or Decimal("0")

    qs = Pago.objects.prefetch_related(
        Prefetch(
            "medios_pago",
            queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
        )
    ).order_by("-fecha_pago", "-id")
    qs = filtrar_queryset_pagos_por_estado_get(qs, estado or None)
    if fecha_desde:
        qs = qs.filter(fecha_pago__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pago__lte=fecha_hasta)

    rows = []
    for pago in qs:
        venta, cliente = venta_cliente_desde_pago(pago)
        rows.append(
            {
                "pago": pago,
                "venta": venta,
                "cliente": cliente,
                "badge": badge_clase_estado_pago(pago.estado_pago),
            }
        )

    if busqueda:
        q_lower = busqueda.lower()

        def _match(r: dict) -> bool:
            p = r["pago"]
            if p.numero_factura and q_lower in p.numero_factura.lower():
                return True
            c = r["cliente"]
            if c:
                nombre = f"{c.nombres} {c.apellidos}".strip().lower()
                if q_lower in nombre or q_lower in (c.correo_electronico or "").lower():
                    return True
            return False

        rows = [r for r in rows if _match(r)]

    rows = [r for r in rows if r["venta"] is not None]

    if orden == "antiguo":
        rows.sort(key=lambda r: (r["pago"].fecha_pago, r["pago"].id))
    else:
        rows.sort(key=lambda r: (r["pago"].fecha_pago, r["pago"].id), reverse=True)

    ctx = {
        "usuario": usuario,
        "rows": rows,
        "estado": estado,
        "fecha_desde": request.GET.get("fechaDesde") or "",
        "fecha_hasta": request.GET.get("fechaHasta") or "",
        "busqueda": busqueda,
        "orden": orden,
        "total_pagos": total_pagos,
        "total_monto": total_monto,
        "pagos_confirmados": pagos_confirmados,
        "monto_este_mes": monto_este_mes,
    }
    return render(request, "frontend/admin/pagos.html", ctx)


@admin_login_required
def admin_pago_detalle(request, pago_id: int):
    usuario = admin_usuario_sesion(request)
    pago = get_object_or_404(
        Pago.objects.prefetch_related(
            Prefetch(
                "medios_pago",
                queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
            )
        ),
        pk=pago_id,
    )
    venta, cliente = venta_cliente_desde_pago(pago)
    if venta is None:
        messages.error(request, "No se encontró la venta asociada a este pago.")
        return redirect("web_admin_pagos")
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in venta.detalles.select_related("producto").all()
    ]
    badge = badge_clase_estado_pago(pago.estado_pago)
    medios_pago_labels = lista_metodos_pago_display(pago)
    return render(
        request,
        "frontend/admin/pago_detalle.html",
        {
            "usuario": usuario,
            "pago": pago,
            "venta": venta,
            "cliente": cliente,
            "lineas": lineas,
            "badge": badge,
            "medios_pago_labels": medios_pago_labels,
            "fecha_pago_es": fecha_larga_es(pago.fecha_pago),
            "fecha_factura_es": fecha_larga_es(pago.fecha_factura),
        },
    )


@admin_login_required
def admin_pago_factura(request, pago_id: int):
    usuario = admin_usuario_sesion(request)
    pago = get_object_or_404(
        Pago.objects.prefetch_related(
            Prefetch(
                "medios_pago",
                queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
            )
        ),
        pk=pago_id,
    )
    venta, cliente = venta_cliente_desde_pago(pago)
    if venta is None:
        messages.error(request, "No se encontró la venta para generar la factura.")
        return redirect("web_admin_pagos")
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in venta.detalles.select_related("producto").all()
    ]
    return render(
        request,
        "frontend/admin/factura_pago.html",
        {
            "usuario": usuario,
            "pago": pago,
            "venta": venta,
            "cliente": cliente,
            "lineas": lineas,
        },
    )


@admin_login_required
def admin_pedidos(request):
    """Listado de ventas / pedidos (panel admin, alineado a gestión de pedidos)."""
    usuario = admin_usuario_sesion(request)
    busqueda = (request.GET.get("busqueda") or "").strip()
    usuario_id = (request.GET.get("usuarioId") or "").strip()
    fecha_desde = (request.GET.get("fechaDesde") or "").strip()
    fecha_hasta = (request.GET.get("fechaHasta") or "").strip()
    producto = (request.GET.get("producto") or "").strip()
    qs = Venta.objects.select_related("usuario").order_by("-fecha_venta", "-id")
    if usuario_id.isdigit():
        qs = qs.filter(usuario_id=int(usuario_id))
    if fecha_desde:
        try:
            f_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            qs = qs.filter(fecha_venta__gte=f_desde)
        except ValueError:
            fecha_desde = ""
    if fecha_hasta:
        try:
            f_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            qs = qs.filter(fecha_venta__lte=f_hasta)
        except ValueError:
            fecha_hasta = ""
    if producto:
        qs = qs.filter(detalles__producto__nombre__icontains=producto).distinct()
    if busqueda:
        if busqueda.isdigit():
            qs = qs.filter(id=int(busqueda))
        else:
            qs = qs.filter(
                Q(usuario__nombres__icontains=busqueda)
                | Q(usuario__apellidos__icontains=busqueda)
                | Q(usuario__correo_electronico__icontains=busqueda)
            )
    ventas = list(qs[:800])
    usuarios_filtro = list(
        Usuario.objects.filter(ventas__isnull=False)
        .distinct()
        .order_by("nombres", "apellidos")
        .values("id", "nombres", "apellidos", "correo_electronico")
    )
    hoy = timezone.localdate()
    total_pedidos = Venta.objects.count()
    agg_monto = Venta.objects.aggregate(s=Sum("total"))
    total_ventas_monto = agg_monto["s"] if agg_monto["s"] is not None else Decimal("0")
    pedidos_este_mes = Venta.objects.filter(
        fecha_venta__year=hoy.year,
        fecha_venta__month=hoy.month,
    ).count()
    return render(
        request,
        "frontend/admin/pedidos.html",
        {
            "usuario": usuario,
            "ventas": ventas,
            "busqueda": busqueda,
            "usuarios_filtro": usuarios_filtro,
            "usuario_id": usuario_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "producto": producto,
            "total_pedidos": total_pedidos,
            "total_ventas_monto": total_ventas_monto,
            "pedidos_este_mes": pedidos_este_mes,
        },
    )


@admin_login_required
def admin_pedido_detalle(request, venta_id: int):
    usuario = admin_usuario_sesion(request)
    venta = get_object_or_404(Venta.objects.select_related("usuario"), pk=venta_id)
    detalles = venta.detalles.select_related("producto").all()
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in detalles
    ]
    envio = (
        Envio.objects.filter(venta_id=venta.id, activo=True)
        .select_related("transportadora")
        .order_by("-id")
        .first()
    )
    pago = Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id).distinct().first()
    medio_pago = None
    if pago:
        medio_pago = (
            MedioPago.objects.filter(pago=pago, detalle_venta__venta_id=venta.id)
            .order_by("id")
            .first()
        )
    medio_pago_etiqueta = etiqueta_medio_pago_mostrar(medio_pago) if medio_pago else ""
    return render(
        request,
        "frontend/admin/pedido_detalle.html",
        {
            "usuario": usuario,
            "venta": venta,
            "cliente": venta.usuario,
            "lineas": lineas,
            "envio": envio,
            "pago": pago,
            "medio_pago": medio_pago,
            "medio_pago_etiqueta": medio_pago_etiqueta,
        },
    )
