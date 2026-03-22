from django.contrib import admin

from pago.models import MedioPago, MetodoPagoUsuario, Pago

admin.site.register(Pago)
admin.site.register(MedioPago)
admin.site.register(MetodoPagoUsuario)
