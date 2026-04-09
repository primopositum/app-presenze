from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0013_signature_binary_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="trasferta",
            name="tragitto",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=500),
                blank=True,
                default=list,
                help_text="Lista tappe/indirizzi del tragitto",
                size=None,
            ),
        ),
    ]
