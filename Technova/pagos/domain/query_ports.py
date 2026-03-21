from abc import ABC, abstractmethod


class PagoQueryPort(ABC):
    @abstractmethod
    def listar_pagos(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_metodos_usuario(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_metodo_usuario(self, data: dict) -> int:
        raise NotImplementedError
