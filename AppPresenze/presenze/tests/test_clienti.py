from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from presenze.models import Cliente, ContrattoCliente
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
            "cliente_id": self.cliente.id,
            "value": "1500.00",
            "pool_task": ["PROJ-1", "PROJ-2", "PROJ-3"],
            "data_creazione": "2026-08-01",
            "data_fine": "2026-12-31",
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

        contratto = self.create_contratto(cliente_id=beta_id)
        update_contratto = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"value": "2000.50"},
            format="json",
        )
        self.assertEqual(update_contratto.status_code, 200, update_contratto.data)
        self.assertEqual(update_contratto.data["value"], "2000.50")

        put_contratto = self.client.put(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"cliente_id": beta_id, "value": "2100.00", "pool_task": ["PROJ-4"]},
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
                "cliente_id": 999999,
                "value": "1.00",
                "data_creazione": "2026-08-01",
                "data_fine": "2026-12-31",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_date_non_modificabili_dopo_la_creazione(self):
        contratto = self.create_contratto()
        response = self.client.patch(
            f"{CONTRATTI_URL}{contratto['id']}/",
            {"data_fine": "2027-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("data_fine", response.data)

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


class ContrattoClienteModelTests(TestCase):
    def test_pool_task_non_accetta_duplicati(self):
        cliente = Cliente.objects.create(nome="Acme Srl")
        contratto = ContrattoCliente(
            cliente=cliente,
            value="10.00",
            pool_task=["PROJ-1", "PROJ-1"],
            data_creazione=date(2026, 8, 1),
            data_fine=date(2026, 12, 31),
        )
        with self.assertRaises(ValidationError):
            contratto.full_clean()
