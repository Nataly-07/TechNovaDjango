from django.contrib import admin

from ventas.models import DetalleVenta, Venta

admin.site.register(Venta)
admin.site.register(DetalleVenta)
