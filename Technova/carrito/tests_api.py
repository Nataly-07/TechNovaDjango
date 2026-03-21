import json
from decimal import Decimal

from django.test import Client, TestCase

from productos.models import Producto
from proveedores.models import Proveedor
from usuarios.models import Usuario


class CarritoApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_carrito",
            correo_electronico="admin.carrito@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Carrito",
            tipo_documento="CC",
            numero_documento="80001",
            telefono="3000000001",
            direccion="Calle 1",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.cliente_a = Usuario.objects.create(
            nombre_usuario="cliente_a",
            correo_electronico="cliente.a@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="A",
            tipo_documento="CC",
            numero_documento="80002",
            telefono="3000000002",
            direccion="Calle 2",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.cliente_b = Usuario.objects.create(
            nombre_usuario="cliente_b",
            correo_electronico="cliente.b@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="B",
            tipo_documento="CC",
            numero_documento="80003",
            telefono="3000000003",
            direccion="Calle 3",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        proveedor = Proveedor.objects.create(
            identificacion="900777111",
            nombre="Proveedor Carrito",
            telefono="3010001111",
            correo_electronico="prov.carrito@demo.com",
            empresa="Proveedor SA",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="PR-CAR-1",
            nombre="Mouse",
            imagen_url="",
            stock=100,
            proveedor=proveedor,
            costo_unitario=Decimal("20"),
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

    def test_cliente_no_puede_crear_carrito_para_otro_usuario(self):
        token = self._token("cliente.a@demo.com")
        response = self.client.post(
            "/api/v1/carrito/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.cliente_b.id,
                    "items": [{"producto_id": self.producto.id, "cantidad": 1}],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_si_puede_crear_carrito_para_otro_usuario(self):
        token = self._token("admin.carrito@demo.com")
        response = self.client.post(
            "/api/v1/carrito/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.cliente_b.id,
                    "items": [{"producto_id": self.producto.id, "cantidad": 2}],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
