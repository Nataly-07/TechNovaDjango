from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_producto_service
from producto.domain.entities import ProductoEntidad
from proveedor.models import Proveedor


def _nombre_proveedor(proveedor_id: int) -> str:
    try:
        p = Proveedor.objects.only("nombre").get(id=proveedor_id)
        return p.nombre
    except Proveedor.DoesNotExist:
        return ""


def _serialize_producto(entidad: ProductoEntidad) -> dict:
    precio = entidad.precio_venta if entidad.precio_venta is not None else entidad.costo_unitario
    return {
        "id": entidad.id,
        "codigo": entidad.codigo,
        "nombre": entidad.nombre,
        "stock": entidad.stock,
        "proveedor_id": entidad.proveedor_id,
        "proveedor": _nombre_proveedor(entidad.proveedor_id),
        "imagen": entidad.imagen_url or "",
        "estado": entidad.activo,
        "costo_unitario": str(entidad.costo_unitario),
        "precio_venta": str(entidad.precio_venta) if entidad.precio_venta is not None else None,
        "caracteristica": {
            "categoria": entidad.categoria,
            "marca": entidad.marca,
            "descripcion": entidad.descripcion,
            "precio_compra": str(entidad.costo_unitario),
            "precio_venta": str(precio),
        },
    }


def _entidad_desde_payload(payload: dict, *, producto_id: int | None = None) -> ProductoEntidad:
    precio_raw = payload.get("precio_venta")
    precio_venta = None
    if precio_raw is not None and precio_raw != "":
        precio_venta = Decimal(str(precio_raw))
    return ProductoEntidad(
        id=producto_id,
        codigo=str(payload["codigo"]).strip(),
        nombre=str(payload["nombre"]).strip(),
        proveedor_id=int(payload["proveedor_id"]),
        stock=int(payload.get("stock", 0)),
        costo_unitario=Decimal(str(payload.get("costo_unitario", "0"))),
        activo=bool(payload.get("activo", True)),
        imagen_url=str(payload.get("imagen_url", "") or payload.get("imagen", "") or ""),
        categoria=str(payload.get("categoria", "") or ""),
        marca=str(payload.get("marca", "") or ""),
        descripcion=str(payload.get("descripcion", "") or ""),
        precio_venta=precio_venta,
    )


def _listar_productos_core(request):
    service = get_producto_service()
    productos = service.listar_productos_activos()
    return success_response({"items": [_serialize_producto(p) for p in productos]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def catalogo_productos(request):
    if request.method == "GET":
        return _listar_productos_core(request)
    return require_auth(roles=["admin", "empleado"])(_crear_producto_core)(request)


def _crear_producto_core(request):
    try:
        payload = parse_json_body(request)
        entidad = _entidad_desde_payload(payload)
    except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_producto_service()
    try:
        creado = service.crear(entidad)
    except Exception as exc:  # noqa: BLE001
        return error_response(str(exc), status=400)
    return success_response(_serialize_producto(creado), status=201)


@require_GET
def listar_productos(request):
    return _listar_productos_core(request)


def _detalle_producto_core(request, producto_id: int):
    service = get_producto_service()
    producto = service.obtener_por_id(producto_id)
    if producto is None:
        return error_response("Producto no encontrado.", status=404)
    return success_response(_serialize_producto(producto))


def _actualizar_producto_core(request, producto_id: int):
    try:
        payload = parse_json_body(request)
        entidad = _entidad_desde_payload(payload, producto_id=producto_id)
    except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_producto_service()
    actualizado = service.actualizar(entidad)
    if actualizado is None:
        return error_response("Producto no encontrado.", status=404)
    return success_response(_serialize_producto(actualizado))


def _eliminar_producto_core(request, producto_id: int):
    service = get_producto_service()
    if not service.eliminar(producto_id):
        return error_response("Producto no encontrado.", status=404)
    return success_response({}, message="Producto desactivado", status=200)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def producto_por_id(request, producto_id: int):
    if request.method == "GET":
        return _detalle_producto_core(request, producto_id)
    auth = require_auth(roles=["admin", "empleado"])
    if request.method == "PUT":
        return auth(_actualizar_producto_core)(request, producto_id)
    return auth(_eliminar_producto_core)(request, producto_id)


@require_GET
def detalle_producto(request, producto_id: int):
    return _detalle_producto_core(request, producto_id)


@require_GET
def productos_por_categoria(request, categoria: str):
    service = get_producto_service()
    items = service.por_categoria(categoria)
    return success_response({"items": [_serialize_producto(p) for p in items]})


@require_GET
def productos_por_marca(request, marca: str):
    service = get_producto_service()
    items = service.por_marca(marca)
    return success_response({"items": [_serialize_producto(p) for p in items]})


@require_GET
def buscar_productos(request):
    termino = request.GET.get("termino", "")
    try:
        page = int(request.GET.get("page", "0"))
        size = int(request.GET.get("size", "10"))
    except ValueError:
        return error_response("page y size deben ser enteros.", status=400)
    service = get_producto_service()
    items, total = service.buscar_paginado(termino, page, size)
    return success_response(
        {
            "items": [_serialize_producto(p) for p in items],
            "total": total,
            "page": page,
            "size": size,
        }
    )


@require_GET
def productos_por_precio(request):
    try:
        min_p = Decimal(request.GET.get("min", "0"))
        max_p = Decimal(request.GET.get("max", "0"))
        page = int(request.GET.get("page", "0"))
        size = int(request.GET.get("size", "10"))
    except (InvalidOperation, ValueError):
        return error_response("Parametros min, max, page o size invalidos.", status=400)
    service = get_producto_service()
    items, total = service.por_rango_precio(min_p, max_p, page, size)
    return success_response(
        {
            "items": [_serialize_producto(p) for p in items],
            "total": total,
            "page": page,
            "size": size,
        }
    )


@require_GET
def buscar_productos_avanzado(request):
    def _decimal_opt(key: str) -> Decimal | None:
        raw = request.GET.get(key)
        if raw in (None, ""):
            return None
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None

    service = get_producto_service()
    items = service.buscar_avanzado(
        termino=request.GET.get("termino"),
        marca=request.GET.get("marca"),
        categoria=request.GET.get("categoria"),
        precio_min=_decimal_opt("precioMin") or _decimal_opt("precio_min"),
        precio_max=_decimal_opt("precioMax") or _decimal_opt("precio_max"),
        disponibilidad=request.GET.get("disponibilidad"),
    )
    return success_response({"items": [_serialize_producto(p) for p in items]})


@csrf_exempt
@require_http_methods(["POST"])
@require_auth(roles=["admin", "empleado"])
def crear_producto(request):
    return _crear_producto_core(request)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def actualizar_producto(request, producto_id: int):
    return _actualizar_producto_core(request, producto_id)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth(roles=["admin", "empleado"])
def eliminar_producto(request, producto_id: int):
    return _eliminar_producto_core(request, producto_id)


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth(roles=["admin", "empleado"])
def patch_estado_producto(request, producto_id: int):
    try:
        payload = parse_json_body(request)
        if "activar" not in payload:
            return error_response("Campo activar requerido.", status=400)
        activar = bool(payload["activar"])
    except (ValueError, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_producto_service()
    actualizado = service.cambiar_estado(producto_id, activar)
    if actualizado is None:
        return error_response("Producto no encontrado.", status=404)
    return success_response(_serialize_producto(actualizado))
