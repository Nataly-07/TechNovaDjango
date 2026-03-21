from envios.models import Envio, Transportadora
from envios.domain.query_ports import EnvioQueryPort


class EnvioQueryRepository(EnvioQueryPort):
    def listar_envios(self) -> list[dict]:
        queryset = Envio.objects.select_related("transportadora", "venta").order_by("-id")
        return [
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

    def listar_transportadoras(self) -> list[dict]:
        queryset = Transportadora.objects.order_by("nombre")
        return [
            {
                "id": t.id,
                "nombre": t.nombre,
                "telefono": t.telefono,
                "correo_electronico": t.correo_electronico,
            }
            for t in queryset
        ]

    def crear_transportadora(self, data: dict) -> int:
        transportadora = Transportadora.objects.create(**data)
        return transportadora.id
