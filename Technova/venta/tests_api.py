import json
from datetime import date
from decimal import Decimal

from django.test import Client, TestCase

from carrito.models import Carrito, DetalleCarrito
from envio.models import Transportadora
from pago.models import Pago
from producto.models import Producto
from proveedor.models import Proveedor
from usuario.models import Usuario
from venta.models import Venta


class VentasApiJwtTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create(
            nombre_usuario="admin_demo",
            correo_electronico="admin@demo.com",
            contrasena_hash="123456",
            nombres="Admin",
            apellidos="Demo",
            tipo_documento="CC",
            numero_documento="90001",
            telefono="3001000000",
            direccion="Calle Admin",
            rol=Usuario.Rol.ADMIN,
            activo=True,
        )
        self.cliente = Usuario.objects.create(
            nombre_usuario="cliente_demo_api",
            correo_electronico="clienteapi@demo.com",
            contrasena_hash="123456",
            nombres="Cliente",
            apellidos="Api",
            tipo_documento="CC",
            numero_documento="90002",
            telefono="3002000000",
            direccion="Calle Cliente",
            rol=Usuario.Rol.CLIENTE,
            activo=True,
            correo_verificado=True,
        )
        self.proveedor = Proveedor.objects.create(
            identificacion="900555111",
            nombre="Proveedor API",
            telefono="3015551111",
            correo_electronico="proveedorapi@demo.com",
            empresa="Proveedor API SAS",
            activo=True,
        )
        self.producto = Producto.objects.create(
            codigo="P-API-1",
            nombre="Teclado",
            imagen_url="",
            stock=5,
            proveedor=self.proveedor,
            costo_unitario=Decimal("50"),
            activo=True,
        )
        self.transportadora = Transportadora.objects.create(
            nombre="Trans API",
            telefono="3023333333",
            correo_electronico="transapi@demo.com",
            activo=True,
        )

    def _token(self, correo: str, contrasena: str) -> str:
        response = self.client.post(
            "/api/v1/auth/login/",
            data=json.dumps({"correo_electronico": correo, "contrasena": contrasena}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        return payload["data"]["access"]

    def test_checkout_api_idempotente(self):
        carrito = Carrito.objects.create(usuario=self.cliente, estado=Carrito.Estado.ACTIVO)
        DetalleCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=2)
        token = self._token("clienteapi@demo.com", "123456")

        payload = {
            "carrito_id": carrito.id,
            "metodo_pago": "pse",
            "numero_factura": "FAC-API-1",
            "fecha_factura": date.today().isoformat(),
            "transportadora_id": self.transportadora.id,
            "numero_guia": "GUIA-API-1",
            "costo_envio": "5",
        }
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

        primera = self.client.post(
            "/api/v1/venta/checkout/",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )
        segunda = self.client.post(
            "/api/v1/venta/checkout/",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(segunda.status_code, 200)
        self.assertFalse(primera.json()["data"]["idempotente"])
        self.assertTrue(segunda.json()["data"]["idempotente"])
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(Pago.objects.count(), 1)

    def test_anular_venta_api_reembolsa_pago(self):
        carrito = Carrito.objects.create(usuario=self.cliente, estado=Carrito.Estado.ACTIVO)
        DetalleCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=1)

        token_cliente = self._token("clienteapi@demo.com", "123456")
        checkout_payload = {
            "carrito_id": carrito.id,
            "metodo_pago": "pse",
            "numero_factura": "FAC-API-2",
            "fecha_factura": date.today().isoformat(),
            "transportadora_id": self.transportadora.id,
            "numero_guia": "GUIA-API-2",
            "costo_envio": "0",
        }
        checkout_resp = self.client.post(
            "/api/v1/venta/checkout/",
            data=json.dumps(checkout_payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token_cliente}",
        )
        self.assertEqual(checkout_resp.status_code, 201)
        venta_id = checkout_resp.json()["data"]["venta_id"]
        pago_id = checkout_resp.json()["data"]["pago_id"]

        token_admin = self._token("admin@demo.com", "123456")
        anular_resp = self.client.post(
            f"/api/v1/venta/{venta_id}/anular/",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token_admin}",
        )
        self.assertEqual(anular_resp.status_code, 200)

        pago = Pago.objects.get(id=pago_id)
        self.assertEqual(pago.estado_pago, Pago.EstadoPago.REEMBOLSADO)
