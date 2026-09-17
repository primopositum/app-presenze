from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presenze", "0030_cliente_contrattocliente"),
    ]

    operations = [
        migrations.RenameField(
            model_name="contrattocliente",
            old_name="cliente",
            new_name="client",
        ),
        migrations.RenameField(
            model_name="contrattocliente",
            old_name="data_creazione",
            new_name="start_date",
        ),
        migrations.RenameField(
            model_name="contrattocliente",
            old_name="data_fine",
            new_name="end_date",
        ),
        migrations.AlterField(
            model_name="contrattocliente",
            name="client",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="commercial_contracts",
                to="presenze.cliente",
            ),
        ),
        migrations.AlterField(
            model_name="contrattocliente",
            name="end_date",
            field=models.DateField(blank=True, null=True, verbose_name="end date"),
        ),
        migrations.AlterField(
            model_name="contrattocliente",
            name="value",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Total contract value as signed.",
                max_digits=12,
                validators=[MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddField(
            model_name="contrattocliente",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name="created at"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="contrattocliente",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name="updated at"),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="contrattocliente",
            options={"ordering": ["-start_date", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="contrattocliente",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_date__isnull", True), ("end_date__gte", models.F("start_date")), _connector="OR"),
                name="commercial_contract_dates_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="contrattocliente",
            constraint=models.CheckConstraint(condition=models.Q(("value__gt", 0)), name="commercial_contract_value_positive"),
        ),
        migrations.AddIndex(
            model_name="contrattocliente",
            index=models.Index(fields=["start_date"], name="commercial_contract_start_idx"),
        ),
        migrations.CreateModel(
            name="Periodicita",
            fields=[
                (
                    "contract",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="periodicity",
                        serialize=False,
                        to="presenze.contrattocliente",
                        verbose_name="contract",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="updated at"),
                ),
                (
                    "periodic_value",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        validators=[MinValueValidator(Decimal("0.01"))],
                        verbose_name="periodic value",
                    ),
                ),
                (
                    "period_days",
                    models.PositiveIntegerField(
                        help_text="Duration of the period in days.",
                        validators=[MinValueValidator(1)],
                        verbose_name="period days",
                    ),
                ),
                (
                    "notification_days",
                    models.PositiveIntegerField(
                        help_text="Number of notification lead days.",
                        validators=[MinValueValidator(1)],
                        verbose_name="notification days",
                    ),
                ),
                ("first_meeting_date", models.DateField(verbose_name="first meeting date")),
            ],
            options={
                "verbose_name": "periodicity",
                "verbose_name_plural": "periodicities",
            },
        ),
        migrations.AddConstraint(
            model_name="periodicita",
            constraint=models.CheckConstraint(condition=models.Q(("periodic_value__gt", 0)), name="periodicity_value_positive"),
        ),
        migrations.AddConstraint(
            model_name="periodicita",
            constraint=models.CheckConstraint(condition=models.Q(("period_days__gte", 1)), name="periodicity_period_days_positive"),
        ),
        migrations.AddConstraint(
            model_name="periodicita",
            constraint=models.CheckConstraint(condition=models.Q(("notification_days__gte", 1)), name="periodicity_notification_days_positive"),
        ),
    ]
