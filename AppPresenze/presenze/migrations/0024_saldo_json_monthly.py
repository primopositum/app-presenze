from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0023_remove_saldo_valore_saldo_sospeso_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="saldo",
            name="valore_saldo_validato",
        ),
        migrations.RemoveField(
            model_name="saldo",
            name="saldo_progressivo",
        ),
        migrations.AddField(
            model_name="saldo",
            name="saldo",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
