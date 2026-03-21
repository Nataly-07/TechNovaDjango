# API Contracts v1

Este documento resume los contratos principales de la API para frontend y QA.

## Documentacion OpenAPI

- `GET /api/v1/schema/` (JSON OpenAPI)
- `GET /api/v1/docs/` (Swagger UI)

## Autenticacion

- `POST /api/v1/auth/login/`
  - request:
    - `correo_electronico` (string)
    - `contrasena` (string)
  - response data:
    - `access` (JWT)
    - `refresh` (JWT)
    - `usuario` (`id`, `correo_electronico`, `nombres`, `apellidos`, `rol`)

- `POST /api/v1/auth/refresh/`
  - request: `refresh` (string)
  - response data: `access` (JWT)

- `GET /api/v1/auth/me/`
  - auth: `Bearer access`
  - response data: perfil del usuario autenticado.

## Ventas Checkout

- `POST /api/v1/ventas/checkout/`
  - auth: `Bearer access`
  - request:
    - `carrito_id` (int)
    - `metodo_pago` (string)
    - `numero_factura` (string, idempotencia)
    - `fecha_factura` (YYYY-MM-DD)
    - `transportadora_id` (int)
    - `numero_guia` (string)
    - `costo_envio` (decimal, opcional)
  - response data:
    - `venta_id` (int)
    - `pago_id` (int)
    - `envio_id` (int)
    - `total` (decimal string)
    - `idempotente` (bool)

- `POST /api/v1/ventas/{venta_id}/anular/`
  - auth: `admin` o `empleado`
  - response data:
    - `venta_id`
    - `pagos_reembolsados`
    - `items_revertidos`

## Pagos

- `POST /api/v1/pagos/{pago_id}/estado/`
  - auth: `admin` o `empleado`
  - request: `estado_pago`
  - transiciones:
    - `pendiente -> aprobado | rechazado`
    - `aprobado -> reembolsado`
    - `rechazado -> pendiente`
  - response data:
    - `id`
    - `estado_pago`
    - `fecha_pago`

## Carrito y Favoritos

- `POST /api/v1/carrito/crear/`
- `POST /api/v1/carrito/favoritos/crear/`
  - auth: usuario autenticado
  - ownership:
    - `cliente` no puede crear recursos para otro `usuario_id`
    - `admin` si puede operar para otros usuarios

## Envios

- `POST /api/v1/envios/registrar/`
  - auth: `admin` o `empleado`
  - `cliente` recibe `403`.

## Formato de respuesta

- Exito:
  - `ok = true`
  - `message`
  - `data`
- Error:
  - `ok = false`
  - `message`
  - `details` (opcional)
