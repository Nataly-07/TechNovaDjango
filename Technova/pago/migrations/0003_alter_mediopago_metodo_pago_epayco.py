# Generated manually for ePayco integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pago", "0002_alter_mediopago_metodo_pago"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mediopago",
            name="metodo_pago",
            field=models.CharField(
                choices=[
                    ("tarjeta_credito", "Tarjeta de credito"),
                    ("tarjeta_debito", "Tarjeta de debito"),
                    ("pse", "PSE"),
                    ("paypal", "PayPal"),
                    ("epayco", "ePayco"),
                    ("transferencia", "Transferencia"),
                    ("efectivo", "Efectivo"),
                ],
                max_length=30,
            ),
        ),
    ]
