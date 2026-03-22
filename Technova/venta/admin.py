from django.contrib import admin

from venta.models import DetalleVenta, Venta

admin.site.register(Venta)
admin.site.register(DetalleVenta)
