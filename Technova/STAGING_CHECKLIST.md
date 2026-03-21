# Staging Release Checklist

## 1) Configuracion de entorno

- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` configurado para staging
- [ ] Secretos fuera de código (env vars): `SECRET_KEY`, DB creds
- [ ] HTTPS habilitado y proxy headers correctos
- [ ] CORS/CSRF configurado para frontend staging

## 2) Base de datos

- [ ] Backup previo de BD staging
- [ ] `python manage.py migrate` ejecutado sin errores
- [ ] `python manage.py check` sin issues
- [ ] Índices/constraints validados en tablas críticas (`pagos`, `ventas`, `envios`)

## 3) Seguridad y autenticacion

- [ ] Login JWT y refresh funcionando
- [ ] Endpoints críticos protegidos por rol (ver `RBAC.md`)
- [ ] Prueba manual de 401/403 por endpoint sensible
- [ ] Validar expiración de access token y renovación con refresh

## 4) Smoke tests funcionales

- [ ] Flujo checkout completo: carrito -> pago -> venta -> envío
- [ ] Reintento de checkout con misma factura retorna idempotencia
- [ ] Anulación de venta revierte stock y reembolsa pago
- [ ] Compras/órdenes/envíos por roles correctos
- [ ] Atencion/mensajería respetan ownership

## 5) Calidad

- [ ] Ejecutar tests: `python manage.py test`
- [ ] Confirmar no warnings críticos en logs
- [ ] Revisar latencia básica de endpoints críticos

## 6) Observabilidad y soporte

- [ ] Logging estructurado activo
- [ ] Health endpoint verificado
- [ ] Plan de rollback documentado (DB + app)
- [ ] Contacto on-call definido para ventana de despliegue
