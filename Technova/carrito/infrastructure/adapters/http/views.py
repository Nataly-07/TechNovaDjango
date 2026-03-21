from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_carrito_query_service, get_carrito_service
from carrito.domain.entities import CarritoEntidad, ItemCarritoEntidad


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
