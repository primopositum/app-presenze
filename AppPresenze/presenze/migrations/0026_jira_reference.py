from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0025_utilitiesbar_nome"),
    ]

    operations = [
        migrations.CreateModel(
            name="JiraReference",
            fields=[
                ("id", models.BigAutoField(db_column="ID", primary_key=True, serialize=False)),
                ("name", models.CharField(db_column="Name", max_length=255)),
                ("price", models.FloatField(db_column="price")),
            ],
            options={
                "db_table": "JiraReference",
                "ordering": ["name", "id"],
            },
        ),
    ]
