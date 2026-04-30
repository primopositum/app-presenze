from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0018_alter_spesa_type_alter_timeentry_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trasferta",
            name="validation_level",
            field=models.IntegerField(
                choices=[
                    (0, "Compilato automaticamente"),
                    (1, "Validato dall'utente"),
                    (2, "Validato dall'amministratore"),
                ],
                default=0,
            ),
        ),
    ]
