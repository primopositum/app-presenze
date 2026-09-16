"""Alert email per gli incontri periodici dei contratti commerciali."""

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

from .models import Periodicita

logger = logging.getLogger(__name__)


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
    periodicity: Periodicita
    meeting_date: date


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
        alerts.append(ContractAlert(periodicity=periodicity, meeting_date=meeting_date))
    return alerts


def _build_email(alert: ContractAlert, today: date) -> tuple[str, str]:
    periodicity = alert.periodicity
    contract = periodicity.contract
    days_left = (alert.meeting_date - today).days
    validity = f"dal {contract.start_date:%d/%m/%Y}"
    if contract.end_date:
        validity += f" al {contract.end_date:%d/%m/%Y}"

    subject = f"Promemoria incontro contratto {contract.contract_id} - {contract.client.nome}"
    body = "\n".join([
        f"Tra {days_left} giorni è previsto l'incontro periodico del contratto {contract.contract_id}.",
        "",
        f"Cliente: {contract.client.nome}",
        f"Data incontro: {alert.meeting_date:%d/%m/%Y}",
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
                    alert.periodicity.contract.contract_id,
                )
    return result
