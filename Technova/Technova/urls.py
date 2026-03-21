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

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="api_schema"),
        name="api_docs",
    ),
    path("api/v1/auth/", include("usuarios.auth_urls")),
    path("api/v1/productos/", include("productos.urls")),
    path("api/v1/compras/", include("compras.urls")),
    path("api/v1/ventas/", include("ventas.urls")),
    path("api/v1/carrito/", include("carrito.urls")),
    path("api/v1/pagos/", include("pagos.urls")),
    path("api/v1/envios/", include("envios.urls")),
    path("api/v1/ordenes/", include("ordenes.urls")),
    path("api/v1/atencion-cliente/", include("atencion_cliente.urls")),
    path("api/v1/mensajeria/", include("mensajeria.urls")),
    path("api/productos/", include("productos.urls")),
    path("api/compras/", include("compras.urls")),
    path("api/ventas/", include("ventas.urls")),
    path("api/carrito/", include("carrito.urls")),
    path("api/pagos/", include("pagos.urls")),
    path("api/envios/", include("envios.urls")),
    path("api/ordenes/", include("ordenes.urls")),
    path("api/atencion-cliente/", include("atencion_cliente.urls")),
    path("api/mensajeria/", include("mensajeria.urls")),
]
