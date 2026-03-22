from datetime import datetime
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_compra_service
from compra.domain.entities import CompraEntidad, ItemCompraEntidad
from compra.models import Compra


def _serialize_compra(c: CompraEntidad) -> dict:
    return {
        "id": c.id,
        "usuario_id": c.usuario_id,
        "proveedor_id": c.proveedor_id,
        "fecha_compra": c.fecha_compra.isoformat(),
        "total": str(c.total),
        "estado": c.estado,
        "items": [
            {
                "producto_id": i.producto_id,
                "cantidad": i.cantidad,
                "precio_unitario": str(i.precio_unitario),
            }
            for i in c.items
        ],
    }


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_compras(request):
    items = get_compra_service().listar_todas()
    return success_response({"items": [_serialize_compra(c) for c in items]})


@require_GET
@require_auth()
def mis_compras(request):
    items = get_compra_service().listar_por_usuario(request.usuario_actual.id)
    return success_response({"items": [_serialize_compra(c) for c in items]})


@require_GET
@require_auth()
def detalle_compra(request, compra_id: int):
    compra = get_compra_service().obtener_por_id(compra_id)
    if compra is None:
        return error_response("Compra no encontrada.", status=404)
    u = request.usuario_actual
    if u.rol not in ("admin", "empleado") and compra.usuario_id != u.id:
        return error_response("No tienes permisos para ver esta compra.", status=403)
    return success_response(_serialize_compra(compra))


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth(roles=["admin", "empleado"])
def actualizar_estado_compra(request, compra_id: int):
    try:
        body = parse_json_body(request)
        estado = str(body.get("estado", "")).strip()
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not estado:
        return error_response("Campo estado requerido.", status=400)
    try:
        ok = get_compra_service().cambiar_estado(compra_id, estado)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not ok:
        return error_response("Compra no encontrada.", status=404)
    return success_response({}, message="Estado actualizado")


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_compra(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes registrar compras para otro usuario.", status=403)

    items = [
        ItemCompraEntidad(
            producto_id=item["producto_id"],
            cantidad=item["cantidad"],
            precio_unitario=Decimal(str(item["precio_unitario"])),
        )
        for item in payload.get("items", [])
    ]
    estado_raw = payload.get("estado", Compra.Estado.REGISTRADA)
    estados_validos = {c[0] for c in Compra.Estado.choices}
    if estado_raw not in estados_validos:
        return error_response(f"Estado invalido. Use uno de: {', '.join(sorted(estados_validos))}", status=400)
    compra = CompraEntidad(
        id=None,
        usuario_id=usuario_objetivo_id,
        proveedor_id=payload["proveedor_id"],
        fecha_compra=datetime.fromisoformat(payload["fecha_compra"]),
        total=Decimal("0"),
        estado=estado_raw,
        items=items,
    )
    service = get_compra_service()
    try:
        compra_guardada = service.registrar_compra(compra)
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    return success_response(
        {
            "id": compra_guardada.id,
            "total": str(compra_guardada.total),
            "estado": compra_guardada.estado,
        },
        status=201,
        message="Compra registrada",
    )
