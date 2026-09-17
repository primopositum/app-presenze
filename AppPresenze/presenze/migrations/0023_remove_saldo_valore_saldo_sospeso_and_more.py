from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0022_alter_timeentry_type_ricovero"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="saldo",
            name="valore_saldo_sospeso",
        ),
        migrations.AddField(
            model_name="saldo",
            name="saldo_progressivo",
            field=ArrayField(
                base_field=models.DecimalField(decimal_places=2, max_digits=10),
                blank=True,
                default=list,
                size=None,
            ),
        ),
    ]
