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
from pathlib import Path
from django.conf import settings

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
URL_TE_RANGE_OVERRIDE = f"{BASE}/time-entries/range-override/"
URL_TE_BULK_VALIDATE  = f"{BASE}/time-entries/bulk-validate-month/"

URL_TRASFERTA_CREATE = f"{BASE}/trasferte/create/"
URL_TRASFERTA_UPDATE = lambda t_id: f"{BASE}/trasferte/{t_id}/"
URL_TRASFERTA_VALID  = lambda tr_id: f"{BASE}/trasferte/{tr_id}/validation/"
URL_TRASFERTA_DELETE = lambda t_id: f"{BASE}/trasferte/{t_id}/delete/"

URL_SPESA_CREATE     = lambda t_id: f"{BASE}/trasferte/{t_id}/spese/create/"
URL_SPESA_MANAGE     = lambda s_id: f"{BASE}/spese/{s_id}/"

URL_SCONTRINI_LIST   = lambda t_id: f"{BASE}/trasferte/{t_id}/scontrini/"
URL_SCONTRINO_DELETE = lambda t_id, filename: f"{BASE}/trasferte/{t_id}/scontrini/{filename}/delete/"


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
        self.assertEqual(res.status_code, 401)

    def test_login_senza_credenziali(self):
        res = self.client.post(URL_LOGIN, {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_login_utente_inattivo(self):
        self.utente.is_active = False
        self.utente.save()
        res = self.client.post(URL_LOGIN, {
            "email": "test@test.com", "password": "pass123"
        }, format="json")
        self.assertEqual(res.status_code, 401)


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
            "password": "Password123!",
            "nome": "Luca",
            "cognome": "Verdi",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Utente.objects.filter(email="nuovo@test.com").exists())

    def test_crea_account_crea_anche_saldo(self):
        self.admin_client.post(URL_CREATE_ACCOUNT, {
            "email": "nuovo@test.com",
            "password": "Password123!",
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

class TestUsersList(TestCase):

    def setUp(self):
        self.user = make_utente(email="user@test.com")
        self.admin = make_utente(
            email="admin@test.com",
            is_superuser=True,
            is_staff=True,
        )

    def test_utente_normale_non_puo_vedere_lista_utenti(self):
        res = auth_client(self.user).get(f"{BASE}/users/")
        self.assertEqual(res.status_code, 403)

    def test_admin_puo_vedere_lista_utenti(self):
        res = auth_client(self.admin).get(f"{BASE}/users/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("count", res.data)
        self.assertIn("results", res.data)

    def test_non_autenticato_restituisce_401(self):
        res = APIClient().get(f"{BASE}/users/")
        self.assertEqual(res.status_code, 401)
    

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
    def test_validazione_admin_sposta_da_sospeso_a_validato(self):
        saldo = Saldo.objects.get(utente=self.utente)
        saldo.valore_saldo_sospeso = Decimal("4.00")
        saldo.valore_saldo_validato = Decimal("0.00")
        saldo.save()

        te = make_timeentry(
            self.utente,
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            ore_tot=Decimal("4.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )

        res = auth_client(self.admin).patch(
            URL_TE_VALIDATION(te.id),
            {"validation_level": TimeEntry.ValidationLevel.VALIDATO_ADMIN},
            format="json"
        )
        self.assertEqual(res.status_code, 200)

        saldo.refresh_from_db()
        self.assertEqual(saldo.valore_saldo_sospeso, Decimal("0.00"))
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
        created = Trasferta.objects.latest("id")
        self.assertEqual(created.validation_level, Trasferta.ValidationLevel.AUTO)

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
    def test_owner_non_puo_cambiare_proprietario_trasferta(self):
        altro = make_utente(email="altro@test.com")

        res = auth_client(self.utente).put(
            URL_TRASFERTA_UPDATE(self.trasferta.id),
            {"utente": altro.id},
            format="json"
        )
        self.assertEqual(res.status_code, 200)

        self.trasferta.refresh_from_db()
        self.assertEqual(self.trasferta.utente_id, self.utente.id)

    def test_admin_puo_cambiare_proprietario_trasferta(self):
        altro = make_utente(email="altro@test.com")

        res = auth_client(self.admin).put(
            URL_TRASFERTA_UPDATE(self.trasferta.id),
            {"utente": altro.id},
            format="json"
        )
        self.assertEqual(res.status_code, 200)

        self.trasferta.refresh_from_db()
        self.assertEqual(self.trasferta.utente_id, altro.id)


class TestTrasfertaValidation(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com", is_superuser=True)
        self.trasferta = make_trasferta(self.utente)

    def test_owner_valida_trasferta_da_0_a_1(self):
        res = auth_client(self.utente).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.trasferta.refresh_from_db()
        self.assertEqual(
            self.trasferta.validation_level,
            Trasferta.ValidationLevel.VALIDATO_UTENTE
        )

    def test_admin_non_puo_validare_da_0_a_1(self):
        res = auth_client(self.admin).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_owner_non_puo_validare_da_1_a_2_su_endpoint_admin(self):
        self.trasferta.validation_level = Trasferta.ValidationLevel.VALIDATO_UTENTE
        self.trasferta.save(update_fields=["validation_level"])
        res = auth_client(self.utente).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_valida_trasferta_da_1_a_2(self):
        self.trasferta.validation_level = Trasferta.ValidationLevel.VALIDATO_UTENTE
        self.trasferta.save(update_fields=["validation_level"])
        res = auth_client(self.admin).patch(
            URL_TRASFERTA_VALID(self.trasferta.id), format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.trasferta.refresh_from_db()
        self.assertEqual(
            self.trasferta.validation_level,
            Trasferta.ValidationLevel.VALIDATO_ADMIN
        )

    def test_admin_non_valida_trasferta_da_0_a_2(self):
        res = auth_client(self.admin).patch(
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


class TestScontrinoDelete(TestCase):

    def setUp(self):
        self.utente = make_utente()
        self.altro = make_utente(email="altro@test.com")
        self.admin = make_utente(email="admin@test.com", is_superuser=True, is_staff=True)
        self.trasferta = make_trasferta(self.utente)

        folder = Path(settings.SCONTRINI_ROOT) / f"{self.trasferta.data.strftime('%Y-%m-%d')}_{self.trasferta.id}"
        folder.mkdir(parents=True, exist_ok=True)

        self.filename = "test.png"
        self.file_path = folder / self.filename
        self.file_path.write_bytes(b"fake-image-content")

    def test_owner_puo_eliminare_scontrino_se_trasferta_non_validata_admin(self):
        res = auth_client(self.utente).delete(
            URL_SCONTRINO_DELETE(self.trasferta.id, self.filename)
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.file_path.exists())

    def test_owner_non_puo_eliminare_scontrino_se_trasferta_validata_admin(self):
        self.trasferta.validation_level = Trasferta.ValidationLevel.VALIDATO_ADMIN
        self.trasferta.save(update_fields=["validation_level"])

        res = auth_client(self.utente).delete(
            URL_SCONTRINO_DELETE(self.trasferta.id, self.filename)
        )
        self.assertEqual(res.status_code, 403)
        self.assertTrue(self.file_path.exists())

    def test_altro_utente_non_puo_eliminare_scontrino(self):
        res = auth_client(self.altro).delete(
            URL_SCONTRINO_DELETE(self.trasferta.id, self.filename)
        )
        self.assertEqual(res.status_code, 403)
        self.assertTrue(self.file_path.exists())

    def test_admin_non_puo_eliminare_scontrino_se_trasferta_validata_admin(self):
        self.trasferta.validation_level = Trasferta.ValidationLevel.VALIDATO_ADMIN
        self.trasferta.save(update_fields=["validation_level"])

        res = auth_client(self.admin).delete(
            URL_SCONTRINO_DELETE(self.trasferta.id, self.filename)
        )
        self.assertEqual(res.status_code, 403)
        self.assertTrue(self.file_path.exists())

class TestChangePasswordExtra(TestCase):
    """Test per i controlli aggiunti dopo il fix #3 sul checkup."""
 
    def setUp(self):
        self.utente = make_utente(password="VecchiaPwd123!")
 
    def test_nuova_password_vuota_restituisce_400(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "VecchiaPwd123!",
            "new_password": "",
        }, format="json")
        self.assertEqual(res.status_code, 400)
        self.utente.refresh_from_db()
        self.assertTrue(self.utente.check_password("VecchiaPwd123!"))
 
    def test_nuova_password_mancante_restituisce_400(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "VecchiaPwd123!",
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_vecchia_password_mancante_restituisce_400(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "new_password": "NuovaPwd456!",
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_nuova_password_troppo_corta_restituisce_400(self):
        """
        Presuppone che AUTH_PASSWORD_VALIDATORS includa MinimumLengthValidator.
        Se nei tuoi settings il minimo Ã¨ diverso, adatta la stringa.
        """
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "VecchiaPwd123!",
            "new_password": "abc",
        }, format="json")
        self.assertEqual(res.status_code, 400)
        self.utente.refresh_from_db()
        self.assertTrue(self.utente.check_password("VecchiaPwd123!"))
 
    def test_nuova_password_uguale_alla_vecchia_restituisce_400(self):
        res = auth_client(self.utente).post(URL_CHANGE_PASSWORD, {
            "old_password": "VecchiaPwd123!",
            "new_password": "VecchiaPwd123!",
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
 
# ===========================================================================
# TimeEntry create â€” split automatico LAVORO -> VERSAMENTO + sync PRELIEVO
# ===========================================================================
 
class TestTimeEntryCreateSplit(TestCase):
    """
    Verifica il comportamento di TimeEntrySerializer.create():
    - Se LAVORO_ORDINARIO supera le ore contrattuali del giorno, viene splittato:
      una entry LAVORO_ORDINARIO con le ore contrattuali + una VERSAMENTO_BANCA_ORE
      con l'eccedenza.
    - Se LAVORO_ORDINARIO Ã¨ inferiore alle ore contrattuali, viene creata
      automaticamente una PRELIEVO_BANCA_ORE per coprire la differenza.
    """
 
    def setUp(self):
        self.utente = make_utente()
        make_saldo(self.utente)
        # Contratto 8h lun-ven
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])
        self.lunedi = "2025-01-06"  # Ã¨ un lunedÃ¬
 
    def test_lavoro_oltre_contratto_genera_versamento(self):
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "10.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)
 
        entries = TimeEntry.objects.filter(
            utente=self.utente, data=date(2025, 1, 6)
        ).order_by("type")
        # Mi aspetto: 1 LAVORO da 8h + 1 VERSAMENTO da 2h
        self.assertEqual(entries.count(), 2)
 
        lavoro = entries.get(type=TimeEntry.EntryType.LAVORO_ORDINARIO)
        versamento = entries.get(type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE)
        self.assertEqual(lavoro.ore_tot, Decimal("8.00"))
        self.assertEqual(versamento.ore_tot, Decimal("2.00"))
 
    def test_lavoro_sotto_contratto_genera_prelievo(self):
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "5.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)
 
        entries = TimeEntry.objects.filter(
            utente=self.utente, data=date(2025, 1, 6)
        )
        # Mi aspetto: 1 LAVORO da 5h + 1 PRELIEVO da 3h
        self.assertEqual(entries.count(), 2)
 
        lavoro = entries.get(type=TimeEntry.EntryType.LAVORO_ORDINARIO)
        prelievo = entries.get(type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE)
        self.assertEqual(lavoro.ore_tot, Decimal("5.00"))
        self.assertEqual(prelievo.ore_tot, Decimal("3.00"))
 
    def test_lavoro_pari_a_contratto_non_crea_extra(self):
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": self.lunedi,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)
 
        entries = TimeEntry.objects.filter(
            utente=self.utente, data=date(2025, 1, 6)
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().type, TimeEntry.EntryType.LAVORO_ORDINARIO)
 
    def test_lavoro_nel_weekend_non_genera_split(self):
        """Sabato (weekday=5): nessun contratto applicabile, nessuno split."""
        sabato = "2025-01-11"
        res = auth_client(self.utente).post(URL_TE_CREATE, {
            "utente_id": self.utente.id,
            "data": sabato,
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "6.00",
        }, format="json")
        self.assertEqual(res.status_code, 201)
 
        entries = TimeEntry.objects.filter(
            utente=self.utente, data=date(2025, 1, 11)
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().ore_tot, Decimal("6.00"))
 
 
# ===========================================================================
# TimeEntry detail PUT â€” ricalcolo PRELIEVO/VERSAMENTO sull'update
# ===========================================================================
 
class TestTimeEntryDetailUpdateSync(TestCase):
    """
    Verifica che modificando le ore di una LAVORO_ORDINARIO via PUT,
    il PRELIEVO o VERSAMENTO collegato venga ricalcolato correttamente.
    """
 
    def setUp(self):
        self.utente = make_utente()
        make_saldo(self.utente)
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])
        self.giorno = date(2025, 1, 6)  # lunedÃ¬
        # Crea LAVORO da 5h: il serializer aggiunge un PRELIEVO da 3h
        self.lavoro = make_timeentry(
            self.utente,
            data=self.giorno,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("5.00"),
        )
        # Simula il prelievo che il serializer avrebbe creato
        self.prelievo = make_timeentry(
            self.utente,
            data=self.giorno,
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            ore_tot=Decimal("3.00"),
        )
 
    def test_aumento_ore_lavoro_riduce_prelievo(self):
        res = auth_client(self.utente).put(URL_TE_DETAIL(self.lavoro.id), {
            "utente_id": self.utente.id,
            "data": self.giorno.isoformat(),
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "7.00",
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        self.prelievo.refresh_from_db()
        self.assertEqual(self.prelievo.ore_tot, Decimal("1.00"))
 
    def test_lavoro_pari_a_contratto_elimina_prelievo(self):
        res = auth_client(self.utente).put(URL_TE_DETAIL(self.lavoro.id), {
            "utente_id": self.utente.id,
            "data": self.giorno.isoformat(),
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "8.00",
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        self.assertFalse(
            TimeEntry.objects.filter(
                utente=self.utente,
                data=self.giorno,
                type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            ).exists()
        )
 
    def test_lavoro_oltre_contratto_genera_versamento(self):
        # Elimino prima il prelievo per non avere conflitti
        self.prelievo.delete()
        res = auth_client(self.utente).put(URL_TE_DETAIL(self.lavoro.id), {
            "utente_id": self.utente.id,
            "data": self.giorno.isoformat(),
            "type": TimeEntry.EntryType.LAVORO_ORDINARIO,
            "ore_tot": "10.00",
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        # LAVORO ridotto a 8h + nuovo VERSAMENTO da 2h
        self.lavoro.refresh_from_db()
        self.assertEqual(self.lavoro.ore_tot, Decimal("8.00"))
        versamento = TimeEntry.objects.get(
            utente=self.utente,
            data=self.giorno,
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
        )
        self.assertEqual(versamento.ore_tot, Decimal("2.00"))
 
 
# ===========================================================================
# TimeEntry range override
# ===========================================================================
 
class TestTimeEntryRangeOverride(TestCase):
    """
    Verifica timeentry_create_range_override:
    - Crea/sostituisce una sola entry per giorno lavorativo nel range
    - Salta sabato e domenica
    - Usa ore_sett del contratto attivo
    - Richiede contratto valido (ore_sett a 5 valori)
    """
 
    def setUp(self):
        self.utente = make_utente()
        self.altro = make_utente(email="altro@test.com")
        self.admin = make_utente(email="admin@test.com",
                                 is_superuser=True, is_staff=True)
        make_contratto(self.utente, ore_sett=[8, 8, 8, 8, 8])
 
    def test_crea_entry_per_giorni_lavorativi(self):
        # Lun 6 gen 2025 - Ven 10 gen 2025 = 5 giorni lavorativi
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["created"], 5)
        self.assertEqual(res.data["skipped_weekends"], 0)
 
        entries = TimeEntry.objects.filter(utente=self.utente)
        self.assertEqual(entries.count(), 5)
        for te in entries:
            self.assertEqual(te.type, TimeEntry.EntryType.FERIE)
            self.assertEqual(te.ore_tot, Decimal("8.00"))
 
    def test_salta_weekend(self):
        # Sab 11 - Dom 12 gen 2025
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-11",
            "dataE": "2025-01-12",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["created"], 0)
        self.assertEqual(res.data["skipped_weekends"], 2)
        self.assertEqual(TimeEntry.objects.filter(utente=self.utente).count(), 0)
 
    def test_sostituisce_entry_esistenti(self):
        # Esiste giÃ  una LAVORO_ORDINARIO il 6 gennaio
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("5.00"),
        )
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-06",
            "type": TimeEntry.EntryType.MALATTIA,
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        entries = TimeEntry.objects.filter(utente=self.utente, data=date(2025, 1, 6))
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().type, TimeEntry.EntryType.MALATTIA)
        self.assertEqual(entries.first().ore_tot, Decimal("8.00"))
 
    def test_utente_normale_non_puo_per_altri(self):
        res = auth_client(self.altro).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 403)
 
    def test_admin_puo_per_altri(self):
        res = auth_client(self.admin).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-06",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
    def test_data_inversa_restituisce_400(self):
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-10",
            "dataE": "2025-01-06",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_senza_contratto_restituisce_400(self):
        senza_contratto = make_utente(email="nocontract@test.com")
        res = auth_client(senza_contratto).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": senza_contratto.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_blocca_se_giorno_ha_entry_validato_admin(self):
        # Esiste una entry VALIDATO_ADMIN il 6 gennaio: tutto il range va bloccato
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("8.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        )
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertIn("errors", res.data)

    def test_blocca_non_modifica_nulla_anche_su_altri_giorni(self):
        # Il 6 gen Ã¨ VALIDATO_ADMIN. Il 7 gen ha una entry AUTO che NON deve essere toccata.
        admin_entry = make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("8.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        )
        auto_entry = make_timeentry(
            self.utente,
            data=date(2025, 1, 7),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("6.00"),
            validation_level=TimeEntry.ValidationLevel.AUTO,
        )
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 403)
        # Verifica che entrambe le entry preesistenti siano intatte
        admin_entry.refresh_from_db()
        self.assertEqual(admin_entry.type, TimeEntry.EntryType.LAVORO_ORDINARIO)
        self.assertEqual(admin_entry.ore_tot, Decimal("8.00"))
        self.assertEqual(admin_entry.validation_level, TimeEntry.ValidationLevel.VALIDATO_ADMIN)
        auto_entry.refresh_from_db()
        self.assertEqual(auto_entry.type, TimeEntry.EntryType.LAVORO_ORDINARIO)
        self.assertEqual(auto_entry.ore_tot, Decimal("6.00"))
        # Nessuna entry nuova creata
        self.assertEqual(TimeEntry.objects.filter(utente=self.utente).count(), 2)

    def test_blocca_anche_superuser(self):
        # Nemmeno il super puÃ² sovrascrivere una entry VALIDATO_ADMIN via range-override
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("8.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        )
        res = auth_client(self.admin).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-06",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_messaggio_errore_elenca_date_bloccanti(self):
        # Verifica che la response contenga le date coinvolte, cosÃ¬ il frontend puÃ² mostrarle
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        )
        make_timeentry(
            self.utente,
            data=date(2025, 1, 8),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            validation_level=TimeEntry.ValidationLevel.VALIDATO_ADMIN,
        )
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-10",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 403)
        err = res.data["errors"]
        self.assertIn("2025-01-06", err)
        self.assertIn("2025-01-08", err)

    def test_consente_modifica_se_tutte_le_entry_sono_sotto_validato_admin(self):
        # Entry VALIDATO_UTENTE (1) puÃ² essere sovrascritta
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal("8.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        res = auth_client(self.utente).post(URL_TE_RANGE_OVERRIDE, {
            "utente_id": self.utente.id,
            "dataS": "2025-01-06",
            "dataE": "2025-01-06",
            "type": TimeEntry.EntryType.FERIE,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        entry = TimeEntry.objects.get(utente=self.utente, data=date(2025, 1, 6))
        self.assertEqual(entry.type, TimeEntry.EntryType.FERIE)
# ===========================================================================
# TimeEntry bulk validate month
# ===========================================================================
 
class TestTimeEntryBulkValidateMonth(TestCase):
    """
    Verifica timeentry_bulk_validate_month nei due casi:
    - Caso utente normale: 0 -> 1 sulle proprie entry
    - Caso superuser: 1 -> 2 sulle entry di un utente specifico, con
      aggiornamento del saldo validato per VERSAMENTO/PRELIEVO
    """
 
    def setUp(self):
        self.utente = make_utente()
        self.admin = make_utente(email="admin@test.com",
                                 is_superuser=True, is_staff=True)
        make_saldo(self.utente)
 
    # --- Caso utente normale (0 -> 1) ---
 
    def test_utente_normale_valida_proprie_entry_da_0_a_1(self):
        # Crea 3 entry AUTO nel mese di gennaio 2025
        for d in [date(2025, 1, 6), date(2025, 1, 7), date(2025, 1, 8)]:
            make_timeentry(
                self.utente,
                data=d,
                validation_level=TimeEntry.ValidationLevel.AUTO,
            )
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count_updated"], 3)
 
        entries = TimeEntry.objects.filter(utente=self.utente)
        for te in entries:
            self.assertEqual(te.validation_level,
                             TimeEntry.ValidationLevel.VALIDATO_UTENTE)
 
    def test_utente_normale_non_tocca_entry_gia_a_livello_1(self):
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count_updated"], 0)
 
    def test_utente_normale_non_passa_utente_id_altrui(self):
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.admin.id,
        }, format="json")
        self.assertEqual(res.status_code, 403)
 
    def test_utente_normale_tocca_solo_il_mese_indicato(self):
        # Una entry a gennaio, una a febbraio
        make_timeentry(
            self.utente,
            data=date(2025, 1, 15),
            validation_level=TimeEntry.ValidationLevel.AUTO,
        )
        make_timeentry(
            self.utente,
            data=date(2025, 2, 15),
            validation_level=TimeEntry.ValidationLevel.AUTO,
        )
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-10",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count_updated"], 1)
 
        gen = TimeEntry.objects.get(utente=self.utente, data=date(2025, 1, 15))
        feb = TimeEntry.objects.get(utente=self.utente, data=date(2025, 2, 15))
        self.assertEqual(gen.validation_level,
                         TimeEntry.ValidationLevel.VALIDATO_UTENTE)
        self.assertEqual(feb.validation_level,
                         TimeEntry.ValidationLevel.AUTO)
 
    # --- Caso superuser (1 -> 2 + aggiornamento saldo) ---
 
    def test_superuser_valida_da_1_a_2(self):
        for d in [date(2025, 1, 6), date(2025, 1, 7)]:
            make_timeentry(
                self.utente,
                data=d,
                validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
            )
        res = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count_updated"], 2)
 
        for te in TimeEntry.objects.filter(utente=self.utente):
            self.assertEqual(te.validation_level,
                             TimeEntry.ValidationLevel.VALIDATO_ADMIN)
 
    def test_superuser_aggiorna_saldo_per_versamento(self):
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            ore_tot=Decimal("5.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        res = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        saldo = Saldo.objects.get(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, Decimal("5.00"))
        self.assertEqual(res.data["delta_saldo_validato"], "5.00")

    def test_superuser_seconda_chiamata_non_riapplica_delta(self):
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            ore_tot=Decimal("5.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        body = {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }

        res1 = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, body, format="json")
        res2 = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, body, format="json")

        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res1.data["count_updated"], 1)
        self.assertEqual(res2.data["count_updated"], 0)
        self.assertEqual(res1.data["delta_saldo_validato"], "5.00")
        self.assertEqual(res2.data["delta_saldo_validato"], "0.00")

        saldo = Saldo.objects.get(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, Decimal("5.00"))

    def test_superuser_aggiorna_saldo_per_prelievo_negativo(self):
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            ore_tot=Decimal("3.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        res = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }, format="json")
        self.assertEqual(res.status_code, 200)
 
        saldo = Saldo.objects.get(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, Decimal("-3.00"))
 
    def test_superuser_saldo_netto_versamento_e_prelievo(self):
        # 5h versamento + 2h prelievo = +3h netto
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            ore_tot=Decimal("5.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        make_timeentry(
            self.utente,
            data=date(2025, 1, 7),
            type=TimeEntry.EntryType.PRELIEVO_BANCA_ORE,
            ore_tot=Decimal("2.00"),
            validation_level=TimeEntry.ValidationLevel.VALIDATO_UTENTE,
        )
        auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }, format="json")
 
        saldo = Saldo.objects.get(utente=self.utente)
        self.assertEqual(saldo.valore_saldo_validato, Decimal("3.00"))
 
    def test_superuser_non_tocca_entry_a_livello_0(self):
        make_timeentry(
            self.utente,
            data=date(2025, 1, 6),
            validation_level=TimeEntry.ValidationLevel.AUTO,
        )
        res = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": self.utente.id,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count_updated"], 0)
 
        te = TimeEntry.objects.get(utente=self.utente)
        self.assertEqual(te.validation_level, TimeEntry.ValidationLevel.AUTO)
 
    # --- Validazione input ---
 
    def test_data_mancante_restituisce_400(self):
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {},
                                             format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_data_malformata_restituisce_400(self):
        res = auth_client(self.utente).patch(URL_TE_BULK_VALIDATE, {
            "data": "non-una-data",
        }, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_superuser_utente_inesistente_restituisce_404(self):
        res = auth_client(self.admin).patch(URL_TE_BULK_VALIDATE, {
            "data": "2025-01-15",
            "utente_id": 99999,
        }, format="json")
        self.assertEqual(res.status_code, 404)


