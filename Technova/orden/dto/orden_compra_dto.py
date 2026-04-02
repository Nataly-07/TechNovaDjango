from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class DetalleOrdenDto:
    producto_id: Optional[int] = None
    producto_nombre: Optional[str] = None
    cantidad: Optional[int] = None
    precio_unitario: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None


@dataclass
class OrdenCompraDto:
    id: Optional[int] = None
    proveedor_id: Optional[int] = None
    proveedor_nombre: Optional[str] = None  # Para mostrar en la lista
    fecha: Optional[date] = None
    total: Optional[Decimal] = None
    estado: Optional[str] = None
    detalles: Optional[List[DetalleOrdenDto]] = None
    
    # Métodos helper
    def __post_init__(self):
        if self.detalles is None:
            self.detalles = []
        if self.total is None:
            self.total = Decimal('0')
    
    def calcular_total(self):
        """Calcular el total basado en los detalles"""
        if self.detalles:
            self.total = sum(
                (detalle.cantidad or 0) * (detalle.precio_unitario or 0) 
                for detalle in self.detalles
            )
        return self.total
    
    def agregar_detalle(self, producto_id, cantidad, precio_unitario):
        """Agregar un detalle a la orden"""
        subtotal = Decimal(str(cantidad)) * Decimal(str(precio_unitario))
        detalle = DetalleOrdenDto(
            producto_id=producto_id,
            cantidad=cantidad,
            precio_unitario=Decimal(str(precio_unitario)),
            subtotal=subtotal
        )
        self.detalles.append(detalle)
        self.calcular_total()
        return detalle
    
    def limpiar_detalles_vacios(self):
        """Eliminar detalles vacíos o con cantidad 0"""
        if self.detalles:
            self.detalles = [
                d for d in self.detalles 
                if d.producto_id is not None and d.cantidad is not None and d.cantidad > 0
            ]
        self.calcular_total()
    
    def tiene_detalles_validos(self):
        """Verificar si hay detalles válidos"""
        self.limpiar_detalles_vacios()
        return len(self.detalles) > 0
