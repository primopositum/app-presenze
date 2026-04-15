from decimal import Decimal
from datetime import date

from django.test import TestCase

from presenze.models import TimeEntry, Spesa
from presenze.serializer import TimeEntrySerializer, SpesaSerializer
from .helpers import make_utente, make_contratto, make_trasferta


# ---------------------------------------------------------------------------
# Helpers locali per il serializer
# ---------------------------------------------------------------------------

def serialize_create(utente_id, data, type, ore_tot,
                     validation_level=TimeEntry.ValidationLevel.AUTO):
    payload = {
        "utente_id": utente_id,
        "data": data,
        "type": type,
        "ore_tot": ore_tot,
        "validation_level": validation_level,
    }
    s = TimeEntrySerializer(data=payload)
    s.is_valid(raise_exception=True)
    return s.save()


def serialize_update(instance, data):
    s = TimeEntrySerializer(instance, data=data, partial=True)
    s.is_valid(raise_exception=True)
    return s.save()


# ---------------------------------------------------------------------------
# TimeEntrySerializer — create senza contratto
# ---------------------------------------------------------------------------

class TestTimeEntrySerializerCreateSenzaContratto(TestCase):
    """
    Senza contratto attivo non avviene nessuno split né sync prelievo:
    viene creata una sola TimeEntry con le ore esatte passate.
    """

    def setUp(self):
        self.utente = make_utente()
        self.lunedi = date(2025, 1, 6)

    def test_create_lavoro_ordinario_senza_contratto(self):
        te = serialize_create(self.utente.id, self.lunedi,
                              TimeEntry.EntryType.LAVORO_ORDINARIO,
                              Decimal("10.00"))
        self.assertEqual(te.ore_tot, Decimal("10.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)

    def test_create_tipo_non_lavoro_non_crea_entry_extra(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.FERIE, Decimal("8.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)


# ---------------------------------------------------------------------------
# TimeEntrySerializer — create con contratto (split ore)
# ---------------------------------------------------------------------------

class TestTimeEntrySerializerCreateSplit(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.lunedi = date(2025, 1, 6)
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])

    def test_split_crea_versamento_banca_ore(self):
        te = serialize_create(self.utente.id, self.lunedi,
                              TimeEntry.EntryType.LAVORO_ORDINARIO,
                              Decimal("10.00"))
        versamento = TimeEntry.objects.filter(
            utente=self.utente,
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
        ).first()
        self.assertIsNotNone(versamento)
        self.assertEqual(te.ore_tot, Decimal("8.00"))
        self.assertEqual(versamento.ore_tot, Decimal("2.00"))

    def test_split_totale_ore_corretto(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("10.00"))
        totale = sum(
            Decimal(str(e.ore_tot))
            for e in TimeEntry.objects.filter(utente=self.utente)
        )
        self.assertEqual(totale, Decimal("10.00"))

    def test_no_split_se_ore_uguali_contratto(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("8.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)

    def test_no_split_se_ore_inferiori_contratto(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("6.00"))
        self.assertFalse(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE).exists())

    def test_no_split_nel_weekend(self):
        sabato = date(2025, 1, 4)
        serialize_create(self.utente.id, sabato,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("10.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)

    def test_no_split_per_tipo_non_lavoro(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.FERIE, Decimal("10.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)


# ---------------------------------------------------------------------------
# TimeEntrySerializer — sync prelievo (create)
# ---------------------------------------------------------------------------

class TestTimeEntrySerializerSyncPrelievo(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.lunedi = date(2025, 1, 6)
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])

    def test_prelievo_creato_se_ore_inferiori_contratto(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("6.00"))
        prelievo = TimeEntry.objects.filter(
            utente=self.utente,
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
        ).first()
        self.assertIsNotNone(prelievo)
        self.assertEqual(prelievo.ore_tot, Decimal("2.00"))

    def test_prelievo_non_creato_se_ore_uguali_contratto(self):
        serialize_create(self.utente.id, self.lunedi,
                         TimeEntry.EntryType.LAVORO_ORDINARIO, Decimal("8.00"))
        self.assertIsNone(TimeEntry.objects.filter(
            utente=self.utente,
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
        ).first())

    def test_prelievo_aggiornato_se_gia_esistente(self):
        te = serialize_create(self.utente.id, self.lunedi,
                               TimeEntry.EntryType.LAVORO_ORDINARIO,
                               Decimal("6.00"))
        self.assertEqual(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE).count(), 1)

        serialize_update(te, {"ore_tot": Decimal("7.00")})

        prelievi = TimeEntry.objects.filter(
            utente=self.utente,
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
        )
        self.assertEqual(prelievi.count(), 1)
        self.assertEqual(prelievi.first().ore_tot, Decimal("1.00"))

    def test_prelievo_eliminato_se_ore_raggiungono_contratto(self):
        te = serialize_create(self.utente.id, self.lunedi,
                               TimeEntry.EntryType.LAVORO_ORDINARIO,
                               Decimal("6.00"))
        self.assertEqual(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE).count(), 1)

        serialize_update(te, {"ore_tot": Decimal("8.00")})

        self.assertEqual(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE).count(), 0)


# ---------------------------------------------------------------------------
# TimeEntrySerializer — update con split
# ---------------------------------------------------------------------------

class TestTimeEntrySerializerUpdate(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.lunedi = date(2025, 1, 6)
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])

    def test_update_crea_versamento_se_ore_superano_contratto(self):
        te = serialize_create(self.utente.id, self.lunedi,
                               TimeEntry.EntryType.LAVORO_ORDINARIO,
                               Decimal("8.00"))
        self.assertEqual(TimeEntry.objects.count(), 1)

        serialize_update(te, {"ore_tot": Decimal("10.00")})

        versamento = TimeEntry.objects.filter(
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE
        ).first()
        self.assertIsNotNone(versamento)
        self.assertEqual(versamento.ore_tot, Decimal("2.00"))

    def test_update_aggiorna_versamento_esistente(self):
        te = serialize_create(self.utente.id, self.lunedi,
                               TimeEntry.EntryType.LAVORO_ORDINARIO,
                               Decimal("10.00"))
        serialize_update(te, {"ore_tot": Decimal("11.00")})

        versamento = TimeEntry.objects.filter(
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE
        ).first()
        self.assertEqual(versamento.ore_tot, Decimal("3.00"))

    def test_update_elimina_versamento_se_ore_rientrano_contratto(self):
        te = serialize_create(self.utente.id, self.lunedi,
                               TimeEntry.EntryType.LAVORO_ORDINARIO,
                               Decimal("10.00"))
        self.assertTrue(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE).exists())

        serialize_update(te, {"ore_tot": Decimal("8.00")})

        self.assertFalse(TimeEntry.objects.filter(
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE).exists())


# ---------------------------------------------------------------------------
# SpesaSerializer — validazione
# ---------------------------------------------------------------------------

class TestSpesaSerializerValidazione(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.trasferta = make_trasferta(self.utente)

    def _make_payload(self, type, importo, tragitto=None):
        return {
            "trasferta": self.trasferta.id,
            "type": type,
            "importo": importo,
            "tragitto": tragitto or [],
        }

    def test_km_senza_tragitto_non_valido(self):
        payload = self._make_payload(Spesa.TrasfertaType.KM, Decimal("50.00"),
                                     tragitto=[])
        s = SpesaSerializer(data=payload)
        self.assertFalse(s.is_valid())
        self.assertIn("tragitto", s.errors)

    def test_km_con_tragitto_valido(self):
        payload = self._make_payload(Spesa.TrasfertaType.KM, Decimal("50.00"),
                                     tragitto=["Milano", "Roma"])
        s = SpesaSerializer(data=payload)
        self.assertTrue(s.is_valid(), s.errors)

    def test_km_tragitto_solo_spazi_non_valido(self):
        payload = self._make_payload(Spesa.TrasfertaType.KM, Decimal("50.00"),
                                     tragitto=["  ", ""])
        s = SpesaSerializer(data=payload)
        self.assertFalse(s.is_valid())
        self.assertIn("tragitto", s.errors)

    def test_tipo_non_km_azzera_tragitto(self):
        payload = self._make_payload(Spesa.TrasfertaType.RISTORANTI,
                                     Decimal("30.00"),
                                     tragitto=["Milano", "Roma"])
        s = SpesaSerializer(data=payload)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["tragitto"], [])

    def test_importo_negativo_non_valido(self):
        payload = self._make_payload(Spesa.TrasfertaType.RISTORANTI,
                                     Decimal("-10.00"))
        s = SpesaSerializer(data=payload)
        self.assertFalse(s.is_valid())
        self.assertIn("importo", s.errors)

    def test_importo_zero_valido(self):
        payload = self._make_payload(Spesa.TrasfertaType.PARCHEGGI,
                                     Decimal("0.00"))
        s = SpesaSerializer(data=payload)
        self.assertTrue(s.is_valid(), s.errors)
