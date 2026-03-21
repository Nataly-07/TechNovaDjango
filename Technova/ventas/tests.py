from datetime import date
from decimal import Decimal

from django.test import TestCase

from common.container import get_checkout_service, get_venta_service
from carrito.models import Carrito, DetalleCarrito
from envios.models import Envio, Transportadora
from pagos.models import Pago
from productos.models import Producto
from proveedores.models import Proveedor
from usuarios.models import Usuario
from ventas.models import Venta


class FlujoVentaTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            nombre_usuario="cliente_demo",
            correo_electronico="cliente@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Demo",
            tipo_documento="CC",
            numero_documento="12345678",
            telefono="3000000000",
            direccion="Calle 1",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.proveedor = Proveedor.objects.create(
            identificacion="900111222",
            nombre="Proveedor Demo",
            telefono="3011111111",
            correo_electronico="proveedor@demo.com",
            empresa="Tech Supplier",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="P-001",
            nombre="Mouse Gamer",
            imagen_url="",
            stock=10,
            proveedor=self.proveedor,
            costo_unitario=Decimal("100"),
            activo=True,
        )
        self.transportadora = Transportadora.objects.create(
            nombre="Trans Demo",
            telefono="3022222222",
            correo_electronico="trans@demo.com",
            activo=True,
        )

    def test_checkout_crea_venta_pago_envio_y_descuenta_stock(self):
        carrito = Carrito.objects.create(usuario=self.usuario, estado=Carrito.Estado.ACTIVO)
        DetalleCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=2)

        resultado = get_checkout_service().ejecutar_checkout(
            usuario_id=self.usuario.id,
            carrito_id=carrito.id,
            metodo_pago="pse",
            numero_factura="FAC-1000",
            fecha_factura=date.today(),
            transportadora_id=self.transportadora.id,
            numero_guia="GUIA-1000",
            costo_envio=Decimal("10"),
        )

        self.assertTrue(Venta.objects.filter(id=resultado.venta_id).exists())
        self.assertTrue(Pago.objects.filter(id=resultado.pago_id).exists())
        self.assertTrue(Envio.objects.filter(id=resultado.envio_id).exists())

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

        carrito.refresh_from_db()
        self.assertEqual(carrito.estado, Carrito.Estado.CERRADO)
        self.assertEqual(carrito.detalles.count(), 0)

    def test_anular_venta_revierte_stock_y_reembolsa_pago(self):
        carrito = Carrito.objects.create(usuario=self.usuario, estado=Carrito.Estado.ACTIVO)
        DetalleCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=3)

        checkout = get_checkout_service().ejecutar_checkout(
            usuario_id=self.usuario.id,
            carrito_id=carrito.id,
            metodo_pago="pse",
            numero_factura="FAC-1001",
            fecha_factura=date.today(),
            transportadora_id=self.transportadora.id,
            numero_guia="GUIA-1001",
            costo_envio=Decimal("0"),
        )

        resultado = get_venta_service().anular_venta(checkout.venta_id)
        self.assertEqual(resultado.venta_id, checkout.venta_id)

        venta = Venta.objects.get(id=checkout.venta_id)
        self.assertEqual(venta.estado, Venta.Estado.ANULADA)

        pago = Pago.objects.get(id=checkout.pago_id)
        self.assertEqual(pago.estado_pago, Pago.EstadoPago.REEMBOLSADO)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_checkout_es_idempotente_por_numero_factura(self):
        carrito = Carrito.objects.create(usuario=self.usuario, estado=Carrito.Estado.ACTIVO)
        DetalleCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=1)

        primero = get_checkout_service().ejecutar_checkout(
            usuario_id=self.usuario.id,
            carrito_id=carrito.id,
            metodo_pago="pse",
            numero_factura="FAC-IDEMP-1",
            fecha_factura=date.today(),
            transportadora_id=self.transportadora.id,
            numero_guia="GUIA-IDEMP-1",
            costo_envio=Decimal("0"),
        )
        segundo = get_checkout_service().ejecutar_checkout(
            usuario_id=self.usuario.id,
            carrito_id=carrito.id,
            metodo_pago="pse",
            numero_factura="FAC-IDEMP-1",
            fecha_factura=date.today(),
            transportadora_id=self.transportadora.id,
            numero_guia="GUIA-IDEMP-1",
            costo_envio=Decimal("0"),
        )

        self.assertEqual(primero.venta_id, segundo.venta_id)
        self.assertEqual(primero.pago_id, segundo.pago_id)
        self.assertTrue(segundo.idempotente)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(Pago.objects.count(), 1)
