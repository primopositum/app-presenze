from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0024_saldo_json_monthly"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilitiesbar",
            name="nome",
            field=models.CharField(blank=True, default="", max_length=100),
            preserve_default=False,
        ),
    ]
