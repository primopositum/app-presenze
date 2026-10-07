from __future__ import annotations

from datetime import date

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from presenze.contract_alerts import email_contract_alert


class Command(BaseCommand):
    help = "Invia gli alert per incontri periodici e scadenze dei contratti commerciali."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            action="append",
            metavar="EMAIL",
            help="Destinatario (ripetibile o separato da virgole). Di default CONTRACT_ALERT_RECIPIENTS.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Non invia email, stampa solo gli alert previsti.",
        )
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Esegue il controllo come se oggi fosse questa data (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))
        today: date = options.get("date") or timezone.localdate()  # rispetta TIME_ZONE (Europe/Rome)
        recipients = None
        if options.get("to"):
            recipients = [
                email.strip()
                for value in options["to"]
                for email in value.split(",")
                if email.strip()
            ]

        try:
            result = email_contract_alert(today=today, recipients=recipients, dry_run=dry_run)
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: nessuna email verrà inviata."))
        self.stdout.write(f"Data controllo: {today} | alert: {len(result.alerts)}")
        for alert in result.alerts:
            contract = alert.contract
            label = "scadenza" if alert.alert_type == "contract_expiry" else "incontro"
            self.stdout.write(f"- {contract.contract_id} ({contract.client.nome}) {label} {alert.due_date}")

        if result.failed:
            raise CommandError(f"Invio fallito per {result.failed} alert su {len(result.alerts)}.")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Email inviate: {result.sent}"))
