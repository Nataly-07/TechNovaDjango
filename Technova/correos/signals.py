"""
El envío de bienvenida al registrar un cliente lo gestiona `usuario.signals`
(junto con `usuario.infrastructure.cuenta_correo_email`).

Este módulo se mantiene para que `CorreosConfig.ready()` siga importando
`correos.signals` sin duplicar `post_save` sobre `Usuario`.
"""
