from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from presenze.models import (
    Utente, TimeEntry, Saldo, Trasferta, Spesa,
)
from .helpers import (
    make_utente, make_saldo, make_contratto, make_timeentry,
    make_trasferta, make_spesa, auth_client,
)

# ---------------------------------------------------------------------------
# URL constants  (prefisso: /presenze/api/)
# ---------------------------------------------------------------------------
BASE = "/presenze/api"

URL_LOGIN            = f"{BASE}/login/"
URL_LOGOUT           = f"{BASE}/logout/"
URL_PROFILE          = f"{BASE}/profile/"
URL_CHANGE_PASSWORD  = f"{BASE}/change-password/"
URL_CREATE_ACCOUNT   = f"{BASE}/create-account/"
URL_DELETE_ACCOUNT   = f"{BASE}/delete-account/"

URL_TE_CREATE        = f"{BASE}/time-entries/"
URL_TE_DETAIL        = lambda te_id: f"{BASE}/time-entries/{te_id}/"
URL_TE_VALIDATION    = lambda te_id: f"{BASE}/time-entries/{te_id}/validation/"

URL_TRASFERTA_CREATE = f"{BASE}/trasferte/create/"
URL_TRASFERTA_UPDATE = lambda t_id: f"{BASE}/trasferte/{t_id}/"
URL_TRASFERTA_VALID  = lambda tr_id: f"{BASE}/trasferte/{tr_id}/validation/"
URL_TRASFERTA_DELETE = lambda t_id: f"{BASE}/trasferte/{t_id}/delete/"

URL_SPESA_CREATE     = lambda t_id: f"{BASE}/trasferte/{t_id}/spese/create/"
URL_SPESA_MANAGE     = lambda s_id: f"{BASE}/spese/{s_id}/"


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

class TestApiLogin(TestCase):

    def setUp(self):
        self.utente = make_utente(password="pass123")
        self.client = APIClient()

    def test_login_credenziali_corrette(self):
        res = self.client.post(URL_LOGIN, {
            "email": "test@test.com", "password": "pass123"
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("token_type", res.data)
        self.assertIn("user", res.data)

    def test_login_password_errata(self):
        res = self.client.post(URL_LOGIN, {
            "email": "test@test.com", "password": "sbagliata"
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_login_senza_credenziali(self):
        res = self.client.post(URL_LOGIN, {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_login_utente_inattivo(self):
        self.utente.is_active = False
        self.utente.save()
        res = self.client.post(URL_LOGIN, {
            "email": "test@test.com", "password": "pass123"
        }, format="json")
        self.assertEqual(res.status_code, 400)


class TestApiLogout(TestCase):

    def setUp(self):
        self.utente = make_utente()

    def test_logout_autenticato(self):
        res = auth_client(self.utente).post(URL_LOGOUT)
        self.assertEqual(res.status_code, 200)

    def test_logout_non_autenticato(self):
        res = APIClient().post(URL_LOGOUT)
        self.assertEqual(res.status_code, 401)


# ---------------------------------------------------------------------------
# Account views
# ---------------------------------------------------------------------------

class TestCreateAccount(TestCase):

    def setUp(self):
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.admin_client = auth_client(self.admin)

    def test_superuser_crea_account(self):
        res = self.admin_client.post(URL_CREATE_ACCOUNT, {
            "email": "nuovo@test.com",
            "password": "pass123",
            "nome": "Luca",
            "cognome": "Verdi",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Utente.objects.filter(email="nuovo@test.com").exists())

    def test_crea_account_crea_anche_saldo(self):
        self.admin_client.post(URL_CREATE_ACCOUNT, {
            "email": "nuovo@test.com",
            "password": "pass123",
        }, format="json")
        utente = Utente.objects.get(email="nuovo@test.com")
        self.assertTrue(Saldo.objects.filter(utente=utente).exists())

    def test_utente_normale_non_puo_creare_account(self):
        user = make_utente(email="normal@test.com")
        res = auth_client(user).post(URL_CREATE_ACCOUNT, {
            "email": "altro@test.com", "password": "pass123",
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_email_mancante_restituisce_400(self):
        res = self.admin_client.post(URL_CREATE_ACCOUNT, {
            "password": "pass123",
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_password_mancante_restituisce_400(self):
        res = self.admin_client.post(URL_CREATE_ACCOUNT, {
            "email": "nuovo@test.com",
        }, format="json")
        self.assertEqual(res.status_code, 400)


class TestDeleteAccount(TestCase):

    def setUp(self):
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.utente = make_utente(email="target@test.com")

    def test_superuser_elimina_account(self):
        res = auth_client(self.admin).delete(URL_DELETE_ACCOUNT, {
            "user_id": self.utente.id
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Utente.objects.filter(id=self.utente.id).exists())

    def test_utente_normale_non_puo_eliminare(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).delete(URL_DELETE_ACCOUNT, {
            "user_id": self.utente.id
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_superuser_non_elimina_altro_superuser(self):
        altro_admin = make_utente(email="admin2@test.com", is_superuser=True)
        res = auth_client(self.admin).delete(URL_DELETE_ACCOUNT, {
            "user_id": altro_admin.id
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_utente_non_trovato_restituisce_404(self):
        res = auth_client(self.admin).delete(URL_DELETE_ACCOUNT, {
            "user_id": 99999
        }, format="json")
        self.assertEqual(res.status_code, 404)


class TestUserProfile(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)

    def test_get_profilo_proprio(self):
        res = auth_client(self.utente).get(URL_PROFILE)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["email"], self.utente.email)

    def test_get_profilo_altrui_come_admin(self):
        res = auth_client(self.admin).get(
            URL_PROFILE, {"user_id": self.utente.id}
        )
        self.assertEqual(res.status_code, 200)

    def test_get_profilo_altrui_come_utente_normale(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).get(
            URL_PROFILE, {"user_id": self.utente.id}
        )
        self.assertEqual(res.status_code, 403)

    def test_put_aggiorna_nome(self):
        res = auth_client(self.utente).put(
            URL_PROFILE, {"nome": "Giuseppe"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.utente.refresh_from_db()
        self.assertEqual(self.utente.nome, "Giuseppe")

    def test_utente_normale_non_modifica_is_active(self):
        res = auth_client(self.utente).put(
            URL_PROFILE, {"is_active": False}, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_modifica_is_active(self):
        res = auth_client(self.admin).put(
            URL_PROFILE,
            {"user_id": self.utente.id, "is_active": False},
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.utente.refresh_from_db()
        self.assertFalse(self.utente.is_active)


class TestChangePassword(TestCase):

    def setUp(self):
        self.utente = make_utente(password="vecchia123")

    def test_cambio_password_corretto(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "vecchia123",
            "new_password": "nuova456",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.utente.refresh_from_db()
        self.assertTrue(self.utente.check_password("nuova456"))

    def test_vecchia_password_errata(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "sbagliata",
            "new_password": "nuova456",
        }, format="json")
        self.assertEqual(res.status_code, 400)


# ---------------------------------------------------------------------------
# TimeEntry views
# ---------------------------------------------------------------------------

class TestTimeEntryCreate(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True,
                                 is_staff=True)
        self.lunedi = "2025-01-06"

    def test_crea_timeentry_per_se_stesso(self):
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_utente_normale_non_crea_per_altri(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_admin_crea_per_altri(self):
        res = auth_client(self.admin).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_utente_normale_non_imposta_validato_admin(self):
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
            "validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_non_autenticato_restituisce_401(self):
        res = APIClient().post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 401)


class TestTimeEntryDetail(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.te = make_timeentry(self.utente)

    def test_get_timeentry(self):
        res = auth_client(self.utente).get(URL_TE_DETAIL(self.te.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], self.te.id)

    def test_utente_non_vede_timeentry_altrui(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).get(URL_TE_DETAIL(self.te.id))
        self.assertEqual(res.status_code, 403)

    def test_admin_vede_timeentry_altrui(self):
        res = auth_client(self.admin).get(URL_TE_DETAIL(self.te.id))
        self.assertEqual(res.status_code, 200)

    def test_timeentry_inesistente_restituisce_404(self):
        res = auth_client(self.utente).get(URL_TE_DETAIL(99999))
        self.assertEqual(res.status_code, 404)

    def test_delete_timeentry_propria(self):
        res = auth_client(self.utente).delete(URL_TE_DETAIL(self.te.id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(TimeEntry.objects.filter(id=self.te.id).exists())

    def test_utente_non_elimina_timeentry_altrui(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).delete(URL_TE_DETAIL(self.te.id))
        self.assertEqual(res.status_code, 403)


class TestTimeEntryValidation(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        make_saldo(self.utente)

    def test_utente_valida_propria_entry_da_0_a_1(self):
        te = make_timeentry(self.utente,
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        res = auth_client(self.utente).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_UTENTE},
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        te.refresh_from_db()
        self.assertEqual(te.validation_level,
                         TimeEntry.ValidationLevel.VALIDATO_UTENTE)

    def test_utente_non_valida_da_0_a_2(self):
        te = make_timeentry(self.utente,
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        res = auth_client(self.utente).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_valida_da_1_a_2(self):
        te = make_timeentry(
            self.utente,
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE
        )
        res = auth_client(self.admin).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN},
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        te.refresh_from_db()
        self.assertEqual(te.validation_level,
                         TimeEntry.ValidationLevel.VALIDATO_ADMIN)

    def test_admin_non_valida_da_0_a_2(self):
        te = make_timeentry(self.utente,
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        res = auth_client(self.admin).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_entry_gia_validata_admin_non_modificabile(self):
        te = make_timeentry(
            self.utente,
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN
        )
        res = auth_client(self.admin).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_UTENTE},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_utente_non_valida_entry_altrui(self):
        altro = make_utente(email="altro@test.com")
        te = make_timeentry(self.utente,
                            validation_level=TimeEntry.ValidationLevel.AUTO)
        res = auth_client(altro).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_UTENTE},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_validazione_admin_versamento_aggiorna_saldo_validato(self):
        """Quando una VERSAMENTO viene portata a VALIDATO_ADMIN il saldo validato aumenta."""
        te = make_timeentry(
            self.utente,
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            ore_tot=Decimal("4.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        auth_client(self.admin).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN},
            format="json"
        )
        saldo = Saldo.objects.get(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, Decimal("4.00"))


# ---------------------------------------------------------------------------
# Trasferta views
# ---------------------------------------------------------------------------

class TestTrasfertaCreate(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)

    def test_utente_crea_trasferta_propria(self):
        res = auth_client(self.utente).post(URL_TRASFERTA_CREATE, {
            "data": "2025-01-06",
            "azienda": "Acme",
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_dati_mancanti_restituiscono_400(self):
        res = auth_client(self.utente).post(URL_TRASFERTA_CREATE, {
            "azienda": "Acme",
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_non_autenticato_restituisce_401(self):
        res = APIClient().post(URL_TRASFERTA_CREATE, {
            "data": "2025-01-06", "azienda": "Acme",
        }, format="json")
        self.assertEqual(res.status_code, 401)

    def test_superuser_crea_trasferta_per_utente(self):
        res = auth_client(self.admin).post(URL_TRASFERTA_CREATE, {
            "data": "2025-01-06",
            "azienda": "Acme",
            "utente_email": self.utente.email,
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(
            Trasferta.objects.filter(utente=self.utente).count(), 1
        )

    def test_superuser_senza_utente_email_restituisce_400(self):
        res = auth_client(self.admin).post(URL_TRASFERTA_CREATE, {
            "data": "2025-01-06",
            "azienda": "Acme",
        }, format="json")
        self.assertEqual(res.status_code, 400)


class TestTrasfertaUpdate(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.trasferta = make_trasferta(self.utente)

    def test_owner_modifica_trasferta(self):
        res = auth_client(self.utente).put(
            URL_TRASFERTA_UPDATE(self.trasferta.id),
            {"azienda": "NuovaAzienda"},
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.trasferta.refresh_from_db()
        self.assertEqual(self.trasferta.azienda, "NuovaAzienda")

    def test_altro_utente_non_modifica_trasferta(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).put(
            URL_TRASFERTA_UPDATE(self.trasferta.id),
            {"azienda": "Hacker"},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_trasferta_validata_admin_non_modificabile(self):
        trasferta_validata = make_trasferta(
            self.utente,
            validation_level=Trasferta.ValidationLevel.VALIDATO_ADMIN
        )
        res = auth_client(self.utente).put(
            URL_TRASFERTA_UPDATE(trasferta_validata.id),
            {"azienda": "X"},
            format="json"
        )
        self.assertEqual(res.status_code, 403)


class TestTrasfertaValidation(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.trasferta = make_trasferta(self.utente)

    def test_admin_valida_trasferta(self):
        res = auth_client(self.admin).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.trasferta.refresh_from_db()
        self.assertEqual(
            self.trasferta.validation_level,
            Trasferta.ValidationLevel.VALIDATO_ADMIN
        )

    def test_utente_normale_non_valida_trasferta(self):
        res = auth_client(self.utente).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_trasferta_gia_validata_non_modificabile(self):
        trasferta_validata = make_trasferta(
            self.utente,
            validation_level=Trasferta.ValidationLevel.VALIDATO_ADMIN
        )
        res = auth_client(self.admin).patch(
            URL_TRASFERTA_VALID(trasferta_validata.id), format="json"
        )
        self.assertEqual(res.status_code, 403)


class TestTrasfertaDelete(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.trasferta = make_trasferta(self.utente)

    def test_owner_elimina_trasferta(self):
        res = auth_client(self.utente).delete(
            URL_TRASFERTA_DELETE(self.trasferta.id)
        )
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            Trasferta.objects.filter(id=self.trasferta.id).exists()
        )

    def test_altro_utente_non_elimina_trasferta(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).delete(
            URL_TRASFERTA_DELETE(self.trasferta.id)
        )
        self.assertEqual(res.status_code, 403)


# ---------------------------------------------------------------------------
# Spesa views
# ---------------------------------------------------------------------------

class TestSpesaCreate(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.trasferta = make_trasferta(self.utente)

    def test_owner_crea_spesa(self):
        res = auth_client(self.utente).post(
            URL_SPESA_CREATE(self.trasferta.id), {
                "type": Spesa.TrasfertaType.RISTORANTI,
                "importo": "25.00",
            }, format="json"
        )
        self.assertEqual(res.status_code, 201)

    def test_altro_utente_non_crea_spesa(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).post(
            URL_SPESA_CREATE(self.trasferta.id), {
                "type": Spesa.TrasfertaType.RISTORANTI,
                "importo": "25.00",
            }, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_trasferta_validata_non_accetta_nuove_spese(self):
        trasferta_validata = make_trasferta(
            self.utente,
            validation_level=Trasferta.ValidationLevel.VALIDATO_ADMIN
        )
        res = auth_client(self.utente).post(
            URL_SPESA_CREATE(trasferta_validata.id), {
                "type": Spesa.TrasfertaType.RISTORANTI,
                "importo": "25.00",
            }, format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_trasferta_inesistente_restituisce_404(self):
        res = auth_client(self.utente).post(
            URL_SPESA_CREATE(99999), {
                "type": Spesa.TrasfertaType.RISTORANTI,
                "importo": "25.00",
            }, format="json"
        )
        self.assertEqual(res.status_code, 404)


class TestSpesaUpdateDelete(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.trasferta = make_trasferta(self.utente)
        self.spesa = make_spesa(self.trasferta)

    def test_owner_modifica_spesa(self):
        res = auth_client(self.utente).put(
            URL_SPESA_MANAGE(self.spesa.id),
            {"importo": "50.00"},
            format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.spesa.refresh_from_db()
        self.assertEqual(self.spesa.importo, Decimal("50.00"))

    def test_altro_utente_non_modifica_spesa(self):
        altro = make_utente(email="altro@test.com")
        res = auth_client(altro).put(
            URL_SPESA_MANAGE(self.spesa.id),
            {"importo": "50.00"},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_owner_elimina_spesa(self):
        res = auth_client(self.utente).delete(URL_SPESA_MANAGE(self.spesa.id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Spesa.objects.filter(id=self.spesa.id).exists())

    def test_spesa_trasferta_validata_non_modificabile(self):
        trasferta_validata = make_trasferta(
            self.utente,
            validation_level=Trasferta.ValidationLevel.VALIDATO_ADMIN
        )
        spesa = make_spesa(trasferta_validata)
        res = auth_client(self.utente).put(
            URL_SPESA_MANAGE(spesa.id),
            {"importo": "99.00"},
            format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_spesa_trasferta_validata_non_eliminabile(self):
        trasferta_validata = make_trasferta(
            self.utente,
            validation_level=Trasferta.ValidationLevel.VALIDATO_ADMIN
        )
        spesa = make_spesa(trasferta_validata)
        res = auth_client(self.utente).delete(URL_SPESA_MANAGE(spesa.id))
        self.assertEqual(res.status_code, 403)
