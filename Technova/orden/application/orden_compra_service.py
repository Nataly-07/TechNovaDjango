from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional

from orden.dto.orden_compra_dto import OrdenCompraDto, DetalleOrdenDto


class OrdenCompraService:
    """Servicio de Órdenes de Compra - Replicando la lógica de Spring Boot"""
    
    def __init__(self):
        pass
    
    def listar_ordenes(self) -> List[OrdenCompraDto]:
        """
        Listar todas las órdenes de compra
        Equivalente a: List<OrdenCompraDto> ordenes = ordenCompraService.listarOrdenes();
        """
        try:
            from orden.infrastructure.models import OrdenCompra, DetalleOrden
        except ImportError:
            try:
                from orden.models import OrdenCompra, DetalleOrden
            except ImportError:
                return []
        
        ordenes_dto = []
        
        # Obtener órdenes con sus relaciones
        ordenes = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles__producto').order_by('-id')
        
        for orden in ordenes:
            # Crear DTO principal
            orden_dto = OrdenCompraDto(
                id=orden.id,
                proveedor_id=orden.proveedor_id,
                proveedor_nombre=orden.proveedor.nombre,
                fecha=orden.fecha,
                total=orden.total,
                estado=orden.estado,
                detalles=[]
            )
            
            # Agregar detalles
            for detalle in orden.detalles.all():
                detalle_dto = DetalleOrdenDto(
                    producto_id=detalle.producto_id,
                    producto_nombre=detalle.producto.nombre,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                    subtotal=detalle.subtotal
                )
                orden_dto.detalles.append(detalle_dto)
            
            ordenes_dto.append(orden_dto)
        
        return ordenes_dto
    
    def crear_orden(self, orden_dto: OrdenCompraDto) -> OrdenCompraDto:
        """
        Crear una nueva orden de compra
        Equivalente a: ordenCompraService.crearOrden(ordenDto);
        """
        try:
            from orden.infrastructure.models import OrdenCompra, DetalleOrden
        except ImportError:
            try:
                from orden.models import OrdenCompra, DetalleOrden
            except ImportError:
                raise Exception("Módulo de órdenes no disponible")
        
        # Validar que tenga detalles válidos
        if not orden_dto.tiene_detalles_validos():
            raise Exception("Debe agregar al menos un producto a la orden")
        
        try:
            # Crear la orden principal
            orden = OrdenCompra.objects.create(
                proveedor_id=orden_dto.proveedor_id,
                fecha=orden_dto.fecha or date.today(),
                total=orden_dto.calcular_total(),
                estado=orden_dto.estado or 'pendiente'
            )
            
            # Crear los detalles
            for detalle_dto in orden_dto.detalles:
                DetalleOrden.objects.create(
                    orden_compra=orden,
                    producto_id=detalle_dto.producto_id,
                    cantidad=detalle_dto.cantidad,
                    precio_unitario=detalle_dto.precio_unitario,
                    subtotal=detalle_dto.subtotal
                )
            
            # Recargar la orden con relaciones
            orden_creada = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles__producto').get(id=orden.id)
            
            # Convertir a DTO y retornar
            return self._convertir_a_dto(orden_creada)
            
        except Exception as e:
            raise Exception(f"Error al crear la orden: {str(e)}")
    
    def recibir_orden(self, orden_id: int) -> bool:
        """
        Recibir una orden y actualizar el stock
        Equivalente a: ordenCompraService.recibirOrden(id);
        """
        try:
            from orden.infrastructure.models import OrdenCompra, DetalleOrden
        except ImportError:
            try:
                from orden.models import OrdenCompra, DetalleOrden
            except ImportError:
                raise Exception("Módulo de órdenes no disponible")
        
        try:
            # Obtener la orden
            orden = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles__producto').get(id=orden_id)
            
            if orden.estado != 'pendiente':
                raise Exception("Solo se pueden recibir órdenes en estado pendiente")
            
            # Cambiar estado
            orden.estado = 'recibida'
            orden.save()
            
            # Actualizar stock de productos
            from producto.models import Producto
            for detalle in orden.detalles.all():
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save()
            
            return True
            
        except OrdenCompra.DoesNotExist:
            raise Exception("Orden no encontrada")
        except Exception as e:
            raise Exception(f"Error al recibir la orden: {str(e)}")
    
    def obtener_orden_por_id(self, orden_id: int) -> Optional[OrdenCompraDto]:
        """
        Obtener una orden por su ID
        Equivalente a: OrdenCompraDto orden = ordenCompraService.obtenerOrdenPorId(id);
        """
        try:
            from orden.infrastructure.models import OrdenCompra, DetalleOrden
        except ImportError:
            try:
                from orden.models import OrdenCompra, DetalleOrden
            except ImportError:
                return None
        
        try:
            orden = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles__producto').get(id=orden_id)
            return self._convertir_a_dto(orden)
        except OrdenCompra.DoesNotExist:
            return None
    
    def _convertir_a_dto(self, orden) -> OrdenCompraDto:
        """Convertir modelo a DTO (método helper)"""
        orden_dto = OrdenCompraDto(
            id=orden.id,
            proveedor_id=orden.proveedor_id,
            proveedor_nombre=orden.proveedor.nombre,
            fecha=orden.fecha,
            total=orden.total,
            estado=orden.estado,
            detalles=[]
        )
        
        for detalle in orden.detalles.all():
            detalle_dto = DetalleOrdenDto(
                producto_id=detalle.producto_id,
                producto_nombre=detalle.producto.nombre,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal
            )
            orden_dto.detalles.append(detalle_dto)
        
        return orden_dto
