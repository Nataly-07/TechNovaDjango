"""
Cierra promociones de productos cuya fecha_fin_promocion ya pasó.

Programar en el servidor (ejemplos):
  Linux cron (cada hora): 0 * * * * cd /ruta/Technova && python manage.py expirar_promociones
  Windows Programador de tareas: ejecutar el mismo comando con manage.py del proyecto.
"""

from django.core.management.base import BaseCommand

from web.application.promociones_admin import cerrar_promociones_productos_vencidas


class Command(BaseCommand):
    help = "Anula precio_promocion en productos con fecha de fin de promoción vencida."

    def handle(self, *args, **options):
        n = cerrar_promociones_productos_vencidas()
        self.stdout.write(self.style.SUCCESS(f"Promociones cerradas automáticamente: {n} producto(s)."))
