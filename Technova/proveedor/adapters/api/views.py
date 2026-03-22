from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_proveedor_service
from proveedor.domain.entities import ProveedorEntidad


def _serialize(entidad: ProveedorEntidad) -> dict:
    return {
        "id": entidad.id,
        "identificacion": entidad.identificacion,
        "nombre": entidad.nombre,
        "telefono": entidad.telefono,
        "correo": entidad.correo_electronico,
        "empresa": entidad.empresa,
        "estado": entidad.activo,
    }


def _entidad_desde_payload(payload: dict, *, proveedor_id: int | None = None) -> ProveedorEntidad:
    return ProveedorEntidad(
        id=proveedor_id,
        identificacion=str(payload["identificacion"]).strip(),
        nombre=str(payload["nombre"]).strip(),
        telefono=str(payload["telefono"]).strip(),
        correo_electronico=str(payload.get("correo") or payload.get("correo_electronico", "")).strip().lower(),
        empresa=str(payload.get("empresa", "") or ""),
        activo=bool(payload.get("estado", payload.get("activo", True))),
    )


def _listar_core(request):
    service = get_proveedor_service()
    items = service.listar_todos()
    return success_response({"items": [_serialize(p) for p in items]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth()
def catalogo_proveedores(request):
    if request.method == "GET":
        return _listar_core(request)
    if request.usuario_actual.rol not in ("admin", "empleado"):
        return error_response("No tienes permisos para esta operacion.", status=403)
    try:
        payload = parse_json_body(request)
        entidad = _entidad_desde_payload(payload)
    except (KeyError, ValueError, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_proveedor_service()
    try:
        creado = service.crear(entidad)
    except Exception as exc:  # noqa: BLE001
        return error_response(str(exc), status=400)
    return success_response(_serialize(creado), status=201)


def _detalle_core(request, proveedor_id: int):
    service = get_proveedor_service()
    p = service.obtener_por_id(proveedor_id)
    if p is None:
        return error_response("Proveedor no encontrado.", status=404)
    return success_response(_serialize(p))


def _actualizar_core(request, proveedor_id: int):
    try:
        payload = parse_json_body(request)
        entidad = _entidad_desde_payload(payload, proveedor_id=proveedor_id)
    except (KeyError, ValueError, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_proveedor_service()
    actualizado = service.actualizar(entidad)
    if actualizado is None:
        return error_response("Proveedor no encontrado.", status=404)
    return success_response(_serialize(actualizado))


def _eliminar_core(request, proveedor_id: int):
    service = get_proveedor_service()
    if not service.eliminar(proveedor_id):
        return error_response("Proveedor no encontrado.", status=404)
    return success_response({}, message="Proveedor desactivado")


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@require_auth()
def proveedor_por_id(request, proveedor_id: int):
    if request.method == "GET":
        return _detalle_core(request, proveedor_id)
    if request.usuario_actual.rol not in ("admin", "empleado"):
        return error_response("No tienes permisos para esta operacion.", status=403)
    if request.method == "PUT":
        return _actualizar_core(request, proveedor_id)
    return _eliminar_core(request, proveedor_id)


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth()
def patch_estado_proveedor(request, proveedor_id: int):
    if request.usuario_actual.rol not in ("admin", "empleado"):
        return error_response("No tienes permisos para esta operacion.", status=403)
    try:
        payload = parse_json_body(request)
        if "activar" not in payload:
            return error_response("Campo activar requerido.", status=400)
        activar = bool(payload["activar"])
    except (ValueError, TypeError) as exc:
        return error_response(str(exc), status=400)
    service = get_proveedor_service()
    actualizado = service.cambiar_estado(proveedor_id, activar)
    if actualizado is None:
        return error_response("Proveedor no encontrado.", status=404)
    return success_response(_serialize(actualizado))


@require_GET
@require_auth()
def listar_proveedores(request):
    return _listar_core(request)
