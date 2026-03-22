from django.contrib import admin

from orden.models import DetalleOrden, OrdenCompra

admin.site.register(OrdenCompra)
admin.site.register(DetalleOrden)
