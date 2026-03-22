from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import (
    get_carrito_lineas_service,
    get_carrito_query_service,
    get_carrito_service,
)
from carrito.domain.entities import CarritoEntidad, ItemCarritoEntidad


def _forbidden_si_otro_usuario(request, usuario_id: int):
    if request.usuario_actual.rol != "admin" and usuario_id != request.usuario_actual.id:
        return error_response("No puedes operar el carrito de otro usuario.", status=403)
    return None


@require_GET
@require_auth()
def listar_carritos(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_carrito_query_service()
    return success_response({"items": query_service.listar_carritos(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_carrito(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes crear carritos para otro usuario.", status=403)

    items = [
        ItemCarritoEntidad(
            producto_id=item["producto_id"],
            cantidad=item["cantidad"],
        )
        for item in payload.get("items", [])
    ]
    fecha_creacion = payload.get("fecha_creacion")
    carrito = CarritoEntidad(
        id=None,
        usuario_id=usuario_objetivo_id,
        fecha_creacion=datetime.fromisoformat(fecha_creacion) if fecha_creacion else datetime.now(),
        estado=payload.get("estado", "activo"),
        items=items,
    )
    service = get_carrito_service()
    try:
        guardado = service.crear_carrito(carrito)
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)

    return success_response({"id": guardado.id, "estado": guardado.estado}, status=201)


@require_GET
@require_auth()
def listar_favoritos(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_carrito_query_service()
    return success_response({"items": query_service.listar_favoritos(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_favorito(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes crear favoritos para otro usuario.", status=403)

    try:
        favorito_id = get_carrito_query_service().crear_favorito(
            usuario_id=usuario_objetivo_id,
            producto_id=payload["producto_id"],
        )
    except (KeyError, ValueError) as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": favorito_id}, status=201)


@require_GET
@require_auth()
def items_carrito_por_usuario(request, usuario_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    service = get_carrito_lineas_service()
    return success_response({"items": service.listar_items(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def agregar_item_carrito(request, usuario_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    try:
        if request.GET.get("productoId") or request.GET.get("producto_id"):
            producto_id = int(request.GET.get("productoId") or request.GET.get("producto_id"))
            cantidad = int(request.GET.get("cantidad") or 1)
        else:
            payload = parse_json_body(request)
            producto_id = int(payload["producto_id"])
            cantidad = int(payload.get("cantidad", 1))
    except (KeyError, ValueError, TypeError) as exc:
        return error_response(f"Dato invalido: {exc}", status=400)

    service = get_carrito_lineas_service()
    try:
        items = service.agregar_producto(usuario_id, producto_id, cantidad)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth()
def actualizar_item_carrito(request, usuario_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    try:
        if request.GET.get("detalleId") or request.GET.get("detalle_id"):
            detalle_id = int(request.GET.get("detalleId") or request.GET.get("detalle_id"))
            cantidad = int(request.GET.get("cantidad") or 1)
        else:
            payload = parse_json_body(request)
            detalle_id = int(payload["detalle_id"])
            cantidad = int(payload.get("cantidad", 1))
    except (KeyError, ValueError, TypeError) as exc:
        return error_response(f"Dato invalido: {exc}", status=400)

    service = get_carrito_lineas_service()
    try:
        items = service.actualizar_cantidad(usuario_id, detalle_id, cantidad)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth()
def eliminar_item_carrito(request, usuario_id: int, detalle_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    service = get_carrito_lineas_service()
    try:
        items = service.eliminar_detalle(usuario_id, detalle_id)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth()
def vaciar_carrito_usuario(request, usuario_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    get_carrito_lineas_service().vaciar(usuario_id)
    return success_response({}, message="Carrito vaciado")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth()
def eliminar_favorito_usuario_producto(request, usuario_id: int, producto_id: int):
    if request.usuario_actual.rol != "admin" and usuario_id != request.usuario_actual.id:
        return error_response("No puedes modificar favoritos de otro usuario.", status=403)
    eliminado = get_carrito_query_service().eliminar_favorito(usuario_id, producto_id)
    if not eliminado:
        return error_response("Favorito no encontrado.", status=404)
    return success_response({}, message="Favorito eliminado")
