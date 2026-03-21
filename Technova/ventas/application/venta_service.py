from ventas.domain.ports import VentaAnulacionPort
from ventas.domain.results import AnulacionVentaResultado


class VentaService:
    def __init__(self, anulacion_port: VentaAnulacionPort) -> None:
        self.anulacion_port = anulacion_port

    def anular_venta(self, venta_id: int) -> AnulacionVentaResultado:
        return self.anulacion_port.anular_venta(venta_id)
