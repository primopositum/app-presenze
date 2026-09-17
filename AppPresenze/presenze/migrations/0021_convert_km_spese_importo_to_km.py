from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def convert_km_importo_to_km(apps, schema_editor):
    spesa_model = apps.get_model("presenze", "Spesa")

    for spesa in spesa_model.objects.filter(type=2).select_related("trasferta__automobile"):
        automobile = getattr(spesa.trasferta, "automobile", None)
        coefficiente = Decimal(str(getattr(automobile, "coefficiente", Decimal("0.00")) or Decimal("0.00")))
        if coefficiente <= 0:
            continue

        spesa.importo = (Decimal(str(spesa.importo)) / coefficiente).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        spesa.save(update_fields=["importo"])


def convert_km_importo_to_euro(apps, schema_editor):
    spesa_model = apps.get_model("presenze", "Spesa")

    for spesa in spesa_model.objects.filter(type=2).select_related("trasferta__automobile"):
        automobile = getattr(spesa.trasferta, "automobile", None)
        coefficiente = Decimal(str(getattr(automobile, "coefficiente", Decimal("0.00")) or Decimal("0.00")))
        if coefficiente <= 0:
            continue

        spesa.importo = (Decimal(str(spesa.importo)) * coefficiente).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        spesa.save(update_fields=["importo"])


class Migration(migrations.Migration):
    dependencies = [
        ("presenze", "0020_jira_control_column"),
    ]

    operations = [
        migrations.RunPython(convert_km_importo_to_km, convert_km_importo_to_euro),
    ]
