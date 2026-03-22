from datetime import date

from pago.domain.entities import PagoEntidad
from pago.domain.repositories import PagoQueryPort, PagoRepositoryPort
from pago.domain.value_objects import Dinero, EstadoPago, NumeroFactura


class PagoService:
    def __init__(self, repository: PagoRepositoryPort) -> None:
        self.repository = repository

    def registrar_pago(self, pago: PagoEntidad) -> PagoEntidad:
        NumeroFactura.crear(pago.numero_factura)
        Dinero.crear(pago.monto)
        EstadoPago.validar(pago.estado_pago)
        return self.repository.guardar(pago)


class PagoQueryService:
    def __init__(self, repository: PagoQueryPort) -> None:
        self.repository = repository

    def listar_pagos(self) -> list[dict]:
        return self.repository.listar_pagos()

    def obtener_pago(self, pago_id: int) -> dict | None:
        return self.repository.obtener_pago(pago_id)

    def listar_metodos_usuario(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_metodos_usuario(usuario_id)

    def crear_metodo_usuario(self, data: dict) -> int:
        return self.repository.crear_metodo_usuario(data)

    def listar_medios_pago_lineas(self) -> list[dict]:
        return self.repository.listar_medios_pago_lineas()

    def obtener_medio_pago_linea(self, medio_id: int) -> dict | None:
        return self.repository.obtener_medio_pago_linea(medio_id)

    def crear_medio_pago_linea(self, data: dict) -> dict:
        return self.repository.crear_medio_pago_linea(data)

    def actualizar_medio_pago_linea(self, medio_id: int, data: dict) -> dict | None:
        return self.repository.actualizar_medio_pago_linea(medio_id, data)

    def desactivar_medio_pago_linea(self, medio_id: int) -> bool:
        return self.repository.desactivar_medio_pago_linea(medio_id)


class PagoStateService:
    def __init__(self, repository: PagoRepositoryPort) -> None:
        self.repository = repository

    allowed_transitions = {
        EstadoPago.PENDIENTE: {EstadoPago.APROBADO, EstadoPago.RECHAZADO},
        EstadoPago.APROBADO: {EstadoPago.REEMBOLSADO},
        EstadoPago.RECHAZADO: {EstadoPago.PENDIENTE},
        EstadoPago.REEMBOLSADO: set(),
    }

    def actualizar_estado(self, pago_id: int, nuevo_estado: str) -> PagoEntidad:
        pago = self.repository.obtener_por_id(pago_id)
        if pago is None:
            raise ValueError("El pago no existe.")

        nuevo_estado_vo = EstadoPago.validar(nuevo_estado)
        estado_actual_vo = EstadoPago.validar(pago.estado_pago)
        if nuevo_estado_vo == estado_actual_vo:
            return pago

        permitidos = self.allowed_transitions.get(estado_actual_vo, set())
        if nuevo_estado_vo not in permitidos:
            raise ValueError(
                f"Transicion invalida de {pago.estado_pago} a {nuevo_estado}."
            )

        actualizado = self.repository.actualizar_estado(pago_id=pago.id, estado_pago=nuevo_estado_vo.value)
        if nuevo_estado_vo == EstadoPago.APROBADO:
            return PagoEntidad(
                id=actualizado.id,
                fecha_pago=date.today(),
                numero_factura=actualizado.numero_factura,
                fecha_factura=actualizado.fecha_factura,
                monto=actualizado.monto,
                estado_pago=actualizado.estado_pago,
            )
        return actualizado
