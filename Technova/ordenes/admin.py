from django.contrib import admin

from ordenes.models import DetalleOrden, OrdenCompra

admin.site.register(OrdenCompra)
admin.site.register(DetalleOrden)
