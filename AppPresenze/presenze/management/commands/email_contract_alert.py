from __future__ import annotations

from datetime import date

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from presenze.contract_alerts import email_contract_alert


class Command(BaseCommand):
    help = "Invia le email di alert per gli incontri periodici dei contratti commerciali."

    def add_arguments(self, parser):
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

        try:
            result = email_contract_alert(today=today, dry_run=dry_run)
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: nessuna email verrà inviata."))
        self.stdout.write(f"Data controllo: {today} | alert: {len(result.alerts)}")
        for alert in result.alerts:
            contract = alert.periodicity.contract
            self.stdout.write(f"- {contract.contract_id} ({contract.client.nome}) incontro {alert.meeting_date}")

        if result.failed:
            raise CommandError(f"Invio fallito per {result.failed} alert su {len(result.alerts)}.")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Email inviate: {result.sent}"))
