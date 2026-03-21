from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from ventas.application.checkout_service import CheckoutService
from ventas.application.venta_service import VentaService
from ventas.models import Venta


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_ventas(request):
    queryset = Venta.objects.prefetch_related("detalles").order_by("-id")
    return success_response(
        {
            "items": [
                {
                    "id": venta.id,
                    "usuario_id": venta.usuario_id,
                    "fecha_venta": venta.fecha_venta.isoformat(),
                    "estado": venta.estado,
                    "total": str(venta.total),
                    "detalles": [
                        {
                            "producto_id": detalle.producto_id,
                            "cantidad": detalle.cantidad,
                            "precio_unitario": str(detalle.precio_unitario),
                        }
                        for detalle in venta.detalles.all()
                    ],
                }
                for venta in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth()
def checkout(request):
    try:
        payload = parse_json_body(request)
        carrito_id = int(payload["carrito_id"])
        metodo_pago = payload["metodo_pago"]
        numero_factura = payload["numero_factura"]
        fecha_factura = date.fromisoformat(payload["fecha_factura"])
        transportadora_id = int(payload["transportadora_id"])
        numero_guia = payload["numero_guia"]
        costo_envio = Decimal(str(payload.get("costo_envio", "0")))
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)

    service = CheckoutService()
    try:
        resultado = service.ejecutar_checkout(
            usuario=request.usuario_actual,
            carrito_id=carrito_id,
            metodo_pago=metodo_pago,
            numero_factura=numero_factura,
            fecha_factura=fecha_factura,
            transportadora_id=transportadora_id,
            numero_guia=numero_guia,
            costo_envio=costo_envio,
        )
    except ValueError as exc:
        return error_response(str(exc), status=400)
    except IntegrityError:
        return error_response("Factura o numero de guia ya existe.", status=409)

    return success_response(
        {
            "venta_id": resultado.venta_id,
            "pago_id": resultado.pago_id,
            "envio_id": resultado.envio_id,
            "total": str(resultado.total),
            "idempotente": resultado.idempotente,
        },
        message="Checkout ya procesado" if resultado.idempotente else "Checkout completado",
        status=200 if resultado.idempotente else 201,
    )


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def anular_venta(request, venta_id: int):
    service = VentaService()
    try:
        resultado = service.anular_venta(venta_id=venta_id)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    return success_response(
        {
            "venta_id": resultado.venta_id,
            "pagos_reembolsados": resultado.pagos_reembolsados,
            "items_revertidos": resultado.items_revertidos,
        },
        message="Venta anulada con exito",
    )
