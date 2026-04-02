from django.urls import path
from . import views

app_name = 'correos'

urlpatterns = [
    # Correos (panel masivo)
    path('panel/', views.panel_correos, name='panel_correos'),
    path('enviar/', views.enviar_correos_masivos, name='enviar_correos'),
    path('historial/', views.historial_envios, name='historial_envios'),
    path('filtrar-usuarios/', views.filtrar_usuarios, name='filtrar_usuarios'),
    
    # Promociones de Productos
    path('promocion-producto/<int:producto_id>/', views.modal_promocion_producto, name='modal_promocion_producto'),
    path('enviar-promocion/<int:producto_id>/', views.enviar_promocion_producto, name='enviar_promocion_producto'),
]
