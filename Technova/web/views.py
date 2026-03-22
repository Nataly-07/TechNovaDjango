import json
import re
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils.safestring import mark_safe

from common.container import get_producto_service
from compra.models import Compra, DetalleCompra
from mensajeria.models import MensajeDirecto
from pago.models import Pago
from producto.domain.entities import ProductoEntidad
from producto.models import Producto
from proveedor.models import Proveedor
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta


def _cliente_login_required(view_func):
    """Solo usuarios con sesión Django (misma clave que login_web)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(SESSION_USUARIO_ID):
            return redirect("web_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _admin_login_required(view_func):
    """Sesión activa y rol administrador."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get(SESSION_USUARIO_ID)
        if not uid:
            return redirect("web_login")
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect("web_login")
        if usuario.rol != Usuario.Rol.ADMIN:
            return redirect("inicio_autenticado")
        return view_func(request, *args, **kwargs)

    return _wrapped


def root_entry(request):
    """Raíz `/`: con sesión → inicio o perfil admin; sin sesión → login."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if uid:
        try:
            u = Usuario.objects.get(pk=uid)
            if u.rol == Usuario.Rol.ADMIN:
                return redirect("web_admin_perfil")
        except Usuario.DoesNotExist:
            pass
        return redirect("inicio_autenticado")
    return redirect("web_login")


@_cliente_login_required
def home(request):
    """Inicio autenticado / catálogo (`/inicio/`)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if uid:
        try:
            u = Usuario.objects.get(pk=uid)
            if u.rol == Usuario.Rol.ADMIN:
                return redirect("web_admin_perfil")
        except Usuario.DoesNotExist:
            pass
    return render(request, "frontend/cliente/home.html")


@_admin_login_required
def perfil_admin(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    mensajes_pendientes = MensajeDirecto.objects.exclude(
        estado=MensajeDirecto.Estado.RESPONDIDO
    ).count()
    ctx = {
        "usuario": usuario,
        "users_count": Usuario.objects.count(),
        "productos_count": Producto.objects.filter(activo=True).count(),
        "proveedores_count": Proveedor.objects.filter(activo=True).count(),
        "reportes_disponibles": 3,
        "mensajes_pendientes": mensajes_pendientes,
        "pedidos_procesados": Venta.objects.count(),
        "transacciones_procesadas": Pago.objects.count(),
    }
    return render(request, "frontend/admin/perfil.html", ctx)


def _admin_usuario_sesion(request) -> Usuario:
    uid = request.session.get(SESSION_USUARIO_ID)
    return get_object_or_404(Usuario, pk=uid)


def _usuario_modal_dict(u: Usuario) -> dict:
    ventas_preview: list[dict] = []
    if u.rol == Usuario.Rol.CLIENTE:
        ventas_preview = [
            {
                "id": v.id,
                "fecha": v.fecha_venta.isoformat(),
                "total": str(v.total),
                "estado": v.estado,
            }
            for v in Venta.objects.filter(usuario=u).order_by("-fecha_venta")[:12]
        ]
    return {
        "id": u.id,
        "name": f"{u.nombres} {u.apellidos}".strip(),
        "firstName": u.nombres,
        "lastName": u.apellidos,
        "email": u.correo_electronico,
        "role": u.rol,
        "estado": u.activo,
        "documentType": u.tipo_documento,
        "documentNumber": u.numero_documento,
        "phone": u.telefono,
        "address": u.direccion,
        "ventas_preview": ventas_preview,
    }


def _producto_modal_dict(p: Producto) -> dict:
    precio = p.precio_venta if p.precio_venta is not None else p.costo_unitario
    return {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "stock": p.stock,
        "estado": p.activo,
        "imagen": p.imagen_url or "",
        "proveedor": p.proveedor.nombre if p.proveedor_id else "",
        "caracteristica": {
            "categoria": p.categoria,
            "marca": p.marca,
            "descripcion": p.descripcion,
            "precioCompra": str(p.costo_unitario),
            "precioVenta": str(precio) if precio is not None else None,
        },
    }


@_admin_login_required
def admin_usuarios(request):
    usuario = _admin_usuario_sesion(request)
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
        [_usuario_modal_dict(u) for u in usuarios],
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


_NOMBRE_PERSONA_RE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,}$")
_EMAIL_ALTA_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validar_nombre_persona(val: str) -> bool:
    val = (val or "").strip()
    if len(val) < 2:
        return False
    return bool(_NOMBRE_PERSONA_RE.match(val))


@_admin_login_required
@require_http_methods(["POST"])
def admin_usuario_crear(request):
    """Alta de administrador o empleado (misma regla que API + registro_usuario_service)."""
    admin = _admin_usuario_sesion(request)
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

    if not _validar_nombre_persona(first_name):
        messages.error(
            request,
            "El primer nombre debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not _validar_nombre_persona(last_name):
        messages.error(
            request,
            "El apellido debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not _EMAIL_ALTA_RE.match(email):
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


@_admin_login_required
@require_http_methods(["POST"])
def admin_usuario_estado(request, usuario_id: int):
    _admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    u = get_object_or_404(Usuario, pk=usuario_id)
    u.activo = activar
    u.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Usuario activado correctamente." if activar else "Usuario desactivado correctamente.",
    )
    return redirect("web_admin_usuarios")


@_admin_login_required
def admin_inventario(request):
    usuario = _admin_usuario_sesion(request)
    categoria = (request.GET.get("categoria") or "").strip()
    busqueda = (request.GET.get("busqueda") or "").strip()

    qs = Producto.objects.select_related("proveedor").order_by("id")
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)
    if busqueda:
        qs = qs.filter(Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda))

    productos = list(qs)
    productos_json = json.dumps(
        [_producto_modal_dict(p) for p in productos],
        ensure_ascii=False,
    )

    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(activo=True, stock__gt=0, stock__lt=10).count()
    productos_agotados = Producto.objects.filter(activo=True, stock=0).count()

    categorias_opts = (
        Producto.objects.exclude(categoria="")
        .values_list("categoria", flat=True)
        .distinct()
        .order_by("categoria")
    )

    categorias_info = [
        {"nombre": row["categoria"], "cantidad": row["cantidad"]}
        for row in (
            Producto.objects.exclude(categoria="")
            .values("categoria")
            .annotate(cantidad=Count("id"))
            .order_by("categoria")
        )
    ]
    marcas_info = [
        {"nombre": row["marca"], "cantidad": row["cantidad"]}
        for row in (
            Producto.objects.exclude(marca="")
            .values("marca")
            .annotate(cantidad=Count("id"))
            .order_by("marca")
        )
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
    }
    return render(request, "frontend/admin/inventario.html", ctx)


def _decimal_desde_post(val: str | None) -> Decimal | None:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


@_admin_login_required
@require_http_methods(["POST"])
def admin_producto_crear(request):
    """Alta de producto vía caso de uso (misma regla que API JSON)."""
    _admin_usuario_sesion(request)

    codigo = (request.POST.get("codigo") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()
    marca = (request.POST.get("marca") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    imagen_url = (request.POST.get("imagen_url") or "").strip()

    if not codigo or len(codigo) > 50:
        messages.error(request, "El código es obligatorio (máximo 50 caracteres).")
        return redirect("web_admin_inventario")
    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_inventario")
    if not categoria or len(categoria) > 120:
        messages.error(request, "La categoría es obligatoria.")
        return redirect("web_admin_inventario")
    if not marca or len(marca) > 120:
        messages.error(request, "La marca es obligatoria.")
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

    costo = _decimal_desde_post(request.POST.get("costo_unitario"))
    if costo is None or costo < 0:
        messages.error(request, "El costo unitario debe ser un número mayor o igual a 0.")
        return redirect("web_admin_inventario")

    precio = _decimal_desde_post(request.POST.get("precio_venta"))
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
        descripcion=descripcion,
        precio_venta=precio,
    )
    service = get_producto_service()
    try:
        creado = service.crear(entidad)
    except IntegrityError:
        messages.error(request, "Ya existe un producto con ese código.")
        return redirect("web_admin_inventario")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_inventario")

    messages.success(request, f"Producto «{creado.nombre}» creado correctamente.")
    return redirect("web_admin_inventario")


@_admin_login_required
@require_http_methods(["POST"])
def admin_producto_estado(request, producto_id: int):
    _admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    p = get_object_or_404(Producto, pk=producto_id)
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Producto activado correctamente." if activar else "Producto desactivado correctamente.",
    )
    return redirect("web_admin_inventario")


@_cliente_login_required
def perfil_cliente(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = None
    if uid:
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            usuario = None
    ctx = {
        "usuario": usuario,
        "favoritos_count": 0,
        "carrito_count": 0,
        "pedidos_count": 0,
        "notificaciones_count": 0,
        "medios_pago_count": 0,
        "compras_count": 0,
    }
    return render(request, "frontend/cliente/perfil.html", ctx)


@_cliente_login_required
def perfil_editar(request):
    """Equivalente a GET/POST /perfil/edit del Java (teléfono, dirección + contraseña actual)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    try:
        usuario = Usuario.objects.get(pk=uid) if uid else None
    except Usuario.DoesNotExist:
        usuario = None
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("web_cliente_perfil")

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        direccion = (request.POST.get("direccion") or "").strip()
        current_password = request.POST.get("current_password") or ""
        if not credenciales_coinciden(current_password, usuario.contrasena_hash):
            messages.error(request, "La contraseña actual no es correcta.")
            return redirect("web_cliente_perfil_editar")
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.save(update_fields=["telefono", "direccion", "actualizado_en"])
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("web_cliente_perfil")

    return render(request, "frontend/cliente/perfil_editar.html", {"usuario": usuario})


@require_http_methods(["POST"])
def perfil_desactivar(request):
    """Equivalente a POST /cliente/perfil/desactivar del Java (JSON)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return JsonResponse({"success": False, "message": "No autenticado."}, status=401)
    try:
        usuario = Usuario.objects.get(pk=uid)
        usuario.activo = False
        usuario.save(update_fields=["activo", "actualizado_en"])
    except Usuario.DoesNotExist:
        return JsonResponse({"success": False, "message": "Usuario no encontrado."}, status=404)
    request.session.flush()
    return JsonResponse({"success": True, "message": "Cuenta desactivada."})


@_cliente_login_required
def favoritos_page(request):
    return render(request, "frontend/cliente/favoritos.html")


@_cliente_login_required
def notificaciones_cliente(request):
    return render(request, "frontend/cliente/notificaciones.html")


@_cliente_login_required
def carrito_page(request):
    return render(request, "frontend/cliente/carrito.html")


@_cliente_login_required
def pedidos_cliente(request):
    """Pedidos = ventas del usuario (ruta Java: /cliente/pedidos)."""
    return render(request, "frontend/cliente/pedidos.html")


@_cliente_login_required
def mis_compras(request):
    return render(request, "frontend/cliente/mis_compras.html")


@_cliente_login_required
def atencion_cliente(request):
    return render(request, "frontend/cliente/atencion.html")


@_cliente_login_required
def producto_detalle(request, producto_id: int):
    return render(request, "frontend/cliente/producto_detalle.html", {"producto_id": producto_id})
