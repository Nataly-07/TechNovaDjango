import json
from datetime import date

from django.test import Client, TestCase

from pago.models import MetodoPagoUsuario, Pago
from usuario.models import Usuario


class PagosApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_pagos",
            correo_electronico="admin.pagos@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Pagos",
            tipo_documento="CC",
            numero_documento="81001",
            telefono="3001000001",
            direccion="Calle 10",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.empleado = Usuario.objects.create(
            nombre_usuario="empleado_pagos",
            correo_electronico="empleado.pagos@demo.com",
            contrasena_hash="123456",
            nombres="Empleado",
            apellidos="Pagos",
            tipo_documento="CC",
            numero_documento="81002",
            telefono="3001000002",
            direccion="Calle 11",
            rol=Usuario.Rol.EMPLEADO,
            activo=True,
        )
        self.cliente = Usuario.objects.create(
            nombre_usuario="cliente_pagos",
            correo_electronico="cliente.pagos@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Pagos",
            tipo_documento="CC",
            numero_documento="81003",
            telefono="3001000003",
            direccion="Calle 12",
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

    def test_cliente_no_puede_crear_metodo_para_otro_usuario(self):
        token = self._token("cliente.pagos@demo.com")
        response = self.client.post(
            "/api/v1/pago/metodos-usuario/crear/",
            data=json.dumps(
                {
                    "usuario_id": self.empleado.id,
                    "metodo_pago": "pse",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MetodoPagoUsuario.objects.count(), 0)

    def test_admin_actualiza_estado_pago(self):
        pago = Pago.objects.create(
            fecha_pago=date.today(),
            numero_factura="FAC-PAGOS-API-1",
            fecha_factura=date.today(),
            monto="100",
            estado_pago=Pago.EstadoPago.PENDIENTE,
        )
        token = self._token("admin.pagos@demo.com")
        response = self.client.post(
            f"/api/v1/pago/{pago.id}/estado/",
            data=json.dumps({"estado_pago": "aprobado"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        pago.refresh_from_db()
        self.assertEqual(pago.estado_pago, Pago.EstadoPago.APROBADO)
