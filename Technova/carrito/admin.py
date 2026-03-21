from django.contrib import admin

from carrito.models import Carrito, DetalleCarrito, Favorito

admin.site.register(Carrito)
admin.site.register(DetalleCarrito)
admin.site.register(Favorito)
