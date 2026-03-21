from datetime import date
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from pagos.application.payment_state_service import PagoStateService
from pagos.application.services import PagoService
from pagos.domain.entities import PagoEntidad
from pagos.infrastructure.repositories import PagoOrmRepository
from pagos.models import MetodoPagoUsuario, Pago


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_pagos(request):
    queryset = Pago.objects.order_by("-id")
    return success_response(
        {
            "items": [
                {
                    "id": pago.id,
                    "numero_factura": pago.numero_factura,
                    "fecha_factura": pago.fecha_factura.isoformat(),
                    "fecha_pago": pago.fecha_pago.isoformat(),
                    "monto": str(pago.monto),
                    "estado_pago": pago.estado_pago,
                }
                for pago in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_pago(request):
    try:
        payload = parse_json_body(request)
        pago = PagoEntidad(
            id=None,
            fecha_pago=date.fromisoformat(payload["fecha_pago"]),
            numero_factura=payload["numero_factura"],
            fecha_factura=date.fromisoformat(payload["fecha_factura"]),
            monto=Decimal(str(payload["monto"])),
            estado_pago=payload.get("estado_pago", "pendiente"),
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    service = PagoService(PagoOrmRepository())
    try:
        guardado = service.registrar_pago(pago)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    return success_response({"id": guardado.id, "estado_pago": guardado.estado_pago}, status=201)


@require_GET
@require_auth()
def listar_metodos_usuario(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    queryset = MetodoPagoUsuario.objects.order_by("-id")
    if usuario_id:
        queryset = queryset.filter(usuario_id=usuario_id)
    return success_response(
        {
            "items": [
                {
                    "id": metodo.id,
                    "usuario_id": metodo.usuario_id,
                    "metodo_pago": metodo.metodo_pago,
                    "es_predeterminado": metodo.es_predeterminado,
                    "marca": metodo.marca,
                    "ultimos_cuatro": metodo.ultimos_cuatro,
                }
                for metodo in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth()
def crear_metodo_usuario(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes registrar metodos de pago para otro usuario.", status=403)

    try:
        metodo = MetodoPagoUsuario.objects.create(
            usuario_id=usuario_objetivo_id,
            metodo_pago=payload["metodo_pago"],
            es_predeterminado=payload.get("es_predeterminado", False),
            marca=payload.get("marca", ""),
            ultimos_cuatro=payload.get("ultimos_cuatro", ""),
            nombre_titular=payload.get("nombre_titular", ""),
            token=payload.get("token", ""),
            mes_expiracion=payload.get("mes_expiracion", ""),
            anio_expiracion=payload.get("anio_expiracion", ""),
            correo=payload.get("correo", ""),
            telefono=payload.get("telefono", ""),
            cuotas=payload.get("cuotas"),
        )
    except KeyError as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": metodo.id}, status=201)


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def actualizar_estado_pago(request, pago_id: int):
    try:
        payload = parse_json_body(request)
        nuevo_estado = payload["estado_pago"]
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)

    service = PagoStateService()
    try:
        pago = service.actualizar_estado(pago_id=pago_id, nuevo_estado=nuevo_estado)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    return success_response(
        {
            "id": pago.id,
            "estado_pago": pago.estado_pago,
            "fecha_pago": pago.fecha_pago.isoformat(),
        },
        message="Estado de pago actualizado",
    )
