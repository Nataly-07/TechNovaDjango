import json

from django.test import Client, TestCase

from usuarios.models import Usuario


class MensajeriaApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_mens",
            correo_electronico="admin.mens@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Mensajeria",
            tipo_documento="CC",
            numero_documento="86001",
            telefono="3006000001",
            direccion="Calle 60",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.empleado = Usuario.objects.create(
            nombre_usuario="empleado_mens",
            correo_electronico="empleado.mens@demo.com",
            contrasena_hash="123456",
            nombres="Empleado",
            apellidos="Mensajeria",
            tipo_documento="CC",
            numero_documento="86002",
            telefono="3006000002",
            direccion="Calle 61",
            rol=Usuario.Rol.EMPLEADO,
            activo=True,
        )
        self.cliente_a = Usuario.objects.create(
            nombre_usuario="cliente_mens_a",
            correo_electronico="cliente.mens.a@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="A",
            tipo_documento="CC",
            numero_documento="86003",
            telefono="3006000003",
            direccion="Calle 62",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.cliente_b = Usuario.objects.create(
            nombre_usuario="cliente_mens_b",
            correo_electronico="cliente.mens.b@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="B",
            tipo_documento="CC",
            numero_documento="86004",
            telefono="3006000004",
            direccion="Calle 63",
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

    def test_cliente_no_puede_crear_notificacion_para_otro(self):
        token = self._token("cliente.mens.a@demo.com")
        response = self.client.post(
            "/api/v1/mensajeria/notificaciones/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.cliente_b.id,
                    "titulo": "Aviso",
                    "mensaje": "Prueba",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_empleado_no_puede_crear_mensaje_empleado(self):
        token = self._token("empleado.mens@demo.com")
        response = self.client.post(
            "/api/v1/mensajeria/mensajes-empleado/crear/",
            data=json.dumps(
                {
                    "empleado_usuario_id": self.empleado.id,
                    "asunto": "Instruccion",
                    "mensaje": "Texto",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_si_puede_crear_mensaje_empleado(self):
        token = self._token("admin.mens@demo.com")
        response = self.client.post(
            "/api/v1/mensajeria/mensajes-empleado/crear/",
            data=json.dumps(
                {
                    "empleado_usuario_id": self.empleado.id,
                    "asunto": "Instruccion",
                    "mensaje": "Texto",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
