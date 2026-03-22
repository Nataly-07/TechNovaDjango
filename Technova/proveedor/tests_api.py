import json

from django.test import Client, TestCase

from proveedor.models import Proveedor
from usuario.models import Usuario


class ProveedorApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.proveedor = Proveedor.objects.create(
            identificacion="900333444",
            nombre="Proveedor API Test",
            telefono="3003334444",
            correo_electronico="prov.api@test.com",
            empresa="API SAS",
            activo=True,
        )
        self.user = Usuario.objects.create(
            nombre_usuario="cliente_prov",
            correo_electronico="cliente.prov@test.com",
            contrasena_hash="123456",
            nombres="Cli",
            apellidos="Prov",
            tipo_documento="CC",
            numero_documento="88001",
            telefono="30088001",
            direccion="Calle 2",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )

    def _token(self) -> str:
        r = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"correo_electronico": "cliente.prov@test.com", "contrasena": "123456"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        return r.json()["data"]["access"]

    def test_listado_sin_token_401(self):
        r = self.client.get("/api/v1/proveedor/")
        self.assertEqual(r.status_code, 401)

    def test_listado_con_token_ok(self):
        token = self._token()
        r = self.client.get("/api/v1/proveedor/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 200)
        items = r.json().get("data", {}).get("items", [])
        self.assertTrue(any(p.get("id") == self.proveedor.id for p in items))
