"""Vistas REST para favoritos (/api/favoritos)."""
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, success_response
from common.auth import require_auth
from common.container import get_carrito_query_service


def _forbidden_si_otro_usuario(request, usuario_id: int):
    if request.usuario_actual.rol != "admin" and usuario_id != request.usuario_actual.id:
        return error_response("No puedes operar favoritos de otro usuario.", status=403)
    return None


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_todos_favoritos(request):
    items = get_carrito_query_service().listar_favoritos_todos_dto()
    return success_response({"items": items})


@require_GET
@require_auth()
def listar_favoritos_por_usuario(request, usuario_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    items = get_carrito_query_service().listar_favoritos_usuario_dto(usuario_id)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
@require_auth()
def favorito_usuario_producto(request, usuario_id: int, producto_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    svc = get_carrito_query_service()
    if request.method == "POST":
        return success_response(svc.agregar_favorito_dto(usuario_id, producto_id))
    dto = svc.quitar_favorito_dto(usuario_id, producto_id)
    if dto is None:
        return error_response("Favorito no encontrado.", status=404)
    return success_response(dto)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth()
def toggle_favorito(request, usuario_id: int, producto_id: int):
    err = _forbidden_si_otro_usuario(request, usuario_id)
    if err:
        return err
    resultado = get_carrito_query_service().toggle_favorito(usuario_id, producto_id)
    return success_response({"resultado": resultado})
