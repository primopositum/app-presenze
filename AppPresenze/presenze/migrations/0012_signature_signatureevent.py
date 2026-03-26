from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("presenze", "0011_sync_automobile_is_active_and_coefficiente"),
    ]

    operations = [
        migrations.CreateModel(
            name="Signature",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("svg", models.TextField()),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_column="U_ID",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signatures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "Signature",
            },
        ),
        migrations.CreateModel(
            name="SignatureEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "event_type",
                    models.CharField(
                        choices=[("created", "Created"), ("used", "Used"), ("deleted", "Deleted")],
                        max_length=20,
                    ),
                ),
                ("document_id", models.UUIDField(blank=True, null=True)),
                ("document_sha256", models.CharField(blank=True, max_length=64, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "signature",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="presenze.signature",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_column="U_ID",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signature_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "SignatureEvent",
            },
        ),
        migrations.AddIndex(
            model_name="signature",
            index=models.Index(fields=["user", "-created_at"], name="Signature_user_cr_70b9f5_idx"),
        ),
        migrations.AddIndex(
            model_name="signature",
            index=models.Index(fields=["sha256"], name="Signature_sha256_5cb32b_idx"),
        ),
        migrations.AddIndex(
            model_name="signatureevent",
            index=models.Index(fields=["signature", "-created_at"], name="SignatureEv_signat_8f2f97_idx"),
        ),
        migrations.AddIndex(
            model_name="signatureevent",
            index=models.Index(fields=["user", "-created_at"], name="SignatureEv_user_id_4c4f1c_idx"),
        ),
        migrations.AddIndex(
            model_name="signatureevent",
            index=models.Index(fields=["event_type", "-created_at"], name="SignatureEv_event_t_c75314_idx"),
        ),
    ]
