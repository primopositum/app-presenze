from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from presenze.models import Cliente, ContrattoCliente, Periodicita
from .helpers import auth_client, make_utente


BASE = "/presenze/api"
CLIENTI_URL = f"{BASE}/clienti/"
CONTRATTI_URL = f"{BASE}/contratti-clienti/"


class ClientiContrattiApiTests(TestCase):
    def setUp(self):
        self.user = make_utente()
        self.client = auth_client(self.user)
        self.cliente = Cliente.objects.create(nome="Acme Srl", indirizzo="Via Roma 1", telefono="0123456789")

    def create_contratto(self, **overrides):
        payload = {
            "contract_id": "ACME-2026-001",
            "client_id": self.cliente.id,
            "value": "1500.00",
            "pool_task": ["PROJ-1", "PROJ-2", "PROJ-3"],
            "start_date": "2026-08-01",
            "end_date": "2026-12-31",
        }
        payload.update(overrides)
        response = self.client.post(CONTRATTI_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_endpoints_richiedono_login(self):
        response = self.client.logout()
        self.assertIsNone(response)
        response = self.client.get(CLIENTI_URL)
        self.assertEqual(response.status_code, 401)

    def test_crud_cliente_e_contratto(self):
        create_cliente = self.client.post(
            CLIENTI_URL,
            {"nome": "Beta Spa", "indirizzo": "", "telefono": ""},
            format="json",
        )
        self.assertEqual(create_cliente.status_code, 201, create_cliente.data)
        beta_id = create_cliente.data["id"]

        update_cliente = self.client.patch(
            f"{CLIENTI_URL}{beta_id}/",
            {"telefono": "3331234567"},
            format="json",
        )
        self.assertEqual(update_cliente.status_code, 200, update_cliente.data)
        self.assertEqual(update_cliente.data["telefono"], "3331234567")

        contratto = self.create_contratto(client_id=beta_id)
        self.assertIsNone(contratto["periodicity"])
        self.assertEqual(contratto["contract_id"], "ACME-2026-001")
        self.assertEqual(contratto["client_id"], beta_id)
        self.assertEqual(contratto["current_value"], "1500.00")
        update_contratto = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"contract_id": "BETA-2026-001", "value": "2000.50", "end_date": "2027-01-01"},
            format="json",
        )
        self.assertEqual(update_contratto.status_code, 200, update_contratto.data)
        self.assertEqual(update_contratto.data["value"], "2000.50")
        self.assertEqual(update_contratto.data["contract_id"], "BETA-2026-001")
        self.assertEqual(update_contratto.data["end_date"], "2027-01-01")

        put_contratto = self.client.put(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {
                "client_id": beta_id,
                "contract_id": "BETA-2026-001",
                "value": "2100.00",
                "pool_task": ["PROJ-4"],
                "start_date": "2026-08-01",
                "end_date": "2027-01-01",
            },
            format="json",
        )
        self.assertEqual(put_contratto.status_code, 200, put_contratto.data)
        self.assertEqual(put_contratto.data["value"], "2100.00")

        self.assertEqual(self.client.delete(f"{CONTRATTI_URL}{contratto['id']}/").status_code, 204)
        self.assertEqual(self.client.delete(f"{CLIENTI_URL}{beta_id}/").status_code, 204)

    def test_contratto_richiede_cliente_esistente(self):
        response = self.client.post(
            CONTRATTI_URL,
            {
                "client_id": 999999,
                "contract_id": "UNKNOWN-2026-001",
                "value": "1.00",
                "start_date": "2026-08-01",
                "end_date": "2026-12-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_contract_id_deve_essere_univoco(self):
        self.create_contratto()
        response = self.client.post(
            CONTRATTI_URL,
            {
                "contract_id": "ACME-2026-001",
                "client_id": self.cliente.id,
                "value": "100.00",
                "start_date": "2027-01-01",
                "end_date": "2027-12-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("contract_id", response.data)

    def test_date_modificabili_dopo_la_creazione(self):
        contratto = self.create_contratto()
        response = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"end_date": "2027-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["end_date"], "2027-01-01")

    def test_contratto_rifiuta_date_incoerenti(self):
        response = self.client.post(
            CONTRATTI_URL,
            {
                "client_id": self.cliente.id,
                "contract_id": "ACME-2026-INVALID",
                "value": "100.00",
                "start_date": "2026-08-15",
                "end_date": "2026-08-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

    def test_periodicity_create_update_and_delete(self):
        contratto = self.create_contratto(
            periodicity={
                "periodic_value": "250.00",
                "period_days": 30,
                "first_meeting_date": "2026-08-15",
                "notification_days": 7,
            }
        )
        self.assertEqual(contratto["periodicity"]["period_days"], 30)
        self.assertTrue(Periodicita.objects.filter(contract_id=contratto["id"]).exists())

        updated = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {
                "periodicity": {
                    "periodic_value": "300.00",
                    "period_days": 60,
                    "first_meeting_date": "2026-09-15",
                    "notification_days": 10,
                }
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["periodicity"]["periodic_value"], "300.00")

        unchanged = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"value": "1600.00"},
            format="json",
        )
        self.assertEqual(unchanged.status_code, 200, unchanged.data)
        self.assertEqual(unchanged.data["periodicity"]["period_days"], 60)

        deleted = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"periodicity": None},
            format="json",
        )
        self.assertEqual(deleted.status_code, 200, deleted.data)
        self.assertIsNone(deleted.data["periodicity"])
        self.assertFalse(Periodicita.objects.filter(contract_id=contratto["id"]).exists())

    def test_periodicity_requires_all_fields_even_on_patch(self):
        contratto = self.create_contratto()
        response = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"periodicity": {"periodic_value": "250.00"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("periodicity", response.data)

    def test_pool_task_append_idempotente_e_rimozione_compatta(self):
        contratto = self.create_contratto()
        pool_url = f"{CONTRATTI_URL}{contratto['id']}/pool-task/"

        duplicated = self.client.post(pool_url, {"task": "PROJ-2"}, format="json")
        self.assertEqual(duplicated.status_code, 200, duplicated.data)
        self.assertEqual(duplicated.data["pool_task"], ["PROJ-1", "PROJ-2", "PROJ-3"])

        removed = self.client.delete(pool_url, {"task": "PROJ-2"}, format="json")
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertEqual(removed.data["pool_task"], ["PROJ-1", "PROJ-3"])

    def test_cliente_con_contratti_non_eliminabile(self):
        self.create_contratto()
        response = self.client.delete(f"{CLIENTI_URL}{self.cliente.id}/")
        self.assertEqual(response.status_code, 409)

    def test_delete_contratto_elimina_anche_periodicity(self):
        contratto = self.create_contratto(
            periodicity={
                "periodic_value": "250.00",
                "period_days": 30,
                "first_meeting_date": "2026-08-15",
                "notification_days": 7,
            }
        )
        self.assertTrue(Periodicita.objects.filter(contract_id=contratto["id"]).exists())
        response = self.client.delete(f"{CONTRATTI_URL}{contratto['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Periodicita.objects.filter(contract_id=contratto["id"]).exists())


class ContrattoClienteModelTests(TestCase):
    def test_current_value_matura_periodi_e_non_modifica_il_valore_firmato(self):
        cliente = Cliente.objects.create(nome="Acme Srl")
        contratto = ContrattoCliente.objects.create(
            contract_id="ACME-2026-PERIODICO",
            client=cliente,
            value=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 5, 31),
        )
        Periodicita.objects.create(
            contract=contratto,
            periodic_value=Decimal("100.00"),
            period_days=30,
            first_meeting_date=date(2026, 1, 15),
            notification_days=7,
        )

        self.assertTrue(contratto.is_periodic)
        self.assertEqual(contratto.value_at(date(2026, 4, 15)), Decimal("1300.00"))
        self.assertEqual(contratto.value_at(date(2026, 12, 31)), Decimal("1400.00"))
        contratto.refresh_from_db()
        self.assertEqual(contratto.value, Decimal("1000.00"))

    def test_current_value_non_matura_prima_del_primo_incontro(self):
        cliente = Cliente.objects.create(nome="Acme Srl")
        contratto = ContrattoCliente.objects.create(
            contract_id="ACME-2026-FUTURO",
            client=cliente,
            value=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
        )
        periodicita = Periodicita.objects.create(
            contract=contratto,
            periodic_value=Decimal("100.00"),
            period_days=30,
            first_meeting_date=date(2026, 6, 1),
            notification_days=7,
        )

        self.assertEqual(periodicita.periods_elapsed(date(2026, 5, 27)), 0)
        self.assertEqual(contratto.value_at(date(2026, 5, 27)), Decimal("1000.00"))

    def test_pool_task_non_accetta_duplicati(self):
        cliente = Cliente.objects.create(nome="Acme Srl")
        contratto = ContrattoCliente(
            contract_id="ACME-2026-001",
            client=cliente,
            value="10.00",
            pool_task=["PROJ-1", "PROJ-1"],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 31),
        )
        with self.assertRaises(ValidationError):
            contratto.full_clean()
