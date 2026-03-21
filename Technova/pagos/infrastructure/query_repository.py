from pagos.models import MetodoPagoUsuario, Pago
from pagos.domain.query_ports import PagoQueryPort


class PagoQueryRepository(PagoQueryPort):
    def listar_pagos(self) -> list[dict]:
        queryset = Pago.objects.order_by("-id")
        return [
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

    def listar_metodos_usuario(self, usuario_id: int | None) -> list[dict]:
        queryset = MetodoPagoUsuario.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
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

    def crear_metodo_usuario(self, data: dict) -> int:
        metodo = MetodoPagoUsuario.objects.create(**data)
        return metodo.id
