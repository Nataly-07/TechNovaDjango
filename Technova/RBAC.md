# RBAC Matrix (API v1)

Roles:
- `admin`
- `empleado`
- `cliente`

## Auth

- `POST /api/v1/auth/login/`: publico
- `POST /api/v1/auth/refresh/`: publico
- `GET /api/v1/auth/me/`: autenticado

## Productos

- `GET /api/v1/productos/`: publico/autenticado

## Compras

- `POST /api/v1/compras/registrar/`: `admin`, `empleado`
  - ownership: `empleado` no puede registrar compra para otro usuario.

## Ventas

- `GET /api/v1/ventas/`: `admin`, `empleado`
- `POST /api/v1/ventas/checkout/`: autenticado
  - ownership: solo sobre carrito propio.
- `POST /api/v1/ventas/{venta_id}/anular/`: `admin`, `empleado`

## Carrito

- `GET /api/v1/carrito/`: autenticado (cliente solo sus carritos)
- `POST /api/v1/carrito/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.
- `GET /api/v1/carrito/favoritos/`: autenticado (cliente solo propios)
- `POST /api/v1/carrito/favoritos/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.

## Pagos

- `GET /api/v1/pagos/`: `admin`, `empleado`
- `POST /api/v1/pagos/registrar/`: `admin`, `empleado`
- `POST /api/v1/pagos/{pago_id}/estado/`: `admin`, `empleado`
- `GET /api/v1/pagos/metodos-usuario/`: autenticado (cliente solo propios)
- `POST /api/v1/pagos/metodos-usuario/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.

## Envios

- `GET /api/v1/envios/`: `admin`, `empleado`
- `POST /api/v1/envios/registrar/`: `admin`, `empleado`
- `GET /api/v1/envios/transportadoras/`: `admin`, `empleado`
- `POST /api/v1/envios/transportadoras/crear/`: `admin`, `empleado`

## Ordenes

- `GET /api/v1/ordenes/`: `admin`, `empleado`
- `POST /api/v1/ordenes/registrar/`: `admin`, `empleado`

## Atencion Cliente

- `GET /api/v1/atencion-cliente/solicitudes/`: autenticado (cliente solo propias)
- `POST /api/v1/atencion-cliente/solicitudes/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.
- `GET /api/v1/atencion-cliente/reclamos/`: autenticado (cliente solo propios)
- `POST /api/v1/atencion-cliente/reclamos/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.

## Mensajeria

- `GET /api/v1/mensajeria/notificaciones/`: autenticado (cliente solo propias)
- `POST /api/v1/mensajeria/notificaciones/crear/`: autenticado
  - ownership: `cliente`/`empleado` no crean para otro; `admin` si puede.
- `GET /api/v1/mensajeria/mensajes-directos/`: autenticado (cliente solo conversaciones propias)
- `POST /api/v1/mensajeria/mensajes-directos/crear/`: autenticado
  - ownership: `cliente`/`empleado` no puede enviar como otro remitente; `admin` si puede.
- `GET /api/v1/mensajeria/mensajes-empleado/`: `admin`, `empleado`
- `POST /api/v1/mensajeria/mensajes-empleado/crear/`: `admin`
