from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0014_trasferta_tragitto"),
    ]

    operations = [
        migrations.AddField(
            model_name="spesa",
            name="tragitto",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=500),
                blank=True,
                default=list,
                help_text="Lista luoghi del tragitto associati alla spesa chilometrica",
                size=None,
            ),
        ),
    ]
