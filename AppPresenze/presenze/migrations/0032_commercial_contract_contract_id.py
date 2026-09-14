from django.db import migrations, models


def populate_legacy_contract_ids(apps, schema_editor):
    ContrattoCliente = apps.get_model("presenze", "ContrattoCliente")
    for contract in ContrattoCliente.objects.filter(contract_id__isnull=True).iterator():
        contract.contract_id = f"LEGACY-{contract.pk}"
        contract.save(update_fields=["contract_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0031_commercial_contract_periodicity"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrattocliente",
            name="contract_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name="contract ID"),
        ),
        migrations.RunPython(populate_legacy_contract_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contrattocliente",
            name="contract_id",
            field=models.CharField(
                help_text="Human-friendly unique contract identifier.",
                max_length=100,
                unique=True,
                verbose_name="contract ID",
            ),
        ),
    ]
