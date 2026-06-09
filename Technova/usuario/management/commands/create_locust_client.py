"""
Crea o actualiza el usuario cliente usado por Locust (locustfile.py).
"""

import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from usuario.application.registro_usuario_service import validar_contrasena_politica
from usuario.models import Usuario


class Command(BaseCommand):
    help = (
        "Crea el usuario cliente de prueba para Locust. "
        "Credenciales por defecto: cliente.locust@technova.local / Prueba123!"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.environ.get("LOCUST_CLIENT_EMAIL", "cliente.locust@technova.local"),
            help="Correo del cliente de carga.",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("LOCUST_CLIENT_PASSWORD", "Prueba123!"),
            help="Contraseña (misma política que registro).",
        )
        parser.add_argument(
            "--nombre-usuario",
            default="cliente_locust",
            help="Nombre de usuario único.",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        password = options["password"]
        nombre_usuario = (options["nombre_usuario"] or "").strip()

        if not email:
            raise CommandError("El correo es obligatorio.")

        err = validar_contrasena_politica(password)
        if err:
            raise CommandError(err)

        existing = Usuario.objects.filter(correo_electronico__iexact=email).first()
        qs_nu = Usuario.objects.filter(nombre_usuario=nombre_usuario)
        if existing:
            qs_nu = qs_nu.exclude(pk=existing.pk)
        if qs_nu.exists() and not existing:
            raise CommandError(
                f"El nombre de usuario '{nombre_usuario}' ya está en uso. "
                "Usa --nombre-usuario con otro valor."
            )

        defaults = {
            "nombre_usuario": nombre_usuario,
            "contrasena_hash": make_password(password),
            "nombres": "Cliente",
            "apellidos": "Locust",
            "tipo_documento": "CC",
            "numero_documento": "8000099901",
            "telefono": "3000000099",
            "direccion": "Calle de pruebas Locust",
            "rol": Usuario.Rol.CLIENTE,
            "activo": True,
            "correo_verificado": True,
        }

        if existing:
            for key, value in defaults.items():
                setattr(existing, key, value)
            if (
                Usuario.objects.filter(numero_documento=defaults["numero_documento"])
                .exclude(pk=existing.pk)
                .exists()
            ):
                existing.numero_documento = f"8{existing.id:09d}"[:10]
            existing.save()
            self.stdout.write(
                self.style.SUCCESS(f"Cliente Locust actualizado: {email} (rol=cliente).")
            )
            return

        if Usuario.objects.filter(numero_documento=defaults["numero_documento"]).exists():
            defaults["numero_documento"] = "8000099902"

        Usuario.objects.create(correo_electronico=email, **defaults)
        self.stdout.write(
            self.style.SUCCESS(
                f"Cliente Locust creado: {email} / {password}\n"
                "Inicia Locust desde Technova/: locust -f locustfile.py"
            )
        )
