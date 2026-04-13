from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0015_spesa_tragitto"),
    ]

    operations = [
        migrations.CreateModel(
            name="UtilitiesBar",
            fields=[
                ("id", models.BigAutoField(db_column="UB_ID", primary_key=True, serialize=False)),
                ("link", models.URLField(max_length=500)),
                ("colore", models.CharField(help_text="Colore hex, esempio: #ffffff", max_length=20)),
                ("icon", models.CharField(help_text="Nome icona Font Awesome, esempio: fa-solid fa-link", max_length=100)),
                ("posizione", models.PositiveIntegerField(db_index=True, default=0)),
                ("data_creaz", models.DateTimeField(default=django.utils.timezone.now)),
                ("data_upd", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "UtilitiesBar",
                "ordering": ["posizione", "id"],
            },
        ),
    ]
