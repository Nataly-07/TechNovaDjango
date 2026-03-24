from django.db import migrations, models


def epayco_a_paypal(apps, schema_editor):
    MedioPago = apps.get_model("pago", "MedioPago")
    MedioPago.objects.filter(metodo_pago="epayco").update(metodo_pago="paypal")


class Migration(migrations.Migration):

    dependencies = [
        ("pago", "0003_alter_mediopago_metodo_pago_epayco"),
    ]

    operations = [
        migrations.RunPython(epayco_a_paypal, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="mediopago",
            name="metodo_pago",
            field=models.CharField(
                choices=[
                    ("tarjeta_credito", "Tarjeta de credito"),
                    ("tarjeta_debito", "Tarjeta de debito"),
                    ("pse", "PSE"),
                    ("paypal", "PayPal"),
                    ("transferencia", "Transferencia"),
                    ("efectivo", "Efectivo"),
                ],
                max_length=30,
            ),
        ),
    ]
