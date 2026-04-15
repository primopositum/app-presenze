"""
helpers.py — funzioni di supporto condivise tra tutti i file di test.

Ogni funzione accetta parametri con valori di default sensati,
in modo da poter creare oggetti minimali con una sola riga
o personalizzarli dove necessario.
"""

from decimal import Decimal
from datetime import date

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from presenze.models import (
    Utente, TimeEntry, Saldo, Contratto,
    Automobile, Trasferta, Spesa,
)


# ---------------------------------------------------------------------------
# Utente
# ---------------------------------------------------------------------------

def make_utente(email="test@test.com", nome="Mario", cognome="Rossi",
                password="testpass123", is_superuser=False, is_staff=False):
    user = Utente.objects.create(
        email=email,
        nome=nome,
        cognome=cognome,
        is_superuser=is_superuser,
        is_staff=is_staff,
    )
    user.set_password(password)
    user.save()
    return user


# ---------------------------------------------------------------------------
# Saldo
# ---------------------------------------------------------------------------

def make_saldo(utente, validato=Decimal("0.00"), sospeso=Decimal("0.00")):
    return Saldo.objects.create(
        utente=utente,
        valore_saldo_validato=validato,
        valore_saldo_sospeso=sospeso,
    )


# ---------------------------------------------------------------------------
# Contratto
# ---------------------------------------------------------------------------

def make_contratto(utente, ore_sett=None, tipologia="Full-time",
                   data_ass=None, data_fine=None, is_active=True, **kwargs):
    return Contratto.objects.create(
        utente=utente,
        ore_sett=ore_sett or [8, 8, 8, 8, 8],
        tipologia=tipologia,
        data_ass=data_ass or date(2020, 1, 1),
        data_fine=data_fine,
        is_active=is_active,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------

def make_timeentry(utente, data=None, type=TimeEntry.EntryType.LAVORO_ORDINARIO,
                   ore_tot=8, validation_level=TimeEntry.ValidationLevel.AUTO,
                   **kwargs):
    return TimeEntry.objects.create(
        utente=utente,
        data=data or timezone.localdate(),
        type=type,
        ore_tot=ore_tot,
        validation_level=validation_level,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Automobile
# ---------------------------------------------------------------------------

def make_automobile(marca="Fiat", alimentazione="Benzina",
                    coefficiente=Decimal("0.3000"), is_active=True):
    return Automobile.objects.create(
        marca=marca,
        alimentazione=alimentazione,
        coefficiente=coefficiente,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Trasferta
# ---------------------------------------------------------------------------

def make_trasferta(utente, data=None, azienda="Acme", automobile=None,
                   validation_level=Trasferta.ValidationLevel.VALIDATO_UTENTE):
    return Trasferta.objects.create(
        utente=utente,
        data=data or timezone.localdate(),
        azienda=azienda,
        automobile=automobile,
        validation_level=validation_level,
    )


# ---------------------------------------------------------------------------
# Spesa
# ---------------------------------------------------------------------------

def make_spesa(trasferta, type=Spesa.TrasfertaType.RISTORANTI,
               importo=Decimal("25.00")):
    return Spesa.objects.create(
        trasferta=trasferta,
        type=type,
        importo=importo,
    )


# ---------------------------------------------------------------------------
# APIClient autenticato
# ---------------------------------------------------------------------------

def auth_client(utente):
    """Restituisce un APIClient autenticato via JWT Bearer token."""
    client = APIClient()
    refresh = RefreshToken.for_user(utente)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client
