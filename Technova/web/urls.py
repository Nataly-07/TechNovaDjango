from django.urls import path

from usuario.adapters.web.session_views import (
    home_portal,
    login_web,
    logout_web,
    registro_web,
)
from web import views

urlpatterns = [
    path("", views.root_entry, name="root"),
    path("inicio/", views.home, name="inicio_autenticado"),
    path("admin/perfil/", views.perfil_admin, name="web_admin_perfil"),
    path("admin/usuarios/crear/", views.admin_usuario_crear, name="web_admin_usuario_crear"),
    path(
        "admin/usuarios/<int:usuario_id>/estado/",
        views.admin_usuario_estado,
        name="web_admin_usuario_estado",
    ),
    path("admin/usuarios/", views.admin_usuarios, name="web_admin_usuarios"),
    path("admin/inventario/producto/crear/", views.admin_producto_crear, name="web_admin_producto_crear"),
    path(
        "admin/inventario/producto/<int:producto_id>/estado/",
        views.admin_producto_estado,
        name="web_admin_producto_estado",
    ),
    path("admin/inventario/", views.admin_inventario, name="web_admin_inventario"),
    path("login/", login_web, name="web_login"),
    path("logout/", logout_web, name="web_logout"),
    path("registro/", registro_web, name="web_registro"),
    path("cuenta/", home_portal, name="home_portal"),
    path("cliente/perfil/editar/", views.perfil_editar, name="web_cliente_perfil_editar"),
    path("cliente/perfil/desactivar/", views.perfil_desactivar, name="web_cliente_perfil_desactivar"),
    path("cliente/perfil/", views.perfil_cliente, name="web_cliente_perfil"),
    path("favoritos/", views.favoritos_page, name="web_favoritos"),
    path("cliente/notificaciones/", views.notificaciones_cliente, name="web_cliente_notificaciones"),
    path("carrito/", views.carrito_page, name="web_carrito"),
    path("cliente/pedidos/", views.pedidos_cliente, name="web_cliente_pedidos"),
    path("cliente/mis-compras/", views.mis_compras, name="web_cliente_mis_compras"),
    path("cliente/atencion-cliente/", views.atencion_cliente, name="web_cliente_atencion"),
    path("producto/<int:producto_id>/", views.producto_detalle, name="web_producto_detalle"),
]
