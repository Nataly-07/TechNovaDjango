# API Contracts v1

Resumen de contratos para frontend y QA. Las mismas rutas existen con prefijo **`/api/v1/`** y, en paralelo, **`/api/`** (alias) salvo que se indique lo contrario.

## Formato de respuesta

- Exito: `ok`, `message`, `data`
- Error: `ok: false`, `message`, `details` (opcional)

## Documentacion OpenAPI

- `GET /api/v1/schema/` (JSON OpenAPI)
- `GET /api/v1/docs/` (Swagger UI)

## Salud y despliegue

- `GET /api/v1/health/live/` y `GET /api/v1/health/ready/` (alias bajo `/api/health/...`) — **publicas**. `live` solo confirma que el proceso responde; `ready` ejecuta `ensure_connection` contra la base de datos (503 si falla).

## CORS (frontend separado)

- Variable de entorno `DJANGO_CORS_ALLOWED_ORIGINS`: URLs separadas por comas (ej. `http://localhost:3000,https://app.midominio.com`).
- Opcional: `DJANGO_CORS_ALLOW_CREDENTIALS=true` si el navegador envia cookies credenciales (la API JWT suele ir solo con `Authorization`).

## Autenticacion

- `POST /api/v1/auth/login/` — publico (`correo_electronico`, `contrasena`) → `access`, `refresh`, `usuario`
- `POST /api/v1/auth/refresh/` — publico (`refresh`) → `access`
- `GET /api/v1/auth/me/` — Bearer
- **Alias:** las mismas rutas bajo `/api/auth/...` (sin `v1`)
- **Login legacy:** `POST /api/v1/usuario/login/` con `email`/`password` (o equivalentes en español) → DTO usuario + JWT

## Usuarios

Base: `/api/v1/usuario/`

- `GET /` — lista (admin, empleado)
- `POST /` — registro (JSON estilo `UsuarioDto` o campos en español)
- `GET|PUT|DELETE /{id}/`
- `PATCH /{id}/estado/?activar=` o body `{"activar": bool}` — admin
- `POST /verificar-identidad/`, `/recuperar-contrasena/`, `/activar-cuenta/`
- `GET /verificar-estado/?email=`

## Proveedores

Base: `/api/v1/proveedor/` — CRUD + `PATCH /{id}/estado/` (admin/empleado para mutaciones; GET autenticado)

## Productos y caracteristicas

- **Productos:** `/api/v1/producto/` — catalogo (`GET|POST ""`), detalle y mutaciones `GET|PUT|DELETE /{id}/`, filtros (`buscar/`, `categoria/`, `marca/`, etc.), `PATCH /{id}/estado/`
- **Caracteristicas (catalogo):** `/api/v1/caracteristicas/` — `GET|POST ""` (POST admin/empleado), `GET|PUT|DELETE /{id}/`

## Ventas y checkout

- `POST /api/v1/venta/checkout/` — Bearer, carrito propio (`carrito_id`, `metodo_pago`, `numero_factura`, `fecha_factura`, `transportadora_id`, `numero_guia`, `costo_envio` opcional)
- `POST /api/v1/venta/{venta_id}/anular/` — admin, empleado
- `GET /api/v1/venta/` — admin, empleado

## Pagos

- `/api/v1/pago/` — listado, registrar, `GET /{pago_id}/`, `POST /{pago_id}/estado/`, metodos guardados del usuario (`metodos-usuario/`)
- **Medios de pago (lineas de venta):** `/api/v1/medios-pago/` — `GET|POST ""`, `GET|PUT|DELETE /{id}/` (admin, empleado). Cuerpo admite `pagoId`, `detalleVentaId`, `usuarioId`, `fechaDeCompra`, etc.
- **User payment methods:** `/api/v1/user-payment-methods/` — `GET ""` (admin/empleado, todos), `GET|POST /usuario/{id}/` (propietario o admin)

## Envios y transportadoras

- `/api/v1/envio/` — envios y transportadoras anidadas como antes
- **Transportadoras (raiz):** `/api/v1/transportadoras/` — `GET|POST ""`, `GET /envio/{envioId}/`, `GET|PUT|DELETE /{id}/` (admin, empleado)

## Carrito y favoritos

- `/api/v1/carrito/` — listados, crear carrito/favoritos, lineas por usuario (`/{usuario_id}/`, `agregar`, `actualizar`, `eliminar`, `vaciar`), `DELETE .../favoritos/{usuario_id}/producto/{producto_id}/`
- `/api/v1/favoritos/` — listado global staff, por usuario, POST/DELETE por producto, toggle

## Compras y ordenes

- **Compras** (`/api/v1/compra/`): `GET /` listado (admin, empleado); `GET /mias/` compras del JWT; `GET /{id}/` detalle (titular o staff); `PATCH /{id}/estado/` body `{"estado": "registrada"|"pagada"|"anulada"}` (admin, empleado); `POST /registrar/` como antes
- **Ordenes** (`/api/v1/orden/`): `GET /` listado; `GET /{id}/` detalle; `PATCH /{id}/estado/` body `{"estado": "pendiente"|"recibida"|"cancelada"}`; `POST /registrar/`

## Atencion al cliente

- `/api/v1/atencion-cliente/` — solicitudes y reclamos (listar/crear JSON existentes)
- **Reclamos:** `/api/v1/reclamos/` — `GET /usuario/{id}/`, `GET /estado/{estado}/`, `GET|DELETE /{id}/`, `POST /` (form o JSON), `PUT /{id}/responder/`, `/cerrar/`, `/enviar-al-admin/`, `/evaluar-resolucion/` (titular)

## Mensajeria

- `/api/v1/mensajeria/` — notificaciones y mensajes (rutas internas actuales)
- **Notificaciones:** `/api/v1/notificaciones/` — `GET|POST ""` (POST admin/empleado), `GET /usuario/{id}/`, `.../leida/?leida=`, `.../rango/?desde=&hasta=`
- **Mensajes directos:** `/api/v1/mensajes-directos/` — listado global (staff), por usuario/empleado/conversacion, crear conversacion, responder, marcar leido, estadisticas
