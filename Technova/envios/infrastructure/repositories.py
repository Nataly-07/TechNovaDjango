from envios.domain.entities import EnvioEntidad
from envios.domain.repositories import EnvioRepositoryPort
from envios.models import Envio


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
