from decimal import Decimal
from django.test import TestCase

from presenze.models import Saldo, TimeEntry
from presenze.utils import update_saldo_for_timeentry
from .helpers import make_utente, make_saldo, make_timeentry


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
                                sospeso=Decimal("5.00"))

    def test_lavoro_ordinario_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.LAVORO_ORDINARIO,
                            ore_tot=8)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("10.00"))
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("5.00"))

    def test_ferie_non_modifica_saldo(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.FERIE, ore_tot=8)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("10.00"))
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("5.00"))


class TestUpdateSaldoVersamento(TestCase):
    """
    VERSAMENTO_BANCA_ORE:
      - operation='add'    → delta positivo (saldo aumenta)
      - operation='remove' → delta negativo (saldo diminuisce)
    """

    def setUp(self):
        self.utente = make_utente()
        self.saldo = make_saldo(self.utente, sospeso=Decimal("10.00"))

    def test_versamento_add_aumenta_saldo_sospeso(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("13.00"))

    def test_versamento_remove_diminuisce_saldo_sospeso(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("7.00"))

    def test_versamento_add_aumenta_saldo_validato(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("4.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("4.00"))
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("10.00"))

    def test_versamento_remove_diminuisce_saldo_validato(self):
        self.saldo.valore_saldo_validato = Decimal("10.00")
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
                            ore_tot=Decimal("4.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("6.00"))


class TestUpdateSaldoPrelievo(TestCase):
    """
    PRELIEVO_BANCA_ORE:
      - operation='add'    → delta negativo (saldo diminuisce)
      - operation='remove' → delta positivo (saldo aumenta)
    """

    def setUp(self):
        self.utente = make_utente()
        self.saldo = make_saldo(self.utente, sospeso=Decimal("10.00"))

    def test_prelievo_add_diminuisce_saldo_sospeso(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("2.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("8.00"))

    def test_prelievo_remove_aumenta_saldo_sospeso(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("2.00"),
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("12.00"))

    def test_prelievo_add_diminuisce_saldo_validato(self):
        self.saldo.valore_saldo_validato = Decimal("10.00")
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="add")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("7.00"))
        self.assertEqual(self.saldo.valore_saldo_sospeso, Decimal("10.00"))

    def test_prelievo_remove_aumenta_saldo_validato(self):
        self.saldo.valore_saldo_validato = Decimal("10.00")
        self.saldo.save()

        te = make_timeentry(self.utente, type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
                            ore_tot=Decimal("3.00"),
                            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        update_saldo_for_timeentry(te, operation="remove")

        self.saldo.refresh_from_db()
        self.assertEqual(self.saldo.valore_saldo_validato, Decimal("13.00"))


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
