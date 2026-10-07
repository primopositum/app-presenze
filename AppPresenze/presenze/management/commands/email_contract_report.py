from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from presenze.contract_alerts import email_contract_report


class Command(BaseCommand):
    help = (
        "Invia una mail di report con le scadenze mancanti di ogni contratto commerciale. "
        "Solo da CLI: serve a provare il servizio email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            action="append",
            metavar="EMAIL",
            help=(
                "Destinatario (ripetibile, o separati da virgola). "
                "Di default CONTRACT_ALERT_RECIPIENTS."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Non invia nulla: stampa la mail che verrebbe inviata.",
        )
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            help="Calcola le scadenze come se oggi fosse questa data (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--smtp-test",
            action="store_true",
            help=(
                "Invia solo una mail di prova, senza leggere i contratti: "
                "non serve il database, solo la configurazione SMTP."
            ),
        )

    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))
        today: date = options.get("date") or timezone.localdate()  # rispetta TIME_ZONE (Europe/Rome)
        recipients = None
        if options.get("to"):
            recipients = [email.strip() for value in options["to"] for email in value.split(",") if email.strip()]

        self._print_config()

        if options.get("smtp_test"):
            self._send_smtp_test(recipients)
            return

        try:
            result = email_contract_report(today=today, recipients=recipients, dry_run=dry_run)
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - qui l'errore SMTP va mostrato per intero
            raise CommandError(f"Invio fallito: {type(exc).__name__}: {exc}") from exc

        self.stdout.write(f"Data report: {today} | contratti: {len(result.contracts)}")
        self.stdout.write(f"Destinatari: {', '.join(result.recipients) or '-'}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: nessuna email inviata. Contenuto:"))
            self.stdout.write(f"Oggetto: {result.subject}\n")
            self.stdout.write(result.body)
            return
        self.stdout.write(self.style.SUCCESS(f"Email inviata: {result.subject}"))

    def _send_smtp_test(self, recipients: list[str] | None):
        """Una mail minima ai destinatari del report: prova il solo invio."""
        recipients = list(settings.CONTRACT_ALERT_RECIPIENTS if recipients is None else recipients)
        if not recipients:
            raise CommandError(
                "Nessun destinatario: imposta CONTRACT_ALERT_RECIPIENTS nel .env o passa --to."
            )
        self.stdout.write(f"Destinatari: {', '.join(recipients)}")

        subject = "Prova servizio email - AppPresenze"
        body = (
            f"Mail di prova inviata il {timezone.localtime():%d/%m/%Y alle %H:%M}.\n"
            "Se la ricevi, la configurazione SMTP usata per gli alert dei contratti funziona.\n"
        )
        try:
            EmailMessage(subject, body, to=recipients).send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001 - qui l'errore SMTP va mostrato per intero
            raise CommandError(f"Invio fallito: {type(exc).__name__}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Email di prova inviata: {subject}"))

    def _print_config(self):
        """Configurazione SMTP in uso, senza la password: e' la prima cosa da controllare."""
        security = "SSL" if settings.EMAIL_USE_SSL else "STARTTLS" if settings.EMAIL_USE_TLS else "nessuna"
        self.stdout.write(
            f"SMTP: {settings.EMAIL_BACKEND} | {settings.EMAIL_HOST}:{settings.EMAIL_PORT} | "
            f"sicurezza {security} | utente {settings.EMAIL_HOST_USER or '-'} | "
            f"password {'impostata' if settings.EMAIL_HOST_PASSWORD else 'assente'} | "
            f"mittente {settings.DEFAULT_FROM_EMAIL}"
        )
