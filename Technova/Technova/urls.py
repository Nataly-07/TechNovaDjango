"""
URL configuration for Technova project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.health_views import health_live, health_ready

urlpatterns = [
    path("", include("web.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/health/live/", health_live, name="health_live"),
    path("api/v1/health/ready/", health_ready, name="health_ready"),
    path("api/health/live/", health_live, name="health_live_alias"),
    path("api/health/ready/", health_ready, name="health_ready_alias"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api_schema"),
        name="api_docs",
    ),
    path("api/v1/auth/", include("usuario.auth_urls")),
    path("api/auth/", include("usuario.auth_urls")),
    path("api/v1/usuario/", include("usuario.urls")),
    path("api/v1/proveedor/", include("proveedor.urls")),
    path("api/v1/producto/", include("producto.urls")),
    path("api/v1/caracteristicas/", include("producto.caracteristica_urls")),
    path("api/v1/reclamos/", include("atencion_cliente.reclamos_urls")),
    path("api/v1/mensajes-directos/", include("mensajeria.mensajes_directos_urls")),
    path("api/v1/notificaciones/", include("mensajeria.notificaciones_urls")),
    path("api/v1/transportadoras/", include("envio.transportadoras_urls")),
    path("api/v1/medios-pago/", include("pago.medios_pago_urls")),
    path("api/v1/user-payment-methods/", include("pago.user_payment_methods_urls")),
    path("api/v1/compra/", include("compra.urls")),
    path("api/v1/venta/", include("venta.urls")),
    path("api/v1/favoritos/", include("carrito.favoritos_urls")),
    path("api/v1/carrito/", include("carrito.urls")),
    path("api/v1/pago/", include("pago.urls")),
    path("api/v1/envio/", include("envio.urls")),
    path("api/v1/orden/", include("orden.urls")),
    path("api/v1/atencion-cliente/", include("atencion_cliente.urls")),
    path("api/v1/mensajeria/", include("mensajeria.urls")),
    path("api/proveedor/", include("proveedor.urls")),
    path("api/usuario/", include("usuario.urls")),
    path("api/producto/", include("producto.urls")),
    path("api/caracteristicas/", include("producto.caracteristica_urls")),
    path("api/reclamos/", include("atencion_cliente.reclamos_urls")),
    path("api/mensajes-directos/", include("mensajeria.mensajes_directos_urls")),
    path("api/notificaciones/", include("mensajeria.notificaciones_urls")),
    path("api/transportadoras/", include("envio.transportadoras_urls")),
    path("api/medios-pago/", include("pago.medios_pago_urls")),
    path("api/user-payment-methods/", include("pago.user_payment_methods_urls")),
    path("api/compra/", include("compra.urls")),
    path("api/venta/", include("venta.urls")),
    path("api/favoritos/", include("carrito.favoritos_urls")),
    path("api/carrito/", include("carrito.urls")),
    path("api/pago/", include("pago.urls")),
    path("api/envio/", include("envio.urls")),
    path("api/orden/", include("orden.urls")),
    path("api/atencion-cliente/", include("atencion_cliente.urls")),
    path("api/mensajeria/", include("mensajeria.urls")),
]
