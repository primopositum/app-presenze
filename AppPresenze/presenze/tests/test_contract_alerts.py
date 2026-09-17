from datetime import date
from io import StringIO

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from presenze.contract_alerts import email_contract_alert, meeting_to_notify
from presenze.models import Cliente, ContrattoCliente, Periodicita


class MeetingToNotifyTests(SimpleTestCase):
    # Incontri: 01/09, 01/10, 31/10, ... (ogni 30 giorni), preavviso 7 giorni
    FIRST = date(2026, 9, 1)

    def notify(self, today, period_days=30, notification_days=7):
        return meeting_to_notify(self.FIRST, period_days, notification_days, today)

    def test_alert_per_il_primo_incontro(self):
        self.assertEqual(self.notify(date(2026, 8, 25)), date(2026, 9, 1))

    def test_alert_per_gli_incontri_successivi(self):
        self.assertEqual(self.notify(date(2026, 9, 24)), date(2026, 10, 1))
        self.assertEqual(self.notify(date(2026, 10, 24)), date(2026, 10, 31))

    def test_nessun_alert_negli_altri_giorni(self):
        for today in (date(2026, 8, 1), date(2026, 8, 26), date(2026, 9, 1), date(2026, 9, 23), date(2026, 9, 25)):
            with self.subTest(today=today):
                self.assertIsNone(self.notify(today))

    def test_una_sola_mail_per_ciclo(self):
        days = [date.fromordinal(date(2026, 9, 2).toordinal() + offset) for offset in range(30)]
        self.assertEqual([day for day in days if self.notify(day)], [date(2026, 9, 24)])

    def test_preavviso_piu_lungo_del_periodo(self):
        self.assertEqual(self.notify(date(2026, 8, 22), period_days=7, notification_days=10), date(2026, 9, 1))
        self.assertEqual(self.notify(date(2026, 8, 29), period_days=7, notification_days=10), date(2026, 9, 8))


class EmailContractAlertTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Acme Srl")

    def create_periodic_contract(self, contract_id="ACME-2026-001", end_date=date(2026, 12, 31)):
        contract = ContrattoCliente.objects.create(
            contract_id=contract_id,
            client=self.cliente,
            value="1500.00",
            start_date=date(2026, 8, 1),
            end_date=end_date,
        )
        Periodicita.objects.create(
            contract=contract,
            periodic_value="250.00",
            period_days=30,
            first_meeting_date=date(2026, 9, 1),
            notification_days=7,
        )
        return contract

    def test_invia_una_mail_per_incontro_in_arrivo(self):
        self.create_periodic_contract()
        result = email_contract_alert(today=date(2026, 9, 24), recipients=["admin@example.com"])

        self.assertEqual((len(result.alerts), result.sent, result.failed), (1, 1, 0))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
        self.assertIn("ACME-2026-001", mail.outbox[0].subject)
        self.assertIn("01/10/2026", mail.outbox[0].body)

    def test_nessuna_mail_se_non_e_il_giorno_di_preavviso(self):
        self.create_periodic_contract()
        result = email_contract_alert(today=date(2026, 9, 25), recipients=["admin@example.com"])
        self.assertEqual(result.alerts, [])
        self.assertEqual(len(mail.outbox), 0)

    def test_nessun_alert_per_incontri_dopo_la_fine_del_contratto(self):
        self.create_periodic_contract(end_date=date(2026, 9, 30))
        result = email_contract_alert(today=date(2026, 9, 24), recipients=["admin@example.com"])
        self.assertEqual(result.alerts, [])
        self.assertEqual(len(mail.outbox), 0)

    def test_contratti_senza_periodicita_ignorati(self):
        ContrattoCliente.objects.create(
            contract_id="ACME-2026-002",
            client=self.cliente,
            value="100.00",
            start_date=date(2026, 8, 1),
        )
        result = email_contract_alert(today=date(2026, 9, 24), recipients=["admin@example.com"])
        self.assertEqual(result.alerts, [])

    def test_dry_run_non_invia(self):
        self.create_periodic_contract()
        result = email_contract_alert(today=date(2026, 9, 24), recipients=[], dry_run=True)
        self.assertEqual(len(result.alerts), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_senza_destinatari_errore_di_configurazione(self):
        with self.assertRaises(ImproperlyConfigured):
            email_contract_alert(today=date(2026, 9, 24), recipients=[])

    @override_settings(CONTRACT_ALERT_RECIPIENTS=["admin@example.com"])
    def test_command_invia_alert_per_la_data_indicata(self):
        self.create_periodic_contract()
        out = StringIO()
        call_command("email_contract_alert", "--date", "2026-09-24", stdout=out)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Email inviate: 1", out.getvalue())
