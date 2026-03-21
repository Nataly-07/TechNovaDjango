from datetime import datetime
from decimal import Decimal

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from envios.application.services import EnvioService
from envios.domain.entities import EnvioEntidad
from envios.infrastructure.repositories import EnvioOrmRepository
from envios.models import Envio, Transportadora


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_envios(request):
    queryset = Envio.objects.select_related("transportadora", "venta").order_by("-id")
    return success_response(
        {
            "items": [
                {
                    "id": envio.id,
                    "venta_id": envio.venta_id,
                    "transportadora_id": envio.transportadora_id,
                    "transportadora": envio.transportadora.nombre,
                    "numero_guia": envio.numero_guia,
                    "fecha_envio": envio.fecha_envio.isoformat(),
                    "costo_envio": str(envio.costo_envio),
                    "estado": envio.estado,
                }
                for envio in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_envio(request):
    try:
        payload = parse_json_body(request)
        fecha_envio = datetime.fromisoformat(payload["fecha_envio"])
        if timezone.is_naive(fecha_envio):
            fecha_envio = timezone.make_aware(fecha_envio, timezone.get_current_timezone())
        envio = EnvioEntidad(
            id=None,
            venta_id=payload["venta_id"],
            transportadora_id=payload["transportadora_id"],
            fecha_envio=fecha_envio,
            numero_guia=payload["numero_guia"],
            costo_envio=Decimal(str(payload.get("costo_envio", "0"))),
            estado=payload.get("estado", "preparando"),
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    service = EnvioService(EnvioOrmRepository())
    try:
        guardado = service.registrar_envio(envio)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    return success_response({"id": guardado.id, "numero_guia": guardado.numero_guia}, status=201)


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_transportadoras(request):
    queryset = Transportadora.objects.order_by("nombre")
    return success_response(
        {
            "items": [
                {
                    "id": transportadora.id,
                    "nombre": transportadora.nombre,
                    "telefono": transportadora.telefono,
                    "correo_electronico": transportadora.correo_electronico,
                }
                for transportadora in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def crear_transportadora(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        transportadora = Transportadora.objects.create(
            nombre=payload["nombre"],
            telefono=payload["telefono"],
            correo_electronico=payload["correo_electronico"],
            activo=payload.get("activo", True),
        )
    except KeyError as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": transportadora.id, "nombre": transportadora.nombre}, status=201)
