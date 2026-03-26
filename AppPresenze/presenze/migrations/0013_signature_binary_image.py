from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("presenze", "0012_signature_signatureevent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signature",
            name="svg",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signature",
            name="image_data",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signature",
            name="mime_type",
            field=models.CharField(default="image/png", max_length=100),
        ),
        migrations.AddField(
            model_name="signature",
            name="file_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
