import django.contrib.postgres.fields
import django.db.models.deletion
import presenze.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0029_remove_jira_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=255)),
                ("indirizzo", models.CharField(blank=True, default="", max_length=255)),
                ("telefono", models.CharField(blank=True, default="", max_length=50)),
            ],
            options={"db_table": "Cliente", "ordering": ["nome", "id"]},
        ),
        migrations.CreateModel(
            name="ContrattoCliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.DecimalField(decimal_places=2, max_digits=12)),
                ("pool_task", django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=255), blank=True, default=list, size=None, validators=[presenze.models.validate_pool_task])),
                ("data_creazione", models.DateField()),
                ("data_fine", models.DateField()),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contratti_commerciali", to="presenze.cliente")),
            ],
            options={"db_table": "ContrattoCliente", "ordering": ["-data_creazione", "-id"]},
        ),
    ]
