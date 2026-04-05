import os
import sys
import django
from dotenv import load_dotenv

# 1. Configuración de rutas
ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_proyecto not in sys.path:
    sys.path.append(ruta_proyecto)

# 2. Cargar variables de entorno
load_dotenv(os.path.join(ruta_proyecto, ".env"))

# 3. Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Technova.settings_dev")
django.setup()

from django.conf import settings
from django.core.mail import get_connection, EmailMessage

from usuario.models import Usuario


def _remitente_y_para_visible():
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if not from_email:
        from_email = (getattr(settings, "EMAIL_HOST_USER", None) or "").strip() or "noreply@localhost"
    visible = getattr(settings, "TECHNOVA_BULK_MAIL_VISIBLE_TO", None)
    if visible is None:
        visible = from_email
    else:
        visible = str(visible).strip()
    to_header = [visible] if visible else []
    return from_email, to_header


def enviar_correos_masivos():
    usuarios = Usuario.objects.filter(activo=True).exclude(correo_electronico="")

    print("--- 👤 Buscando Usuarios en Technova ---")
    conteo = usuarios.count()
    print(f"Usuarios activos con correo: {conteo}")
    print("---------------------------------------")

    if conteo == 0:
        print("❌ No hay usuarios para enviar correos.")
        return

    subject = "Promoción Especial Technova 💻📱"
    from_email, to_header = _remitente_y_para_visible()

    connection = get_connection()
    try:
        connection.open()
    except Exception as e:
        print(f"\n🔴 No se pudo conectar al servidor de correo: {e}")
        return

    exitosos = 0
    fallidos = 0
    try:
        for usuario in usuarios:
            correo = (usuario.correo_electronico or "").strip()
            if not correo:
                fallidos += 1
                continue
            cuerpo = (
                f"¡Hola {usuario.nombres}!\n\n"
                "Tenemos ofertas especiales en celulares y computadores para ti."
            )
            try:
                email = EmailMessage(
                    subject,
                    cuerpo,
                    from_email,
                    to_header,
                    bcc=[correo],
                    connection=connection,
                )
                email.send()
                exitosos += 1
            except Exception as e:
                print(f"  ⚠ Fallo a {correo}: {e}")
                fallidos += 1
    finally:
        try:
            connection.close()
        except Exception:
            pass

    print(f"\nEnviados: {exitosos} · Fallidos: {fallidos}")
    if exitosos:
        print("¡Proceso terminado (con al menos un envío exitoso). ✅")


if __name__ == "__main__":
    enviar_correos_masivos()
