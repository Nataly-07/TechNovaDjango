"""
Crea o actualiza un usuario Technova con rol administrador (modelo Usuario, no Django superuser).
"""

import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from usuario.application.registro_usuario_service import validar_contrasena_politica
from usuario.models import Usuario


class Command(BaseCommand):
    help = (
        "Crea el primer usuario con rol 'admin' (login web y API JWT). "
        "Si el correo ya existe, actualiza contrasena y rol a admin."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.environ.get("TECHNOVA_ADMIN_EMAIL", "admin@technova.local"),
            help="Correo del administrador (unico).",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("TECHNOVA_ADMIN_PASSWORD"),
            help="Contrasena (misma politica que registro). Opcional si define TECHNOVA_ADMIN_PASSWORD.",
        )
        parser.add_argument(
            "--nombre-usuario",
            default="admin_technova",
            help="Nombre de usuario unico en el sistema.",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        password = options["password"]
        nombre_usuario = (options["nombre_usuario"] or "").strip()

        if not email:
            raise CommandError("El correo es obligatorio.")
        if not password:
            raise CommandError(
                "Indica --password o la variable de entorno TECHNOVA_ADMIN_PASSWORD."
            )

        err = validar_contrasena_politica(password)
        if err:
            raise CommandError(err)

        existing_email = Usuario.objects.filter(correo_electronico__iexact=email).first()
        qs_nu = Usuario.objects.filter(nombre_usuario=nombre_usuario)
        if existing_email:
            qs_nu = qs_nu.exclude(pk=existing_email.pk)
        existing_nu = qs_nu.exists()
        if existing_nu and not existing_email:
            raise CommandError(
                f"El nombre de usuario '{nombre_usuario}' ya esta en uso. Usa --nombre-usuario otro valor."
            )

        defaults = {
            "nombre_usuario": nombre_usuario,
            "contrasena_hash": make_password(password),
            "nombres": "Administrador",
            "apellidos": "Technova",
            "tipo_documento": "CC",
            "numero_documento": "9000000001",
            "telefono": "3000000000",
            "direccion": "Oficina principal",
            "rol": Usuario.Rol.ADMIN,
            "activo": True,
            "correo_verificado": True,
        }

        if existing_email:
            for k, v in defaults.items():
                setattr(existing_email, k, v)
            # Evitar choque de documento con otro usuario
            if (
                Usuario.objects.filter(numero_documento=defaults["numero_documento"])
                .exclude(pk=existing_email.pk)
                .exists()
            ):
                existing_email.numero_documento = f"9{existing_email.id:09d}"[:10]
            existing_email.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Usuario actualizado: admin listo para '{email}' (rol=admin)."
                )
            )
            return

        if Usuario.objects.filter(numero_documento=defaults["numero_documento"]).exists():
            defaults["numero_documento"] = "9000000002"

        Usuario.objects.create(correo_electronico=email, **defaults)
        self.stdout.write(
            self.style.SUCCESS(
                f"Administrador creado: {email} (rol=admin). Puedes iniciar sesion en /login/ o por API JWT."
            )
        )
