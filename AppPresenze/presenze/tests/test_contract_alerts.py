from datetime import date
from io import StringIO

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from presenze.contract_alerts import (
    ALERT_TYPE_CONTRACT_EXPIRY,
    email_contract_alert,
    email_contract_report,
    meeting_to_notify,
    next_meeting,
)
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

    def test_invia_alert_trenta_giorni_prima_della_scadenza(self):
        ContrattoCliente.objects.create(
            contract_id="ACME-2026-EXP",
            client=self.cliente,
            value="100.00",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 10, 24),
        )

        result = email_contract_alert(today=date(2026, 9, 24), recipients=["admin@example.com"])

        self.assertEqual((len(result.alerts), result.sent, result.failed), (1, 1, 0))
        self.assertEqual(result.alerts[0].alert_type, ALERT_TYPE_CONTRACT_EXPIRY)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Scadenza contratto ACME-2026-EXP", mail.outbox[0].subject)
        self.assertIn("scade tra 30 giorni", mail.outbox[0].body)
        self.assertIn("24/10/2026", mail.outbox[0].body)

    def test_non_invia_alert_scadenza_in_un_giorno_diverso_da_trenta(self):
        ContrattoCliente.objects.create(
            contract_id="ACME-2026-NO-EXP",
            client=self.cliente,
            value="100.00",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 10, 23),
        )

        result = email_contract_alert(today=date(2026, 9, 24), recipients=["admin@example.com"])

        self.assertEqual(result.alerts, [])
        self.assertEqual(len(mail.outbox), 0)

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

    def test_command_accetta_destinatario_esplicito(self):
        self.create_periodic_contract()
        call_command(
            "email_contract_alert",
            "--date",
            "2026-09-24",
            "--to",
            "test@example.com,second@example.com",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["test@example.com", "second@example.com"])


class NextMeetingTests(SimpleTestCase):
    FIRST = date(2026, 9, 1)

    def test_prima_del_primo_incontro(self):
        self.assertEqual(next_meeting(self.FIRST, 30, date(2026, 8, 20)), self.FIRST)

    def test_il_giorno_dell_incontro_e_compreso(self):
        self.assertEqual(next_meeting(self.FIRST, 30, date(2026, 10, 1)), date(2026, 10, 1))

    def test_fra_due_incontri(self):
        self.assertEqual(next_meeting(self.FIRST, 30, date(2026, 10, 2)), date(2026, 10, 31))


class EmailContractReportTests(TestCase):
    TODAY = date(2026, 10, 2)

    setUp = EmailContractAlertTests.setUp
    create_periodic_contract = EmailContractAlertTests.create_periodic_contract

    def test_una_sola_mail_con_tutti_i_contratti_validi(self):
        self.create_periodic_contract()
        ContrattoCliente.objects.create(
            contract_id="ACME-2026-002", client=self.cliente, value="100.00", start_date=date(2026, 8, 1)
        )
        self.create_periodic_contract(contract_id="ACME-2025-OLD", end_date=date(2026, 9, 30))

        result = email_contract_report(today=self.TODAY, recipients=["admin@example.com"])

        self.assertTrue(result.sent)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("ACME-2026-001", body)
        self.assertIn("ACME-2026-002", body)
        self.assertNotIn("ACME-2025-OLD", body)
        self.assertIn("Prossimo incontro: 31/10/2026 (tra 29 giorni)", body)
        # 31/10, 30/11, 30/12: gli incontri che restano entro il 31/12.
        self.assertIn("Incontri mancanti a fine contratto: 3", body)
        self.assertIn("nessuna periodicita' impostata", body)

    def test_dry_run_non_invia_ma_prepara_il_testo(self):
        self.create_periodic_contract()
        result = email_contract_report(today=self.TODAY, recipients=[], dry_run=True)
        self.assertFalse(result.sent)
        self.assertIn("ACME-2026-001", result.body)
        self.assertEqual(len(mail.outbox), 0)

    def test_senza_destinatari_errore_di_configurazione(self):
        with self.assertRaises(ImproperlyConfigured):
            email_contract_report(today=self.TODAY, recipients=[])

    def test_command_con_destinatario_da_cli(self):
        self.create_periodic_contract()
        out = StringIO()
        call_command("email_contract_report", "--date", "2026-10-02", "--to", "test@example.com", stdout=out)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])
        self.assertIn("Email inviata", out.getvalue())

    @override_settings(CONTRACT_ALERT_RECIPIENTS=["admin@example.com"])
    def test_command_smtp_test_usa_i_destinatari_del_env(self):
        out = StringIO()
        call_command("email_contract_report", "--smtp-test", stdout=out)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
        self.assertIn("Prova servizio email", mail.outbox[0].subject)
        self.assertIn("Email di prova inviata", out.getvalue())
