import os
import sys
import django

# 1. Agregamos la carpeta raíz al path de Python
# Esto permite que 'import Technova' funcione correctamente
ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_proyecto not in sys.path:
    sys.path.append(ruta_proyecto)

# 2. Configuramos el entorno de Django (Asegúrate que Technova sea con T mayúscula si así se llama la carpeta)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Technova.settings_dev')
django.setup()

# 3. IMPORTANTE: Las importaciones de Django deben ir DESPUÉS de django.setup()
# Si las pones al principio, fallará porque los settings aún no cargan.
from django.core.mail import send_mail
from django.conf import settings

# Enviar un correo de prueba
try:
    send_mail(
        subject='Correo de prueba desde Django',
        message='¡Holaaa! Este es un correo de prueba enviado desde tu proyecto Technova.',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=['technovaprueba@gmail.com'],  # Reemplaza con tu correo real
        fail_silently=False,
    )
    print("Correo de prueba enviado correctamente ✅")
except Exception as e:
    print(f"Error al enviar el correo: {e}")


