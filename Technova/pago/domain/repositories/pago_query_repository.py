from abc import ABC, abstractmethod


class PagoQueryPort(ABC):
    @abstractmethod
    def listar_pagos(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_pago(self, pago_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def listar_metodos_usuario(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_metodo_usuario(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    def listar_medios_pago_lineas(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_medio_pago_linea(self, medio_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def crear_medio_pago_linea(self, data: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def actualizar_medio_pago_linea(self, medio_id: int, data: dict) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def desactivar_medio_pago_linea(self, medio_id: int) -> bool:
        raise NotImplementedError
