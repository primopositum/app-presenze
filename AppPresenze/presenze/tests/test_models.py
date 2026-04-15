from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from presenze.models import (
    Utente, TimeEntry, Saldo, Contratto,
    Automobile, Trasferta, Spesa,
)
from .helpers import (
    make_utente, make_saldo, make_contratto, make_timeentry,
    make_automobile, make_trasferta, make_spesa,
)


# ---------------------------------------------------------------------------
# Utente
# ---------------------------------------------------------------------------

class TestUtenteModel(TestCase):

    def test_creazione_utente_base(self):
        utente = make_utente()
        self.assertEqual(utente.email, "test@test.com")
        self.assertEqual(utente.nome, "Mario")
        self.assertEqual(utente.cognome, "Rossi")
        self.assertTrue(utente.is_active)
        self.assertFalse(utente.is_superuser)

    def test_str_restituisce_email(self):
        utente = make_utente()
        self.assertEqual(str(utente), "test@test.com")

    def test_email_unica(self):
        make_utente(email="unico@test.com")
        with self.assertRaises(IntegrityError):
            make_utente(email="unico@test.com")

    def test_password_viene_hashata(self):
        utente = make_utente(password="testpass123")
        self.assertNotEqual(utente.password, "testpass123")
        self.assertTrue(utente.check_password("testpass123"))

    def test_create_user_senza_password_imposta_password_inutilizzabile(self):
        utente = Utente.objects.create_user(email="nopwd@test.com")
        self.assertFalse(utente.has_usable_password())

    def test_create_user_senza_email_solleva_errore(self):
        with self.assertRaises(ValueError):
            Utente.objects.create_user(email="")

    def test_create_superuser(self):
        superuser = Utente.objects.create_superuser(
            email="admin@test.com", password="adminpass"
        )
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_active)

    def test_cancellazione_utente_a_cascata(self):
        utente = make_utente()
        make_timeentry(utente)
        self.assertEqual(TimeEntry.objects.filter(utente=utente).count(), 1)
        utente.delete()
        self.assertEqual(TimeEntry.objects.count(), 0)


# ---------------------------------------------------------------------------
# Contratto
# ---------------------------------------------------------------------------

class TestContrattoModel(TestCase):

    def setUp(self):
        self.utente = make_utente()

    def test_ore_lun_ven_restituisce_dict_corretto(self):
        contratto = make_contratto(self.utente, ore_sett=[8, 8, 6, 8, 4])
        ore = contratto.ore_lun_ven
        self.assertEqual(ore["lun"], 8)
        self.assertEqual(ore["mar"], 8)
        self.assertEqual(ore["mer"], 6)
        self.assertEqual(ore["gio"], 8)
        self.assertEqual(ore["ven"], 4)

    def test_ore_lun_ven_con_ore_sett_vuoto(self):
        contratto = make_contratto(self.utente)
        contratto.ore_sett = []
        ore = contratto.ore_lun_ven
        self.assertIsNone(ore["lun"])
        self.assertIsNone(ore["ven"])

    def test_validatore_ore_sett_meno_di_5_elementi(self):
        contratto = make_contratto(self.utente, ore_sett=[8, 8, 8])
        with self.assertRaises(ValidationError):
            contratto.full_clean()

    def test_validatore_ore_sett_piu_di_5_elementi(self):
        contratto = make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8, 8])
        with self.assertRaises(ValidationError):
            contratto.full_clean()

    def test_validatore_ore_sett_esattamente_5_elementi_non_solleva(self):
        contratto = make_contratto(
            self.utente,
            ore_sett=[Decimal("8"), Decimal("8"), Decimal("8"),
                      Decimal("8"), Decimal("8")]
        )
        contratto.full_clean()

    def test_str_contratto(self):
        contratto = make_contratto(self.utente, tipologia="Part-time")
        self.assertIn("Part-time", str(contratto))
        self.assertIn(self.utente.email, str(contratto))


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------

class TestTimeEntryModel(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.oggi = timezone.localdate()

    def test_creazione_timeentry(self):
        te = make_timeentry(self.utente, ore_tot=8)
        self.assertEqual(te.utente, self.utente)
        self.assertEqual(te.ore_tot, 8)
        self.assertEqual(te.validation_level, TimeEntry.ValidationLevel.AUTO)

    def test_str_timeentry(self):
        te = make_timeentry(self.utente, type=TimeEntry.EntryType.FERIE, ore_tot=8)
        self.assertIn(self.utente.email, str(te))
        self.assertIn("Ferie", str(te))

    def test_unicita_utente_data_type(self):
        make_timeentry(self.utente, data=self.oggi,
                       type=TimeEntry.EntryType.LAVORO_ORDINARIO)
        with self.assertRaises(IntegrityError):
            make_timeentry(self.utente, data=self.oggi,
                           type=TimeEntry.EntryType.LAVORO_ORDINARIO)

    def test_stesso_utente_stessa_data_tipo_diverso_e_consentito(self):
        make_timeentry(self.utente, data=self.oggi,
                       type=TimeEntry.EntryType.LAVORO_ORDINARIO)
        make_timeentry(self.utente, data=self.oggi,
                       type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE)

    def test_utenti_diversi_stessa_data_stesso_tipo_consentito(self):
        altro_utente = make_utente(email="altro@test.com")
        make_timeentry(self.utente, data=self.oggi,
                       type=TimeEntry.EntryType.LAVORO_ORDINARIO)
        make_timeentry(altro_utente, data=self.oggi,
                       type=TimeEntry.EntryType.LAVORO_ORDINARIO)

    def test_validation_level_default_e_auto(self):
        te = make_timeentry(self.utente)
        self.assertEqual(te.validation_level, TimeEntry.ValidationLevel.AUTO)


# ---------------------------------------------------------------------------
# Saldo
# ---------------------------------------------------------------------------

class TestSaldoModel(TestCase):

    def setUp(self):
        self.utente = make_utente()

    def test_creazione_saldo(self):
        saldo = Saldo.objects.create(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, 0)
        self.assertEqual(saldo.valore_saldo_sospeso, 0)

    def test_saldo_one_to_one_non_permette_duplicati(self):
        Saldo.objects.create(utente=self.utente)
        with self.assertRaises(IntegrityError):
            Saldo.objects.create(utente=self.utente)

    def test_cancellazione_utente_elimina_saldo(self):
        Saldo.objects.create(utente=self.utente)
        self.assertEqual(Saldo.objects.count(), 1)
        self.utente.delete()
        self.assertEqual(Saldo.objects.count(), 0)


# ---------------------------------------------------------------------------
# Trasferta
# ---------------------------------------------------------------------------

class TestTrasfertaModel(TestCase):

    def setUp(self):
        self.utente = make_utente()

    def test_totale_spese_senza_spese(self):
        trasferta = make_trasferta(self.utente)
        self.assertEqual(trasferta.totale_spese, 0)

    def test_totale_spese_con_piu_spese(self):
        trasferta = make_trasferta(self.utente)
        make_spesa(trasferta, importo=Decimal("25.00"))
        make_spesa(trasferta, type=Spesa.TrasfertaType.PEDAGGI,
                   importo=Decimal("10.50"))
        self.assertEqual(trasferta.totale_spese, Decimal("35.50"))

    def test_totale_spese_trasferta_non_salvata(self):
        trasferta = Trasferta(utente=self.utente, data=timezone.localdate(),
                              azienda="Test")
        self.assertEqual(trasferta.totale_spese, 0)

    def test_str_trasferta(self):
        trasferta = make_trasferta(self.utente, azienda="Acme")
        self.assertIn(self.utente.email, str(trasferta))
        self.assertIn("Acme", str(trasferta))

    def test_automobile_set_null_alla_cancellazione(self):
        auto = make_automobile()
        trasferta = make_trasferta(self.utente, automobile=auto)
        self.assertIsNotNone(trasferta.automobile)
        auto.delete()
        trasferta.refresh_from_db()
        self.assertIsNone(trasferta.automobile)

    def test_cancellazione_utente_elimina_trasferta(self):
        make_trasferta(self.utente)
        self.assertEqual(Trasferta.objects.count(), 1)
        self.utente.delete()
        self.assertEqual(Trasferta.objects.count(), 0)


# ---------------------------------------------------------------------------
# Spesa
# ---------------------------------------------------------------------------

class TestSpesaModel(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.trasferta = make_trasferta(self.utente)

    def test_creazione_spesa(self):
        spesa = make_spesa(self.trasferta, importo=Decimal("50.00"))
        self.assertEqual(spesa.trasferta, self.trasferta)
        self.assertEqual(spesa.importo, Decimal("50.00"))

    def test_str_spesa(self):
        spesa = make_spesa(self.trasferta, type=Spesa.TrasfertaType.HOTEL,
                           importo=Decimal("100.00"))
        self.assertIn("100.00", str(spesa))

    def test_cancellazione_trasferta_elimina_spese(self):
        make_spesa(self.trasferta)
        make_spesa(self.trasferta, type=Spesa.TrasfertaType.PEDAGGI,
                   importo=Decimal("5.00"))
        self.assertEqual(Spesa.objects.count(), 2)
        self.trasferta.delete()
        self.assertEqual(Spesa.objects.count(), 0)
