from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from presenze.models import Contratto, TimeEntry, Utente


# ---- Festività ITA ----
try:
    import holidays
except Exception:
    holidays = None


def _italy_holidays(year: int):
    """
    Ritorna un set/dict di festività italiane per l'anno dato.
    Se la lib 'holidays' non è installata, ritorna vuoto (quindi niente ferie automatiche).
    """
    if holidays is None:
        return set()
    return holidays.country_holidays("IT", years=[year])


def _next_monday(d: date) -> date:
    # weekday: lun=0 ... dom=6
    days_ahead = (7 - d.weekday()) % 7
    return d if days_ahead == 0 else d + timedelta(days=days_ahead)


def _first_friday_on_or_after(d: date) -> date:
    # ven = 4
    delta = (4 - d.weekday()) % 7
    return d + timedelta(days=delta)


def _business_days_inclusive(start: date, end: date) -> List[date]:
    out: List[date] = []
    cur = start
    while cur <= end:
        if cur.weekday() <= 4:  # lun-ven
            out.append(cur)
        cur += timedelta(days=1)
    return out


@dataclass(frozen=True)
class PlanWindow:
    start: date
    end: date


def _compute_window(today: date) -> PlanWindow:
    """
    Regole richieste:
    - Se oggi è lunedì: compila la settimana entrante (lun-ven della settimana corrente)
      (dato che la routine gira alle 00:00 del lunedì, "settimana entrante" = questa settimana lun-ven)
    - Se oggi non è lunedì:
        - se è mar/mer/gio/ven: compila oggi..venerdì
        - se è sab/dom: compila dal prossimo lunedì..venerdì
    """
    if today.weekday() == 0:  # lunedì
        start = today
        end = today + timedelta(days=4)
        return PlanWindow(start=start, end=end)

    if today.weekday() <= 4:  # mar-ven
        start = today
        end = _first_friday_on_or_after(today)
        return PlanWindow(start=start, end=end)

    # sab/dom -> da prossimo lunedì al venerdì
    start = _next_monday(today)
    end = start + timedelta(days=4)
    return PlanWindow(start=start, end=end)


def _pick_active_contract(user: Utente) -> Optional[Contratto]:
    return (
        Contratto.objects
        .filter(utente=user, is_active=True)
        .order_by("-data_ass", "-id")
        .first()
    )


class Command(BaseCommand):
    help = "Crea automaticamente TimeEntry (AUTO) per la settimana entrante / fino a venerdì."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Non scrive su DB, stampa solo cosa farebbe.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))

        today = timezone.localdate()  # rispetta TIME_ZONE (Europe/Rome)
        window = _compute_window(today)
        days = _business_days_inclusive(window.start, window.end)

        if not days:
            self.stdout.write(self.style.WARNING("Nessun giorno lavorativo da compilare."))
            return

        # Festività (attenzione: possono attraversare due anni)
        years = sorted({d.year for d in days})
        holiday_sets = {y: _italy_holidays(y) for y in years}

        active_users = Utente.objects.filter(is_active=True).only("id", "email")

        # Pre-carico (utente_id, data) già presenti per non duplicare
        existing_pairs = set(
            TimeEntry.objects
            .filter(utente__in=active_users, data__in=days)
            .values_list("utente_id", "data")
        )

        to_create: List[TimeEntry] = []
        skipped_no_contract = 0
        skipped_existing = 0

        for user in active_users:
            contract = _pick_active_contract(user)
            if not contract or not contract.ore_sett or len(contract.ore_sett) != 5:
                skipped_no_contract += 1
                continue

            for d in days:
                key = (user.id, d)
                if key in existing_pairs:
                    skipped_existing += 1
                    continue

                # ore_sett: [lun, mar, mer, gio, ven]
                ore = contract.ore_sett[d.weekday()]
                ore_dec = Decimal(str(ore))
                # Tipo: festivita se giorno festivo, altrimenti lavoro ordinario
                is_holiday = d in holiday_sets[d.year]
                entry_type = (
                    TimeEntry.EntryType.FESTIVITA
                    if is_holiday
                    else TimeEntry.EntryType.LAVORO_ORDINARIO
                )
                validation_level = (
                    TimeEntry.ValidationLevel.VALIDATO_ADMIN
                    if is_holiday
                    else TimeEntry.ValidationLevel.AUTO
                )

                to_create.append(
                    TimeEntry(
                        utente=user,
                        data=d,
                        ore_tot=ore_dec,
                        type=entry_type,
                        validation_level=validation_level,
                    )
                )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: niente verrà scritto su DB."))
            self.stdout.write(f"Finestra: {window.start} -> {window.end} (giorni: {len(days)})")
            self.stdout.write(f"Da creare: {len(to_create)} | skip no contract: {skipped_no_contract} | skip existing: {skipped_existing}")
            for te in to_create[:20]:
                self.stdout.write(f"- {te.utente.email} {te.data} type={te.type} ore={te.ore_tot} vl={te.validation_level}")
            if len(to_create) > 20:
                self.stdout.write("... (tagliato)")
            return

        created = 0
        if to_create:
            TimeEntry.objects.bulk_create(to_create, batch_size=1000)
            created = len(to_create)

        self.stdout.write(self.style.SUCCESS("Operazione completata."))
        self.stdout.write(f"Finestra: {window.start} -> {window.end} (giorni: {len(days)})")
        self.stdout.write(f"Creati: {created} | skip no contract: {skipped_no_contract} | skip existing: {skipped_existing}")

