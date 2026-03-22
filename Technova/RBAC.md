# RBAC Matrix (API v1)

Roles: `admin`, `empleado`, `cliente`.

Las reglas aplican a **`/api/v1/...`** y al alias **`/api/...`**.

## Auth

- `POST /auth/login/`, `POST /auth/refresh/`: publico (tambien bajo `/api/auth/...` sin `v1`)
- `GET /auth/me/`: autenticado

## Salud

- `GET /health/live/`, `GET /health/ready/` (bajo `/api/v1/` y `/api/`): publico

## Usuario (`/usuario/`)

- `GET /`: `admin`, `empleado`
- `POST /`: registro publico (rol cliente; `admin` puede fijar rol si va autenticado como admin)
- `GET|PUT /{id}/`: titular o `admin` (`PUT` rol/estado solo `admin`)
- `DELETE /{id}/`: `admin`
- `PATCH /{id}/estado/`: `admin`
- `POST /verificar-identidad/`, `/recuperar-contrasena/`, `/activar-cuenta/`: publico
- `GET /verificar-estado/`: publico
- `POST /login/`: publico (devuelve JWT + DTO)

## Proveedor (`/proveedor/`)

- `GET /`: autenticado
- `POST`, `PUT`, `DELETE`, `PATCH .../estado/`: `admin`, `empleado`

## Producto (`/producto/`)

- `GET` catalogo, filtros, detalle: publico
- `POST`, `PUT`, `DELETE`, `PATCH .../estado/`: `admin`, `empleado`

## Caracteristicas (`/caracteristicas/`)

- `GET`: publico
- `POST`, `PUT`, `DELETE`: `admin`, `empleado`

## Compra (`/compra/`)

- `GET /`, `PATCH /{id}/estado/`: `admin`, `empleado`
- `GET /mias/`, `GET /{id}/` (solo si es el titular): autenticado
- `POST /registrar/`: `admin`, `empleado` (empleado no registra para otro usuario)

## Venta (`/venta/`)

- `GET /`, `POST .../anular/`: `admin`, `empleado`
- `GET /mias/`, `GET /{id}/` (titular o staff): autenticado
- `POST /checkout/`: autenticado (carrito del JWT)

## Carrito (`/carrito/`)

- Operaciones autenticadas; `cliente`/`empleado` solo sobre si mismo salvo `admin`

## Favoritos (`/favoritos/`)

- `GET ""`: `admin`, `empleado`
- Resto: autenticado; ownership como carrito (no operar favoritos de otro salvo `admin`)

## Pago (`/pago/`)

- Listados, detalle `GET /{id}/` y mutaciones de pagos: `admin`, `empleado`
- Metodos de usuario (`/pago/metodos-usuario/`): autenticado; propietario o `admin`

## Medios de pago (`/medios-pago/`)

- Todo: `admin`, `empleado`

## User payment methods (`/user-payment-methods/`)

- `GET ""`: `admin`, `empleado`
- `GET|POST /usuario/{id}/`: titular o `admin`

## Envio (`/envio/`)

- Listado, registro, detalle y actualizacion `GET|PUT /{id}/`, baja logica `DELETE /{id}/`, transportadoras anidadas: `admin`, `empleado`

## Transportadoras (`/transportadoras/`)

- Todo: `admin`, `empleado`

## Orden (`/orden/`)

- `GET /`, `GET /{id}/`, `POST /registrar/`, `PATCH /{id}/estado/`: `admin`, `empleado`

## Atencion cliente (`/atencion-cliente/`)

- Solicitudes/reclamos JSON: autenticado; ownership habitual (cliente solo propio)

## Reclamos (`/reclamos/` — alias)

- `GET /usuario/{id}/`: titular o staff
- `GET /estado/{estado}/`, `PUT` responder/cerrar/enviar-admin: `admin`, `empleado`
- `POST /`: autenticado (`usuarioId` propio salvo `admin`)
- `PUT /{id}/evaluar-resolucion/`: titular del reclamo
- `DELETE /{id}/`: titular o `admin`

## Mensajeria (`/mensajeria/`)

- Notificaciones/mensajes internos: segun rutas existentes

## Notificaciones (`/notificaciones/` — alias)

- `GET|POST ""`: `admin`, `empleado`
- Rutas bajo `/usuario/{id}/...`: titular o `admin`

## Mensajes directos (`/mensajes-directos/` — alias)

- `GET ""`, estadisticas, por empleado: `admin`, `empleado` (empleado acotado a su id donde aplica)
- Por usuario/conversacion: participante o staff
- `POST` crear/conversacion/responder: autenticado con reglas de remitente
- `PUT .../marcar-leido/`: participante con permiso de ver el mensaje
