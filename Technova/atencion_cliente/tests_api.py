import json

from django.test import Client, TestCase

from usuario.models import Usuario


class AtencionClienteApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_atencion",
            correo_electronico="admin.atencion@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Atencion",
            tipo_documento="CC",
            numero_documento="85001",
            telefono="3005000001",
            direccion="Calle 50",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.cliente_a = Usuario.objects.create(
            nombre_usuario="cliente_atencion_a",
            correo_electronico="cliente.atencion.a@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="A",
            tipo_documento="CC",
            numero_documento="85002",
            telefono="3005000002",
            direccion="Calle 51",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.cliente_b = Usuario.objects.create(
            nombre_usuario="cliente_atencion_b",
            correo_electronico="cliente.atencion.b@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="B",
            tipo_documento="CC",
            numero_documento="85003",
            telefono="3005000003",
            direccion="Calle 52",
            rol=Usuario.Rol.CLIENTE,
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

    def test_cliente_no_puede_crear_reclamo_para_otro(self):
        token = self._token("cliente.atencion.a@demo.com")
        response = self.client.post(
            "/api/v1/atencion-cliente/reclamos/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.cliente_b.id,
                    "fecha_reclamo": "2026-03-21T10:00:00",
                    "titulo": "Reclamo test",
                    "descripcion": "Descripcion test",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_si_puede_crear_solicitud_para_otro(self):
        token = self._token("admin.atencion@demo.com")
        response = self.client.post(
            "/api/v1/atencion-cliente/solicitudes/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.cliente_a.id,
                    "fecha_consulta": "2026-03-21T11:00:00",
                    "tema": "Garantia",
                    "descripcion": "Consulta de garantia",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
