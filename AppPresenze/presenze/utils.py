from .models import  TimeEntry, Saldo
from decimal import Decimal
from django.db import transaction

@transaction.atomic
def update_saldo_for_timeentry(timeentry, operation="add"):
    if timeentry.type not in [
        TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
        TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
    ]:
        return

    # SOLO GET: se non esiste, è un errore di setup
    saldo = Saldo.objects.select_for_update().get(utente=timeentry.utente)

    ore = Decimal(str(timeentry.ore_tot))

    if timeentry.type == TimeEntry.EntryType.VERSAMENTO_BANCA_ORE:
        delta = ore if operation == "add" else -ore
    else:  # PRELIEVO
        delta = -ore if operation == "add" else ore

    if timeentry.validation_level == TimeEntry.ValidationLevel.VALIDATO_ADMIN:
        saldo.valore_saldo_validato += delta
    else:
        saldo.valore_saldo_sospeso += delta

    saldo.save(update_fields=["valore_saldo_validato", "valore_saldo_sospeso", "data_upd"])
