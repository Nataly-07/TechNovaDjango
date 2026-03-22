from datetime import datetime

from django.utils import timezone

from pago.domain.repositories import PagoQueryPort
from pago.models import MedioPago, MetodoPagoUsuario, Pago


class PagoQueryRepository(PagoQueryPort):
    @staticmethod
    def _pago_dict(pago: Pago) -> dict:
        return {
            "id": pago.id,
            "numero_factura": pago.numero_factura,
            "fecha_factura": pago.fecha_factura.isoformat(),
            "fecha_pago": pago.fecha_pago.isoformat(),
            "monto": str(pago.monto),
            "estado_pago": pago.estado_pago,
        }

    def listar_pagos(self) -> list[dict]:
        queryset = Pago.objects.order_by("-id")
        return [self._pago_dict(pago) for pago in queryset]

    def obtener_pago(self, pago_id: int) -> dict | None:
        pago = Pago.objects.filter(id=pago_id).first()
        return self._pago_dict(pago) if pago else None

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

    def _medio_linea_dict(self, m: MedioPago) -> dict:
        return {
            "id": m.id,
            "metodoPago": m.metodo_pago,
            "pagoId": m.pago_id,
            "detalleVentaId": m.detalle_venta_id,
            "usuarioId": m.usuario_id,
            "fechaDeCompra": m.fecha_compra.isoformat(),
            "tiempoDeEntrega": m.tiempo_entrega.isoformat() if m.tiempo_entrega else None,
            "estado": m.activo,
        }

    def listar_medios_pago_lineas(self) -> list[dict]:
        return [self._medio_linea_dict(m) for m in MedioPago.objects.order_by("-id")]

    def obtener_medio_pago_linea(self, medio_id: int) -> dict | None:
        m = MedioPago.objects.filter(id=medio_id).first()
        return self._medio_linea_dict(m) if m else None

    def crear_medio_pago_linea(self, data: dict) -> dict:
        payload = {**data}
        pago_id = payload.get("pago_id") or payload.get("pagoId")
        dv_id = payload.get("detalle_venta_id") or payload.get("detalleVentaId")
        usuario_id = payload.get("usuario_id") or payload.get("usuarioId")
        metodo = payload.get("metodo_pago") or payload.get("metodoPago")
        fc = payload.get("fecha_compra") or payload.get("fechaDeCompra")
        if isinstance(fc, str):
            fc = datetime.fromisoformat(fc.replace("Z", "+00:00"))
        if timezone.is_naive(fc):
            fc = timezone.make_aware(fc, timezone.get_current_timezone())
        te = payload.get("tiempo_entrega") or payload.get("tiempoDeEntrega")
        if isinstance(te, str):
            te = datetime.fromisoformat(te.replace("Z", "+00:00"))
            if timezone.is_naive(te):
                te = timezone.make_aware(te, timezone.get_current_timezone())
        m = MedioPago.objects.create(
            pago_id=pago_id,
            detalle_venta_id=dv_id,
            usuario_id=usuario_id,
            metodo_pago=metodo,
            fecha_compra=fc,
            tiempo_entrega=te,
            activo=payload.get("activo", payload.get("estado", True)),
        )
        return self._medio_linea_dict(m)

    def actualizar_medio_pago_linea(self, medio_id: int, data: dict) -> dict | None:
        m = MedioPago.objects.filter(id=medio_id).first()
        if m is None:
            return None
        if "metodo_pago" in data or "metodoPago" in data:
            m.metodo_pago = data.get("metodo_pago") or data.get("metodoPago")
        if "activo" in data or "estado" in data:
            m.activo = data.get("activo", data.get("estado", m.activo))
        if "tiempo_entrega" in data or "tiempoDeEntrega" in data:
            te = data.get("tiempo_entrega") or data.get("tiempoDeEntrega")
            if isinstance(te, str):
                te = datetime.fromisoformat(te.replace("Z", "+00:00"))
                if timezone.is_naive(te):
                    te = timezone.make_aware(te, timezone.get_current_timezone())
            m.tiempo_entrega = te
        m.save()
        return self._medio_linea_dict(m)

    def desactivar_medio_pago_linea(self, medio_id: int) -> bool:
        return MedioPago.objects.filter(id=medio_id).update(activo=False) > 0
