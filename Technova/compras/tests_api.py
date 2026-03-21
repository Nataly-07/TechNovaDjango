import json
from decimal import Decimal

from django.test import Client, TestCase

from productos.models import Producto
from proveedores.models import Proveedor
from usuarios.models import Usuario


class ComprasApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_compras",
            correo_electronico="admin.compras@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Compras",
            tipo_documento="CC",
            numero_documento="83001",
            telefono="3003000001",
            direccion="Calle 30",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.empleado = Usuario.objects.create(
            nombre_usuario="empleado_compras",
            correo_electronico="empleado.compras@demo.com",
            contrasena_hash="123456",
            nombres="Empleado",
            apellidos="Compras",
            tipo_documento="CC",
            numero_documento="83002",
            telefono="3003000002",
            direccion="Calle 31",
            rol=Usuario.Rol.EMPLEADO,
            activo=True,
        )
        self.cliente = Usuario.objects.create(
            nombre_usuario="cliente_compras",
            correo_electronico="cliente.compras@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Compras",
            tipo_documento="CC",
            numero_documento="83003",
            telefono="3003000003",
            direccion="Calle 32",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.proveedor = Proveedor.objects.create(
            identificacion="900444222",
            nombre="Proveedor Compras",
            telefono="3014442222",
            correo_electronico="prov.compras@demo.com",
            empresa="Proveedor Compras SAS",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="PROD-COMP-1",
            nombre="SSD",
            imagen_url="",
            stock=15,
            proveedor=self.proveedor,
            costo_unitario=Decimal("120"),
            activo=True,
        )

    def _token(self, correo: str) -> str:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"correo_electronico": correo, "contrasena": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["access"]

    def test_cliente_no_puede_registrar_compra(self):
        token = self._token("cliente.compras@demo.com")
        response = self.client.post(
            "/api/v1/compras/registrar/",
            data=json.dumps(
                {
                    "proveedor_id": self.proveedor.id,
                    "fecha_compra": "2026-03-21T10:00:00",
                    "items": [{"producto_id": self.producto.id, "cantidad": 1, "precio_unitario": "120"}],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_empleado_no_puede_registrar_compra_para_otro_usuario(self):
        token = self._token("empleado.compras@demo.com")
        response = self.client.post(
            "/api/v1/compras/registrar/",
            data=json.dumps(
                {
                    "usuario_id": self.admin.id,
                    "proveedor_id": self.proveedor.id,
                    "fecha_compra": "2026-03-21T10:00:00",
                    "items": [{"producto_id": self.producto.id, "cantidad": 1, "precio_unitario": "120"}],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)
