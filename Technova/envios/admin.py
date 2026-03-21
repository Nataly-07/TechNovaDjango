from django.contrib import admin

from envios.models import Envio, Transportadora

admin.site.register(Transportadora)
admin.site.register(Envio)
