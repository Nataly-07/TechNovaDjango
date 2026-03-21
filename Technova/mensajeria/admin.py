from django.contrib import admin

from mensajeria.models import MensajeDirecto, MensajeEmpleado, Notificacion

admin.site.register(MensajeDirecto)
admin.site.register(MensajeEmpleado)
admin.site.register(Notificacion)
