from decimal import Decimal
from django.test import TestCase

from presenze.models import Saldo, TimeEntry
from presenze.utils import update_saldo_for_timeentry
from .helpers import make_utente, make_saldo, make_timeentry


def latest_saldo_value(saldo):
    return Decimal(str(saldo.saldo[-1]["saldo"])) if saldo.saldo else Decimal("0.00")


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestUpdateSaldoTipoIrrilevante(TestCase):
    """
    Se il tipo della TimeEntry non è VERSAMENTO né PRELIEVO,
    la funzione deve uscire subito senza modificare il saldo.
    """

    def setUp(self):
        self.utente = make_utente()
        self.saldo = make_saldo(self.utente, validato=Decimal("10.00"),
                                saldo_progressivo=[Decimal("10.00")])

    def test_lavoro_ordinario_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.LAVORO_ORDINARIO,
                            ore_tot=8)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("10"))
        self.assertEqual(len(self.saldo.saldo), 1)

    def test_ferie_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.FERIE, ore_tot=8)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("10"))
        self.assertEqual(len(self.saldo.saldo), 1)


class TestUpdateSaldoVersamento(TestCase):
    """
    VERSAMENTO_BANCA_ORE:
      - operation='add'    → delta positivo (saldo aumenta)
      - operation='remove' → delta negativo (saldo diminuisce)
    """

    def setUp(self):
        self.utente = make_utente()
        self.saldo = make_saldo(self.utente)

    def test_versamento_add_auto_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.saldo, [])

    def test_versamento_remove_auto_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.saldo, [])

    def test_versamento_add_aumenta_saldo_validato(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("4.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("4"))

    def test_versamento_remove_diminuisce_saldo_validato(self):
        self.saldo.saldo = [{"periodo": "01-2025", "saldo": 10, "validazioni": 1}]
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("4.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("6"))


class TestUpdateSaldoPrelievo(TestCase):
    """
    PRELIEVO_BANCA_ORE:
      - operation='add'    → delta negativo (saldo diminuisce)
      - operation='remove' → delta positivo (saldo aumenta)
    """

    def setUp(self):
        self.utente = make_utente()
        self.saldo = make_saldo(self.utente)

    def test_prelievo_add_auto_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("2.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.saldo, [])

    def test_prelievo_remove_auto_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("2.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.saldo, [])

    def test_prelievo_add_diminuisce_saldo_validato(self):
        self.saldo.saldo = [{"periodo": "01-2025", "saldo": 10, "validazioni": 1}]
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("7"))

    def test_prelievo_remove_aumenta_saldo_validato(self):
        self.saldo.saldo = [{"periodo": "01-2025", "saldo": 10, "validazioni": 1}]
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(latest_saldo_value(self.saldo), Decimal("13"))


class TestUpdateSaldoSaldoMancante(TestCase):
    """
    Se il Saldo per l'utente non esiste, la funzione deve
    sollevare Saldo.DoesNotExist.
    """

    def setUp(self):
        self.utente = make_utente()

    def test_solleva_eccezione_se_saldo_mancante(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("4.00"))
        with self.assertRaises(Saldo.DoesNotExist):
            update_saldo_for_timeentry(te, operation="add")
