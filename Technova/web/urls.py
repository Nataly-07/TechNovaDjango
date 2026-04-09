from django.urls import path

from usuario.adapters.web.session_views import (
    home_portal,
    login_web,
    logout_web,
    registro_web,
)
from web import views
from web.adapters.http import mensajes_web_views as mensajes_web
from web.adapters.http.views_ordenes import (
    admin_ordenes_compra,
    admin_orden_compra_detalle,
    admin_orden_compra_crear,
    admin_orden_compra_cambiar_estado,
    admin_ordenes_compra_api,
)
from web.adapters.http.views_ordenes_test import admin_ordenes_compra_test
from web.adapters.http.ordenes_views import (
    listar_ordenes,
    mostrar_formulario_crear,
    guardar_orden,
    recibir_orden,
    obtener_detalle_orden_api,
)
from web.adapters.http.debug_ordenes import debug_ordenes, debug_ordenes_auth
from web.adapters.http.views_promociones import admin_producto_promocionar, admin_producto_info

urlpatterns = [
    path(
        "api/mensajes-empleado",
        mensajes_web.api_mensajes_empleado_spring,
        name="api_mensajes_empleado_spring",
    ),
    path(
        "api/mensajes-empleado/",
        mensajes_web.api_mensajes_empleado_spring,
        name="api_mensajes_empleado_spring_slash",
    ),
    path("", views.root_entry, name="root"),
    path("inicio/", views.home, name="inicio_autenticado"),
    path(
        "cliente/catalogo/agregar-carrito/",
        views.catalogo_agregar_carrito,
        name="web_catalogo_agregar_carrito",
    ),
    path(
        "cliente/catalogo/toggle-favorito/",
        views.catalogo_toggle_favorito,
        name="web_catalogo_toggle_favorito",
    ),
    path(
        "empleado/",
        views.empleado_dashboard,
        kwargs={"seccion": "inicio"},
        name="web_empleado_inicio",
    ),
    path("empleado/perfil/editar/", views.empleado_perfil_editar, name="web_empleado_perfil_editar"),
    path(
        "empleado/pos/paypal/retorno/",
        views.empleado_pos_paypal_retorno,
        name="web_empleado_pos_paypal_retorno",
    ),
    path(
        "empleado/pos/<int:venta_id>/factura/",
        views.empleado_pos_factura,
        name="web_empleado_pos_factura",
    ),
    path("empleado/mensajes", mensajes_web.empleado_mensajes_page, name="web_empleado_mensajes_noslash"),
    path("empleado/mensajes/", mensajes_web.empleado_mensajes_page, name="web_empleado_mensajes"),
    path(
        "empleado/notificaciones/poll/",
        views.empleado_notificaciones_poll,
        name="web_empleado_notificaciones_poll",
    ),
    path(
        "empleado/notificaciones/",
        views.empleado_notificaciones,
        name="web_empleado_notificaciones",
    ),
    path(
        "empleado/punto-venta/",
        views.empleado_dashboard,
        kwargs={"seccion": "punto-venta"},
        name="web_empleado_punto_venta",
    ),
    path("empleado/<slug:seccion>/", views.empleado_dashboard, name="web_empleado_seccion"),
    path("admin/perfil/editar/", views.admin_perfil_editar, name="web_admin_perfil_editar"),
    path("admin/perfil/", views.perfil_view, name="web_admin_perfil"),
    path("admin/dashboard/", views.dashboard_view, name="web_admin_dashboard"),
    path("admin/notificaciones/poll/", views.admin_notificaciones_poll, name="web_admin_notificaciones_poll"),
    path("admin/notificaciones/", views.admin_notificaciones, name="web_admin_notificaciones"),
    path("admin/mensajes", mensajes_web.admin_mensajes_page, name="web_admin_mensajes_noslash"),
    path("admin/mensajes/", mensajes_web.admin_mensajes_page, name="web_admin_mensajes"),
    path(
        "admin/mensajes/reclamo/<int:reclamo_id>/json",
        mensajes_web.admin_mensajes_reclamo_json,
        name="web_admin_mensajes_reclamo_json_noslash",
    ),
    path(
        "admin/mensajes/reclamo/<int:reclamo_id>/json/",
        mensajes_web.admin_mensajes_reclamo_json,
        name="web_admin_mensajes_reclamo_json",
    ),
    path("admin/reclamos/", mensajes_web.admin_reclamos_gestion, name="web_admin_reclamos"),
    path(
        "admin/reclamos/<int:reclamo_id>/asignar/",
        mensajes_web.admin_reclamos_asignar_sesion,
        name="web_admin_reclamo_asignar",
    ),
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
    path(
        "admin/inventario/producto/<int:producto_id>/editar/",
        views.admin_producto_editar,
        name="web_admin_producto_editar",
    ),
    path(
        "admin/inventario/catalogo/categoria/",
        views.admin_catalogo_categoria_agregar,
        name="web_admin_catalogo_categoria_agregar",
    ),
    path(
        "admin/inventario/catalogo/marca/",
        views.admin_catalogo_marca_agregar,
        name="web_admin_catalogo_marca_agregar",
    ),
    path("admin/inventario/", views.admin_inventario, name="web_admin_inventario"),
    path(
        "admin/inventario/importar-excel/plantilla/",
        views.admin_inventario_plantilla_excel,
        name="web_admin_inventario_plantilla_excel",
    ),
    path(
        "admin/inventario/importar-excel/",
        views.admin_inventario_importar_excel,
        name="web_admin_inventario_importar_excel",
    ),
    path("admin/proveedores/crear/", views.admin_proveedor_crear, name="web_admin_proveedor_crear"),
    path(
        "admin/proveedores/<int:proveedor_id>/estado/",
        views.admin_proveedor_estado,
        name="web_admin_proveedor_estado",
    ),
    path("admin/proveedores/", views.admin_proveedores, name="web_admin_proveedores"),
    # URLs de Órdenes de Compra - Exactamente como en Spring Boot
    path("admin/ordenes/", listar_ordenes, name="web_admin_ordenes_compra"),
    path("admin/ordenes/crear/", mostrar_formulario_crear, name="web_admin_orden_compra_crear"),
    path("admin/ordenes/guardar/", guardar_orden, name="web_admin_orden_compra_guardar"),
    path("admin/ordenes/recibir/<int:orden_id>/", recibir_orden, name="web_admin_orden_compra_recibir"),
    path("admin/ordenes/api/<int:orden_id>/", obtener_detalle_orden_api, name="web_admin_ordenes_compra_api"),
    # URLs antiguas (mantener para compatibilidad)
    path("admin/ordenes-compra/", admin_ordenes_compra, name="web_admin_ordenes_compra_old"),
    path("admin/ordenes-compra/test/", admin_ordenes_compra_test, name="web_admin_ordenes_compra_test"),
    path("admin/ordenes-compra/crear/", admin_orden_compra_crear, name="web_admin_orden_compra_crear_old"),
    path("admin/ordenes-compra/<int:orden_id>/", admin_orden_compra_detalle, name="web_admin_orden_compra_detalle"),
    path("admin/ordenes-compra/<int:orden_id>/cambiar-estado/", admin_orden_compra_cambiar_estado, name="web_admin_orden_compra_cambiar_estado"),
    path("admin/ordenes-compra/api/", admin_ordenes_compra_api, name="web_admin_ordenes_compra_api_old"),
    path("admin/reportes/", views.admin_reportes, name="web_admin_reportes"),
    path("admin/reportes/<str:tipo>/preview/", views.admin_reportes_preview, name="web_admin_reportes_preview"),
    path("admin/reportes/<str:tipo>/pdf/", views.admin_reportes_pdf, name="web_admin_reportes_pdf"),
    # URLs de depuración
    path("debug/ordenes/", debug_ordenes, name="debug_ordenes"),
    path("debug/ordenes-auth/", debug_ordenes_auth, name="debug_ordenes_auth"),
    # URLs de promociones
    path("admin/producto/<int:producto_id>/promocionar/", admin_producto_promocionar, name="web_admin_producto_promocionar"),
    path("admin/producto/<int:producto_id>/info/", admin_producto_info, name="web_admin_producto_info"),
    path("admin/pagos/", views.admin_pagos, name="web_admin_pagos"),
    path(
        "admin/pagos/detalle/<int:pago_id>/",
        views.admin_pago_detalle,
        name="web_admin_pago_detalle",
    ),
    path(
        "admin/pagos/factura/<int:pago_id>/",
        views.admin_pago_factura,
        name="web_admin_pago_factura",
    ),
    path(
        "admin/pedidos/<int:venta_id>/",
        views.admin_pedido_detalle,
        name="web_admin_pedido_detalle",
    ),
    path("admin/pedidos/", views.admin_pedidos, name="web_admin_pedidos"),
    path("login/", login_web, name="web_login"),
    path("logout/", logout_web, name="web_logout"),
    path("registro/", registro_web, name="web_registro"),
    path("cuenta/", home_portal, name="home_portal"),
    path("cliente/perfil/editar/", views.perfil_editar, name="web_cliente_perfil_editar"),
    path("cliente/perfil/desactivar/", views.perfil_desactivar, name="web_cliente_perfil_desactivar"),
    path("cliente/perfil/", views.perfil_cliente, name="web_cliente_perfil"),
    path("favoritos/", views.favoritos_page, name="web_favoritos"),
    path("favoritos/quitar/", views.favorito_quitar, name="web_favorito_quitar"),
    path("favoritos/al-carrito/", views.favorito_agregar_carrito, name="web_favorito_al_carrito"),
    path("cliente/notificaciones/", views.notificaciones_cliente, name="web_cliente_notificaciones"),
    path("carrito/actualizar/", views.carrito_actualizar, name="web_carrito_actualizar"),
    path("carrito/eliminar/", views.carrito_eliminar, name="web_carrito_eliminar"),
    path("carrito/vaciar/", views.carrito_vaciar, name="web_carrito_vaciar"),
    path("carrito/", views.carrito_page, name="web_carrito"),
    path(
        "cliente/checkout/informacion/",
        views.checkout_informacion,
        name="web_cliente_checkout_info",
    ),
    path(
        "cliente/checkout/direccion/",
        views.checkout_direccion,
        name="web_cliente_checkout_direccion",
    ),
    path("cliente/checkout/envio/", views.checkout_envio, name="web_cliente_checkout_envio"),
    path("cliente/checkout/pago/", views.checkout_pago, name="web_cliente_checkout_pago"),
    path(
        "cliente/checkout/revision/",
        views.checkout_revision,
        name="web_cliente_checkout_revision",
    ),
    path(
        "cliente/checkout/finalizar/",
        views.checkout_finalizar,
        name="web_cliente_checkout_finalizar",
    ),
    path(
        "cliente/checkout/paypal/iniciar/",
        views.checkout_paypal_iniciar,
        name="web_cliente_checkout_paypal_iniciar",
    ),
    path(
        "cliente/checkout/paypal/retorno/",
        views.checkout_paypal_retorno,
        name="web_cliente_checkout_paypal_retorno",
    ),
    path(
        "cliente/checkout/confirmacion/",
        views.checkout_confirmacion,
        name="web_cliente_checkout_confirmacion",
    ),
    path("cliente/pedidos/", views.pedidos_cliente, name="web_cliente_pedidos"),
    path("cliente/mis-compras/", views.mis_compras, name="web_cliente_mis_compras"),
    path(
        "cliente/mis-compras/<int:venta_id>/factura/",
        views.cliente_factura_compra,
        name="web_cliente_factura_compra",
    ),
    path("cliente/atencion-cliente/", views.atencion_cliente, name="web_cliente_atencion"),
    path("cliente/mensajes", mensajes_web.cliente_mensajes_page, name="web_cliente_mensajes_noslash"),
    path("cliente/mensajes/", mensajes_web.cliente_mensajes_page, name="web_cliente_mensajes"),
    path(
        "cliente/mensajes/nueva/",
        mensajes_web.cliente_mensajes_nueva_conversacion,
        name="web_cliente_mensajes_nueva",
    ),
    path(
        "cliente/mensajes/responder/",
        mensajes_web.cliente_mensajes_responder,
        name="web_cliente_mensajes_responder",
    ),
    path("cliente/reclamos/", views.cliente_reclamos, name="web_cliente_reclamos"),
    path("producto/<int:producto_id>/", views.producto_detalle, name="web_producto_detalle"),
]
