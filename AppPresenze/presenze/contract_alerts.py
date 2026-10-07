"""Alert e report email per le scadenze dei contratti commerciali."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Sequence

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, get_connection
from django.db.models import Q
from django.utils import timezone

from .models import ContrattoCliente, Periodicita

logger = logging.getLogger(__name__)

CONTRACT_EXPIRY_NOTIFICATION_DAYS = 30
ALERT_TYPE_MEETING = "meeting"
ALERT_TYPE_CONTRACT_EXPIRY = "contract_expiry"


def meeting_to_notify(
    first_meeting_date: date,
    period_days: int,
    notification_days: int,
    today: date,
) -> Optional[date]:
    """
    Ritorna la data dell'incontro da notificare oggi, oppure None.

    Gli incontri cadono su first_meeting_date + k * period_days (k = 0, 1, 2, ...).
    L'alert parte quando tra esattamente notification_days giorni c'è un incontro:
    così il job giornaliero invia una sola mail per incontro, compreso il primo,
    anche se il preavviso è più lungo del periodo.
    """
    meeting_date = today + timedelta(days=notification_days)
    offset = (meeting_date - first_meeting_date).days
    if offset < 0 or offset % period_days != 0:
        return None
    return meeting_date


@dataclass(frozen=True)
class ContractAlert:
    contract: ContrattoCliente
    alert_type: str
    due_date: date
    periodicity: Optional[Periodicita] = None


@dataclass
class ContractAlertResult:
    alerts: List[ContractAlert] = field(default_factory=list)
    sent: int = 0
    failed: int = 0


def find_contract_alerts(today: date) -> List[ContractAlert]:
    periodicities = (
        Periodicita.objects
        .select_related("contract", "contract__client")
        .filter(Q(contract__end_date__isnull=True) | Q(contract__end_date__gte=today))
        .order_by("first_meeting_date", "contract__contract_id")
    )

    alerts: List[ContractAlert] = []
    for periodicity in periodicities:
        meeting_date = meeting_to_notify(
            periodicity.first_meeting_date,
            periodicity.period_days,
            periodicity.notification_days,
            today,
        )
        if meeting_date is None:
            continue
        # Nessun alert per incontri che cadrebbero dopo la fine del contratto.
        end_date = periodicity.contract.end_date
        if end_date is not None and meeting_date > end_date:
            continue
        alerts.append(
            ContractAlert(
                contract=periodicity.contract,
                alert_type=ALERT_TYPE_MEETING,
                due_date=meeting_date,
                periodicity=periodicity,
            )
        )

    expiry_date = today + timedelta(days=CONTRACT_EXPIRY_NOTIFICATION_DAYS)
    expiring_contracts = (
        ContrattoCliente.objects
        .select_related("client")
        .filter(end_date=expiry_date)
        .order_by("contract_id")
    )
    for contract in expiring_contracts:
        alerts.append(
            ContractAlert(
                contract=contract,
                alert_type=ALERT_TYPE_CONTRACT_EXPIRY,
                due_date=contract.end_date,
            )
        )

    alerts.sort(key=lambda alert: (alert.due_date, alert.contract.contract_id, alert.alert_type))
    return alerts


def _build_email(alert: ContractAlert, today: date) -> tuple[str, str]:
    contract = alert.contract
    days_left = (alert.due_date - today).days

    if alert.alert_type == ALERT_TYPE_CONTRACT_EXPIRY:
        subject = f"Scadenza contratto {contract.contract_id} - {contract.client.nome}"
        body = "\n".join([
            f"Il contratto {contract.contract_id} scade tra {days_left} giorni.",
            "",
            f"Cliente: {contract.client.nome}",
            f"Data scadenza: {alert.due_date:%d/%m/%Y}",
            f"Valore contratto: € {contract.value}",
            f"Validità contratto: dal {contract.start_date:%d/%m/%Y} al {alert.due_date:%d/%m/%Y}",
        ])
        return subject, body

    periodicity = alert.periodicity
    if periodicity is None:
        raise ValueError("Un alert incontro richiede una periodicità.")

    validity = f"dal {contract.start_date:%d/%m/%Y}"
    if contract.end_date:
        validity += f" al {contract.end_date:%d/%m/%Y}"

    subject = f"Promemoria incontro contratto {contract.contract_id} - {contract.client.nome}"
    body = "\n".join([
        f"Tra {days_left} giorni è previsto l'incontro periodico del contratto {contract.contract_id}.",
        "",
        f"Cliente: {contract.client.nome}",
        f"Data incontro: {alert.due_date:%d/%m/%Y}",
        f"Periodicità: ogni {periodicity.period_days} giorni",
        f"Valore periodico: € {periodicity.periodic_value}",
        f"Primo incontro: {periodicity.first_meeting_date:%d/%m/%Y}",
        f"Validità contratto: {validity}",
    ])
    return subject, body


def email_contract_alert(
    today: Optional[date] = None,
    recipients: Optional[Sequence[str]] = None,
    dry_run: bool = False,
) -> ContractAlertResult:
    """
    Controlla le periodicità dei contratti commerciali e invia una mail di alert
    per ogni incontro che cade tra notification_days giorni.
    """
    today = today or timezone.localdate()
    recipients = list(settings.CONTRACT_ALERT_RECIPIENTS if recipients is None else recipients)
    if not dry_run and not recipients:
        raise ImproperlyConfigured("CONTRACT_ALERT_RECIPIENTS non è configurato: nessun destinatario per gli alert.")

    result = ContractAlertResult(alerts=find_contract_alerts(today))
    if dry_run or not result.alerts:
        return result

    with get_connection() as connection:
        for alert in result.alerts:
            subject, body = _build_email(alert, today)
            message = EmailMessage(subject, body, to=recipients, connection=connection)
            try:
                message.send()
                result.sent += 1
            except (smtplib.SMTPException, OSError):
                result.failed += 1
                logger.exception(
                    "Invio alert fallito per il contratto %s",
                    alert.contract.contract_id,
                )
    return result


# --- Report scadenze -------------------------------------------------------


def next_meeting(first_meeting_date: date, period_days: int, today: date) -> date:
    """Primo incontro da oggi in poi (oggi compreso): first_meeting_date + k * period_days."""
    if today <= first_meeting_date:
        return first_meeting_date
    elapsed = (today - first_meeting_date).days
    cycles = -(-elapsed // period_days)  # divisione per eccesso
    return first_meeting_date + timedelta(days=cycles * period_days)


@dataclass(frozen=True)
class ContractDeadlines:
    contract: ContrattoCliente
    periodicity: Optional[Periodicita]
    next_meeting_date: Optional[date]
    # Incontri da oggi a fine contratto, compreso il prossimo; None se il contratto non ha fine.
    remaining_meetings: Optional[int]

    def days_to(self, day: Optional[date], today: date) -> Optional[int]:
        return None if day is None else (day - today).days


@dataclass
class ContractReportResult:
    contracts: List[ContractDeadlines] = field(default_factory=list)
    recipients: List[str] = field(default_factory=list)
    subject: str = ""
    body: str = ""
    sent: bool = False


def find_contract_deadlines(today: date) -> List[ContractDeadlines]:
    """Scadenze di ogni contratto ancora valido oggi, dalla piu' vicina."""
    contracts = (
        ContrattoCliente.objects
        .select_related("client", "periodicity")
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
    )

    rows: List[ContractDeadlines] = []
    for contract in contracts:
        periodicity = getattr(contract, "periodicity", None)
        meeting = None
        remaining = None
        if periodicity is not None:
            meeting = next_meeting(periodicity.first_meeting_date, periodicity.period_days, today)
            if contract.end_date is not None:
                if meeting > contract.end_date:
                    meeting = None
                    remaining = 0
                else:
                    remaining = (contract.end_date - meeting).days // periodicity.period_days + 1
        rows.append(ContractDeadlines(contract, periodicity, meeting, remaining))

    def first_deadline(row: ContractDeadlines):
        candidates = [day for day in (row.next_meeting_date, row.contract.end_date) if day is not None]
        return (min(candidates) if candidates else date.max, row.contract.contract_id)

    return sorted(rows, key=first_deadline)


def _when(day: Optional[date], today: date) -> str:
    if day is None:
        return "-"
    days = (day - today).days
    if days == 0:
        return f"{day:%d/%m/%Y} (oggi)"
    return f"{day:%d/%m/%Y} (tra {days} {'giorno' if days == 1 else 'giorni'})"


def build_contract_report(rows: Sequence[ContractDeadlines], today: date) -> tuple[str, str]:
    subject = f"Report scadenze contratti commerciali - {today:%d/%m/%Y}"
    lines = [
        f"Scadenze dei contratti commerciali validi al {today:%d/%m/%Y}: {len(rows)} contratti.",
        "",
    ]
    if not rows:
        lines.append("Nessun contratto valido alla data del report.")

    for row in rows:
        contract = row.contract
        periodicity = row.periodicity
        lines.append(f"{contract.contract_id} - {contract.client.nome}")
        lines.append(f"  Fine contratto: {_when(contract.end_date, today) if contract.end_date else 'nessuna scadenza'}")
        if periodicity is None:
            lines.append("  Incontri periodici: nessuna periodicita' impostata")
        else:
            lines.append(
                f"  Incontri: ogni {periodicity.period_days} giorni, "
                f"€ {periodicity.periodic_value}, preavviso {periodicity.notification_days} giorni"
            )
            if row.next_meeting_date is None:
                lines.append("  Prossimo incontro: nessuno prima della fine del contratto")
            else:
                lines.append(f"  Prossimo incontro: {_when(row.next_meeting_date, today)}")
                alert_day = row.next_meeting_date - timedelta(days=periodicity.notification_days)
                lines.append(f"  Alert previsto: {_when(alert_day, today) if alert_day >= today else 'gia scattato'}")
            if row.remaining_meetings is not None:
                lines.append(f"  Incontri mancanti a fine contratto: {row.remaining_meetings}")
        lines.append("")

    return subject, "\n".join(lines).rstrip() + "\n"


def email_contract_report(
    today: Optional[date] = None,
    recipients: Optional[Sequence[str]] = None,
    dry_run: bool = False,
) -> ContractReportResult:
    """
    Una sola mail con le scadenze mancanti di ogni contratto valido.

    Pensata per provare il servizio email: a differenza degli alert, gli errori
    SMTP non vengono assorbiti ma risalgono a chi chiama.
    """
    today = today or timezone.localdate()
    recipients = list(settings.CONTRACT_ALERT_RECIPIENTS if recipients is None else recipients)
    if not dry_run and not recipients:
        raise ImproperlyConfigured(
            "Nessun destinatario: imposta CONTRACT_ALERT_RECIPIENTS o passa i destinatari esplicitamente."
        )

    rows = find_contract_deadlines(today)
    subject, body = build_contract_report(rows, today)
    result = ContractReportResult(contracts=rows, recipients=recipients, subject=subject, body=body)
    if dry_run:
        return result

    EmailMessage(subject, body, to=recipients).send(fail_silently=False)
    result.sent = True
    return result
