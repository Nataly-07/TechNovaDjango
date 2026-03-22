import json
from decimal import Decimal

from django.test import Client, TestCase

from producto.models import Producto
from proveedor.models import Proveedor
from usuario.models import Usuario


class OrdenesApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.empleado = Usuario.objects.create(
            nombre_usuario="empleado_ordenes",
            correo_electronico="empleado.ordenes@demo.com",
            contrasena_hash="123456",
            nombres="Empleado",
            apellidos="Ordenes",
            tipo_documento="CC",
            numero_documento="84001",
            telefono="3004000001",
            direccion="Calle 40",
            rol=Usuario.Rol.EMPLEADO,
            activo=True,
        )
        self.cliente = Usuario.objects.create(
            nombre_usuario="cliente_ordenes",
            correo_electronico="cliente.ordenes@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Ordenes",
            tipo_documento="CC",
            numero_documento="84002",
            telefono="3004000002",
            direccion="Calle 41",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
        )
        self.proveedor = Proveedor.objects.create(
            identificacion="900555777",
            nombre="Proveedor Ordenes",
            telefono="3015557777",
            correo_electronico="prov.ordenes@demo.com",
            empresa="Proveedor Ordenes SAS",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="PROD-ORD-1",
            nombre="RAM",
            imagen_url="",
            stock=40,
            proveedor=self.proveedor,
            costo_unitario=Decimal("70"),
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

    def test_cliente_no_puede_registrar_orden(self):
        token = self._token("cliente.ordenes@demo.com")
        response = self.client.post(
            "/api/v1/orden/registrar/",
            data=json.dumps(
                {
                    "proveedor_id": self.proveedor.id,
                    "fecha": "2026-03-21",
                    "items": [
                        {
                            "producto_id": self.producto.id,
                            "cantidad": 2,
                            "precio_unitario": "70",
                            "subtotal": "140",
                        }
                    ],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_empleado_si_puede_registrar_orden(self):
        token = self._token("empleado.ordenes@demo.com")
        response = self.client.post(
            "/api/v1/orden/registrar/",
            data=json.dumps(
                {
                    "proveedor_id": self.proveedor.id,
                    "fecha": "2026-03-21",
                    "items": [
                        {
                            "producto_id": self.producto.id,
                            "cantidad": 2,
                            "precio_unitario": "70",
                            "subtotal": "140",
                        }
                    ],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)

    def test_empleado_lista_y_detalle_orden(self):
        token = self._token("empleado.ordenes@demo.com")
        reg = self.client.post(
            "/api/v1/orden/registrar/",
            data=json.dumps(
                {
                    "proveedor_id": self.proveedor.id,
                    "fecha": "2026-03-21",
                    "items": [
                        {
                            "producto_id": self.producto.id,
                            "cantidad": 1,
                            "precio_unitario": "70",
                            "subtotal": "70",
                        }
                    ],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(reg.status_code, 201)
        orden_id = reg.json()["data"]["id"]

        lst = self.client.get("/api/v1/orden/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(lst.status_code, 200)
        items = lst.json().get("data", {}).get("items", [])
        self.assertTrue(any(o.get("id") == orden_id for o in items))

        det = self.client.get(
            f"/api/v1/orden/{orden_id}/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(det.status_code, 200)
        self.assertEqual(det.json().get("data", {}).get("id"), orden_id)

    def test_empleado_actualiza_estado_orden(self):
        token = self._token("empleado.ordenes@demo.com")
        reg = self.client.post(
            "/api/v1/orden/registrar/",
            data=json.dumps(
                {
                    "proveedor_id": self.proveedor.id,
                    "fecha": "2026-03-22",
                    "items": [
                        {
                            "producto_id": self.producto.id,
                            "cantidad": 1,
                            "precio_unitario": "70",
                            "subtotal": "70",
                        }
                    ],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        orden_id = reg.json()["data"]["id"]
        patch = self.client.patch(
            f"/api/v1/orden/{orden_id}/estado/",
            data=json.dumps({"estado": "recibida"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(patch.status_code, 200)

    def test_cliente_no_lista_ordenes(self):
        token = self._token("cliente.ordenes@demo.com")
        r = self.client.get("/api/v1/orden/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 403)
