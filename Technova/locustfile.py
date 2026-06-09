"""
Pruebas de carga Locust para TECHNOVA (HU-001 … HU-013).

Requisitos:
  pip install -r requirements-locust.txt
  python manage.py create_locust_client   # usuario cliente de prueba
  python manage.py runserver              # en otra terminal

Variables de entorno (opcionales):
  LOCUST_HOST          → http://localhost:8000
  LOCUST_CLIENT_EMAIL  → cliente.locust@technova.local
  LOCUST_CLIENT_PASSWORD → Prueba123!

Ejemplos:
  locust -f locustfile.py
  locust -f locustfile.py --headless -u 20 -r 2 -t 5m
  locust -f locustfile.py --tags HU-003 HU-007
  locust -f locustfile.py RegistroLocustUser --headless -u 2 -r 1 -t 1m
"""

from __future__ import annotations

import os
import re
from random import choice

from locust import HttpUser, between, events, tag, task

LOCUST_HOST = os.environ.get("LOCUST_HOST", "http://localhost:8000")
CLIENT_EMAIL = os.environ.get("LOCUST_CLIENT_EMAIL", "cliente.locust@technova.local")
CLIENT_PASSWORD = os.environ.get("LOCUST_CLIENT_PASSWORD", "Prueba123!")

_CSRF_INPUT_RE = re.compile(
    r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
    re.IGNORECASE,
)
_PRODUCTO_ID_RE = re.compile(r'data-producto-id="(\d+)"')
_CARRITO_NEGOCIO_KW = ("stock", "agotado", "no esta disponible", "no encontrado")


def _csrf_from_html(html: str) -> str:
    match = _CSRF_INPUT_RE.search(html or "")
    return match.group(1) if match else ""


def _producto_ids_from_html(html: str) -> list[int]:
    return list({int(m) for m in _PRODUCTO_ID_RE.findall(html or "")})


def _producto_ids_con_stock_from_html(html: str) -> list[int]:
    """Solo productos marcados como disponibles en el catálogo SSR."""
    ids: list[int] = []
    for chunk in re.split(r'<div class="producto"', html or "")[1:]:
        if "producto-stock-badge--no" in chunk:
            continue
        match = _PRODUCTO_ID_RE.search(chunk)
        if match:
            ids.append(int(match.group(1)))
    return list(dict.fromkeys(ids))


def _es_rechazo_negocio_carrito(payload: dict | None) -> bool:
    msg = ((payload or {}).get("message") or "").lower()
    return any(kw in msg for kw in _CARRITO_NEGOCIO_KW)


class TechnovaSessionMixin:
    """Sesión Django + CSRF para la interfaz web."""

    host = LOCUST_HOST
    producto_ids: list[int] = []

    def _csrf_cookie(self) -> str:
        token = self.client.cookies.get("csrftoken", "")
        return token or ""

    def _json_headers(self, referer_path: str = "/inicio/") -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-CSRFToken": self._csrf_cookie(),
            "Referer": f"{self.host.rstrip('/')}{referer_path}",
        }

    def _ensure_producto_ids(self) -> int | None:
        if self.producto_ids:
            return choice(self.producto_ids)
        r = self.client.get("/inicio/", name="HU-003 (cache) Catálogo")
        if r.status_code != 200:
            return None
        self.producto_ids = _producto_ids_con_stock_from_html(r.text)
        if not self.producto_ids:
            self.producto_ids = _producto_ids_from_html(r.text)
        if not self.producto_ids:
            env_id = os.environ.get("LOCUST_PRODUCTO_ID")
            if env_id and env_id.isdigit():
                self.producto_ids = [int(env_id)]
        return choice(self.producto_ids) if self.producto_ids else None

    def _login_cliente(self) -> bool:
        r = self.client.get("/login/", name="HU-002 GET login")
        if r.status_code != 200:
            return False
        token = _csrf_from_html(r.text) or self._csrf_cookie()
        data = {
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD,
        }
        if token:
            data["csrfmiddlewaretoken"] = token
        resp = self.client.post(
            "/login/",
            data=data,
            name="HU-002 Iniciar sesión",
            allow_redirects=False,
        )
        return resp.status_code in (200, 302)

    def _logout(self) -> None:
        r = self.client.get("/inicio/", name="HU-013 (prep) sesión")
        token = _csrf_from_html(r.text) or self._csrf_cookie()
        data = {}
        if token:
            data["csrfmiddlewaretoken"] = token
        self.client.post("/logout/", data=data, name="HU-013 Cerrar sesión")


@events.test_start.add_listener
def _on_test_start(environment, **_kwargs):
    if environment.parsed_options and getattr(environment.parsed_options, "host", None):
        TechnovaSessionMixin.host = environment.parsed_options.host.rstrip("/")
        ClienteTechnovaUser.host = TechnovaSessionMixin.host
        RegistroLocustUser.host = TechnovaSessionMixin.host


class ClienteTechnovaUser(TechnovaSessionMixin, HttpUser):
    """
    Flujo principal del cliente autenticado (HU-002 … HU-012).
    Pesos orientados a lectura; escrituras ligeras en carrito/favoritos.
    """

    wait_time = between(1, 3)
    weight = 10

    def on_start(self):
        if not self._login_cliente():
            raise RuntimeError(
                f"No se pudo iniciar sesión con {CLIENT_EMAIL}. "
                "Ejecuta: python manage.py create_locust_client"
            )
        self._ensure_producto_ids()

    def on_stop(self):
        self._logout()

    @task(5)
    @tag("HU-003")
    def consultar_catalogo(self):
        r = self.client.get("/inicio/", name="HU-003 Consultar catálogo")
        if r.status_code == 200:
            ids = _producto_ids_con_stock_from_html(r.text) or _producto_ids_from_html(r.text)
            if ids:
                self.producto_ids = ids

    @task(2)
    @tag("HU-003", "HU-005")
    def agregar_al_carrito(self):
        pid = self._ensure_producto_ids()
        if pid is None:
            return
        with self.client.post(
            "/cliente/catalogo/agregar-carrito/",
            json={"producto_id": pid},
            headers=self._json_headers(),
            name="HU-005 Agregar al carrito",
            catch_response=True,
        ) as resp:
            try:
                body = resp.json()
            except ValueError:
                body = None
            if resp.status_code == 200 and (body or {}).get("ok") is True:
                resp.success()
            elif resp.status_code == 400 and _es_rechazo_negocio_carrito(body):
                # Stock agotado / producto no disponible: regla de negocio, no fallo del servidor.
                resp.success()
            else:
                resp.failure(
                    f"status={resp.status_code} "
                    f"{(body or {}).get('message', resp.text[:120])}"
                )

    @task(1)
    @tag("HU-004")
    def toggle_favorito(self):
        pid = self._ensure_producto_ids()
        if pid is None:
            return
        with self.client.post(
            "/cliente/catalogo/toggle-favorito/",
            json={"producto_id": pid},
            headers=self._json_headers(),
            name="HU-004 Gestionar favoritos",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"status={resp.status_code}")

    @task(3)
    @tag("HU-005")
    def ver_carrito(self):
        self.client.get("/carrito/", name="HU-005 Ver carrito")

    @task(1)
    @tag("HU-006")
    def checkout_informacion(self):
        """Solo lectura del flujo de pago (sin PayPal)."""
        self.client.get(
            "/cliente/checkout/informacion/",
            name="HU-006 Checkout información",
        )

    @task(2)
    @tag("HU-007")
    def consultar_pedidos(self):
        self.client.get("/cliente/pedidos/", name="HU-007 Consultar pedidos")

    @task(2)
    @tag("HU-008")
    def consultar_historial(self):
        self.client.get("/cliente/mis-compras/", name="HU-008 Consultar historial")

    @task(1)
    @tag("HU-009")
    def ver_perfil(self):
        self.client.get("/cliente/perfil/", name="HU-009 Ver perfil")

    @task(1)
    @tag("HU-010")
    def consultar_notificaciones(self):
        self.client.get(
            "/cliente/notificaciones/",
            name="HU-010 Consultar notificaciones",
        )

    @task(1)
    @tag("HU-011")
    def consultar_soporte(self):
        self.client.get("/cliente/mensajes/", name="HU-011 Contactar soporte (lista)")

    @task(1)
    @tag("HU-012")
    def consultar_reclamos(self):
        self.client.get("/cliente/reclamos/", name="HU-012 Consultar reclamos")


class RegistroLocustUser(TechnovaSessionMixin, HttpUser):
    """
    HU-001 Registrar usuario. Ejecutar en escenario aparte (pocos usuarios).
    No mezclar con carga alta: crea filas en BD y puede enviar correos.
    """

    wait_time = between(3, 6)
    weight = 0

    @task
    @tag("HU-001")
    def registrar_usuario(self):
        r = self.client.get("/registro/", name="HU-001 GET registro")
        if r.status_code != 200:
            return
        token = _csrf_from_html(r.text) or self._csrf_cookie()
        uid = getattr(self.environment.runner, "user_count", 0) or id(self)
        correo = f"locust{uid}_{os.getpid()}@load.test"
        data = {
            "nombre": "Carga",
            "apellido": "Locust",
            "correo": correo,
            "confirmar-correo": correo,
            "telefono": "3001234567",
            "tipo-doc": "CC",
            "documento": f"9{uid % 1000000000:09d}"[:10],
            "direccion": "Calle prueba 1",
            "password": "Prueba123!",
            "password_confirmation": "Prueba123!",
        }
        if token:
            data["csrfmiddlewaretoken"] = token
        self.client.post(
            "/registro/",
            data=data,
            name="HU-001 Registrar usuario",
            allow_redirects=False,
        )
