import json

from django.test import Client, TestCase

from producto.models import Producto
from proveedor.models import Proveedor
from usuario.models import Usuario


class ProductoApiTestCase(TestCase):
    """Catalogo publico y mutaciones con JWT."""

    def setUp(self):
        self.client = Client()
        self.proveedor = Proveedor.objects.create(
            identificacion="900111222",
            nombre="Prov Prod API",
            telefono="3001112222",
            correo_electronico="prov.prod@test.com",
            empresa="Prov Prod SAS",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="TP-API-1",
            nombre="Producto API",
            imagen_url="",
            stock=5,
            proveedor=self.proveedor,
            costo_unitario=50,
            activo=True,
        )
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_prod_api",
            correo_electronico="admin.prod@test.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Prod",
            tipo_documento="CC",
            numero_documento="99001",
            telefono="30099001",
            direccion="Calle 1",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )

    def test_catalogo_get_sin_auth(self):
        r = self.client.get("/api/v1/producto/")
        self.assertEqual(r.status_code, 200)
        items = r.json().get("data", {}).get("items", [])
        self.assertTrue(any(p.get("id") == self.producto.id for p in items))

    def test_detalle_producto_sin_auth(self):
        r = self.client.get(f"/api/v1/producto/{self.producto.id}/")
        self.assertEqual(r.status_code, 200)

    def _admin_token(self) -> str:
        r = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"correo_electronico": "admin.prod@test.com", "contrasena": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        return r.json()["data"]["access"]

    def test_patch_estado_admin(self):
        token = self._admin_token()
        r = self.client.patch(
            f"/api/v1/producto/{self.producto.id}/estado/",
            data=json.dumps({"activar": False}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(r.status_code, 200)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
