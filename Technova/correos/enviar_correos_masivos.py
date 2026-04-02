import os
import sys
import django
from dotenv import load_dotenv

# 1. Configuración de rutas
# Obtenemos la carpeta raíz (donde está manage.py y el .env)
ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_proyecto not in sys.path:
    sys.path.append(ruta_proyecto)

# 2. Cargar variables de entorno (Configuración de Postgres y Email)
load_dotenv(os.path.join(ruta_proyecto, '.env'))

# 3. Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Technova.settings_dev")
django.setup()

# 4. Importar TU modelo y herramientas de correo
# Usamos 'usuario' en singular como me indicaste
from usuario.models import Usuario 
from django.core.mail import get_connection, EmailMessage
from django.conf import settings

def enviar_correos_masivos():
    # --- FILTRADO PERSONALIZADO ---
    # Usamos 'activo' y 'correo_electronico' que están en tu models.py
    usuarios = Usuario.objects.filter(activo=True).exclude(correo_electronico="")

    print("--- 👤 Buscando Usuarios en Technova ---")
    conteo = usuarios.count()
    print(f"Usuarios activos con correo: {conteo}")
    print("---------------------------------------")

    if conteo == 0:
        print("❌ No hay usuarios para enviar correos.")
        return

    # --- CONFIGURACIÓN DEL MENSAJE ---
    subject = "Promoción Especial Technova 💻📱"
    from_email = settings.EMAIL_HOST_USER

    try:
        # Abrimos una sola conexión para ser más eficientes
        connection = get_connection()
        connection.open()
        
        mensajes = []
        for usuario in usuarios:
            # Personalizamos con 'nombres' de tu modelo
            cuerpo = f"¡Hola {usuario.nombres}!\n\nTenemos ofertas especiales en celulares y computadores para ti."
            
            email = EmailMessage(
                subject,
                cuerpo,
                from_email,
                [usuario.correo_electronico],
                connection=connection,
            )
            mensajes.append(email)

        # Enviamos todos los correos juntos
        print(f"Enviando {len(mensajes)} correos... por favor espera.")
        connection.send_messages(mensajes)
        
        # Cerramos la conexión
        connection.close()
        
        print("\n¡Proceso completado con éxito! ✅")

    except Exception as e:
        print(f"\n🔴 Ocurrió un error: {e}")

if __name__ == "__main__":
    enviar_correos_masivos()