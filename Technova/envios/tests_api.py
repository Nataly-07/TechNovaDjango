import json
from datetime import date
from decimal import Decimal

from django.test import Client, TestCase

from envios.models import Transportadora
from pagos.models import Pago
from productos.models import Producto
from proveedores.models import Proveedor
from usuarios.models import Usuario
from ventas.models import DetalleVenta, Venta


class EnviosApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_envios",
            correo_electronico="admin.envios@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Envios",
            tipo_documento="CC",
            numero_documento="82001",
            telefono="3002000001",
            direccion="Calle 20",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.empleado = Usuario.objects.create(
            nombre_usuario="empleado_envios",
            correo_electronico="empleado.envios@demo.com",
            contrasena_hash="123456",
            nombres="Empleado",
            apellidos="Envios",
            tipo_documento="CC",
            numero_documento="82002",
            telefono="3002000002",
            direccion="Calle 21",
            rol=Usuario.Rol.EMPLEADO,
            activo=True,
        )
        self.cliente = Usuario.objects.create(
            nombre_usuario="cliente_envios",
            correo_electronico="cliente.envios@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Envios",
            tipo_documento="CC",
            numero_documento="82003",
            telefono="3002000003",
            direccion="Calle 22",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        proveedor = Proveedor.objects.create(
            identificacion="900666333",
            nombre="Proveedor Envios",
            telefono="3011239999",
            correo_electronico="prov.envios@demo.com",
            empresa="Proveedor Envios",
            activo=True,
        )
        producto = Producto.objects.create(
            codigo="PROD-ENV-1",
            nombre="Monitor",
            imagen_url="",
            stock=20,
            proveedor=proveedor,
            costo_unitario=Decimal("200"),
            activo=True,
        )
        self.venta = Venta.objects.create(
            usuario=self.cliente,
            fecha_venta=date.today(),
            estado=Venta.Estado.FACTURADA,
            total=Decimal("200"),
        )
        DetalleVenta.objects.create(
            venta=self.venta,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal("200"),
        )
        self.transportadora = Transportadora.objects.create(
            nombre="Trans Existing",
            telefono="3028889999",
            correo_electronico="trans.existing@demo.com",
            activo=True,
        )
        self.pago = Pago.objects.create(
            fecha_pago=date.today(),
            numero_factura="FAC-ENV-1",
            fecha_factura=date.today(),
            monto=Decimal("200"),
            estado_pago=Pago.EstadoPago.APROBADO,
        )

    def _token(self, correo: str) -> str:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"correo_electronico": correo, "contrasena": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["access"]

    def test_cliente_no_puede_registrar_envio(self):
        token = self._token("cliente.envios@demo.com")
        response = self.client.post(
            "/api/v1/envios/registrar/",
            data=json.dumps(
                {
                    "venta_id": self.venta.id,
                    "transportadora_id": self.transportadora.id,
                    "fecha_envio": "2026-03-21T10:00:00",
                    "numero_guia": "GUIA-ENV-API-1",
                    "costo_envio": "10",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_empleado_si_puede_registrar_envio(self):
        token = self._token("empleado.envios@demo.com")
        response = self.client.post(
            "/api/v1/envios/registrar/",
            data=json.dumps(
                {
                    "venta_id": self.venta.id,
                    "transportadora_id": self.transportadora.id,
                    "fecha_envio": "2026-03-21T10:00:00",
                    "numero_guia": "GUIA-ENV-API-2",
                    "costo_envio": "10",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
