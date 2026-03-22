from envio.domain.repositories import EnvioQueryPort
from envio.models import Envio, Transportadora


class EnvioQueryRepository(EnvioQueryPort):
    @staticmethod
    def _transportadora_dict(t: Transportadora) -> dict:
        return {
            "id": t.id,
            "nombre": t.nombre,
            "telefono": t.telefono,
            "correo_electronico": t.correo_electronico,
            "activo": t.activo,
        }

    def _envio_dict(self, envio: Envio) -> dict:
        return {
            "id": envio.id,
            "venta_id": envio.venta_id,
            "transportadora_id": envio.transportadora_id,
            "transportadora": envio.transportadora.nombre,
            "numero_guia": envio.numero_guia,
            "fecha_envio": envio.fecha_envio.isoformat(),
            "costo_envio": str(envio.costo_envio),
            "estado": envio.estado,
            "activo": envio.activo,
        }

    def listar_envios(self) -> list[dict]:
        queryset = Envio.objects.select_related("transportadora", "venta").order_by("-id")
        return [self._envio_dict(envio) for envio in queryset]

    def obtener_envio(self, envio_id: int) -> dict | None:
        envio = (
            Envio.objects.select_related("transportadora", "venta").filter(id=envio_id).first()
        )
        return self._envio_dict(envio) if envio else None

    def listar_transportadoras(self) -> list[dict]:
        queryset = Transportadora.objects.order_by("nombre")
        return [self._transportadora_dict(t) for t in queryset]

    def crear_transportadora(self, data: dict) -> int:
        transportadora = Transportadora.objects.create(**data)
        return transportadora.id

    def obtener_transportadora(self, transportadora_id: int) -> dict | None:
        t = Transportadora.objects.filter(id=transportadora_id).first()
        return self._transportadora_dict(t) if t else None

    def actualizar_transportadora(self, transportadora_id: int, data: dict) -> dict | None:
        t = Transportadora.objects.filter(id=transportadora_id).first()
        if t is None:
            return None
        for key in ("nombre", "telefono", "correo_electronico", "activo"):
            if key in data:
                setattr(t, key, data[key])
        t.save()
        return self._transportadora_dict(t)

    def desactivar_transportadora(self, transportadora_id: int) -> bool:
        return Transportadora.objects.filter(id=transportadora_id).update(activo=False) > 0

    def listar_transportadoras_por_envio(self, envio_id: int) -> list[dict]:
        envio = Envio.objects.filter(id=envio_id).select_related("transportadora").first()
        if envio is None:
            return []
        return [self._transportadora_dict(envio.transportadora)]
