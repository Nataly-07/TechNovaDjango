from django.db import IntegrityError

from envio.domain.entities import EnvioEntidad
from envio.domain.repositories import EnvioRepositoryPort
from envio.models import Envio


class EnvioOrmRepository(EnvioRepositoryPort):
    def guardar(self, envio: EnvioEntidad) -> EnvioEntidad:
        model = Envio.objects.create(
            venta_id=envio.venta_id,
            transportadora_id=envio.transportadora_id,
            fecha_envio=envio.fecha_envio,
            numero_guia=envio.numero_guia,
            costo_envio=envio.costo_envio,
            estado=envio.estado,
        )
        return EnvioEntidad(
            id=model.id,
            venta_id=model.venta_id,
            transportadora_id=model.transportadora_id,
            fecha_envio=model.fecha_envio,
            numero_guia=model.numero_guia,
            costo_envio=model.costo_envio,
            estado=model.estado,
        )

    def actualizar(self, envio: EnvioEntidad) -> EnvioEntidad | None:
        if envio.id is None:
            return None
        try:
            model = Envio.objects.get(id=envio.id)
        except Envio.DoesNotExist:
            return None
        estado_anterior = model.estado
        model.venta_id = envio.venta_id
        model.transportadora_id = envio.transportadora_id
        model.fecha_envio = envio.fecha_envio
        model.numero_guia = envio.numero_guia.strip()
        model.costo_envio = envio.costo_envio
        model.estado = envio.estado
        try:
            model.save()
        except IntegrityError:
            raise ValueError("Numero de guia duplicado.") from None
        if estado_anterior != model.estado and model.estado in (
            Envio.Estado.EN_RUTA,
            Envio.Estado.ENTREGADO,
        ):
            from mensajeria.services.notificaciones_admin import notificar_envio_cambio_estado

            notificar_envio_cambio_estado(
                envio_id=model.id,
                venta_id=model.venta_id,
                estado_anterior=estado_anterior,
                estado_nuevo=model.estado,
                guia=model.numero_guia,
            )
        return EnvioEntidad(
            id=model.id,
            venta_id=model.venta_id,
            transportadora_id=model.transportadora_id,
            fecha_envio=model.fecha_envio,
            numero_guia=model.numero_guia,
            costo_envio=model.costo_envio,
            estado=model.estado,
        )

    def marcar_inactivo(self, envio_id: int) -> bool:
        return Envio.objects.filter(id=envio_id).update(activo=False) > 0
