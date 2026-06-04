from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0021_convert_km_spese_importo_to_km"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timeentry",
            name="type",
            field=models.IntegerField(
                choices=[
                    (1, "Lavoro ordinario"),
                    (2, "Ferie"),
                    (3, "Versamento banca ore"),
                    (4, "Prelievo banca ore"),
                    (5, "Malattia"),
                    (6, "Permesso ordinario"),
                    (7, "Permesso studio"),
                    (8, "Permesso 104"),
                    (9, "Permesso ex festività"),
                    (10, "Permesso R.O.L."),
                    (11, "Congedo maternità/paternità"),
                    (12, "Sciopero"),
                    (13, "Festività"),
                    (14, "Visite mediche L.106/25"),
                    (15, "Ricovero presso struttura ospedaliera"),
                ]
            ),
        ),
    ]
