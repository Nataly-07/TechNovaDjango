import re

# Mismas claves de sesión que Spring: checkout_informacion, checkout_direccion, etc.
SESSION_CK_INFO = "checkout_informacion"
SESSION_CK_DIR = "checkout_direccion"
SESSION_CK_ENV = "checkout_envio"
SESSION_CK_PAGO = "checkout_pago"
SESSION_CK_RESULT = "checkout_resultado"
SESSION_CK_PAYPAL = "checkout_paypal"

FACTURA_VENTA_PATTERN = re.compile(r"^FACT-\d+-(\d+)$", re.IGNORECASE)

EMPLEADO_SECCIONES: dict[str, str] = {
    "inicio": "Panel de empleado",
    "perfil": "Mi perfil",
    "usuarios": "Usuarios",
    "mensajes": "Mensajes",
    "productos": "Visualización de artículos",
    "pedidos": "Pedidos",
    "venta-punto-fisico": "Venta punto físico",
    "atencion-cliente": "Atención al cliente",
    "notificaciones": "Notificaciones",
}
