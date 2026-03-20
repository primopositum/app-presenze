"""
Backend Tests - Gestionale Presenze Trasferte

Test suite for Django backend covering:
- Models (Utente, TimeEntry)
- Authentication (login, logout, token management)
- Serializers
- API endpoints

Run with: python manage.py test presenze.tests
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from decimal import Decimal
from datetime import date, timedelta

from .models import Utente, TimeEntry

Utente = get_user_model()


# ============================================================
# MODEL TESTS
# ============================================================

class UtenteModelTest(TestCase):
    """Test del modello Utente (custom user model)"""

    def test_create_user_success(self):
        """Creazione utente standard con email e password"""
        user = Utente.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_user_without_password(self):
        """Creazione utente senza password (login disabilitato)"""
        user = Utente.objects.create_user(email='nopass@example.com')
        
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.is_active)

    def test_create_user_without_email_fails(self):
        """Creazione utente senza email deve fallire"""
        with self.assertRaises(ValueError):
            Utente.objects.create_user(password='testpass123')

    def test_create_superuser_success(self):
        """Creazione superuser con tutti i permessi"""
        admin = Utente.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertTrue(admin.check_password('adminpass123'))
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_active)

    def test_create_superuser_missing_staff_flag(self):
        """Superuser deve avere is_staff=True"""
        with self.assertRaises(ValueError):
            Utente.objects.create_superuser(
                email='admin@example.com',
                password='pass123',
                is_staff=False
            )

    def test_create_superuser_missing_superuser_flag(self):
        """Superuser deve avere is_superuser=True"""
        with self.assertRaises(ValueError):
            Utente.objects.create_superuser(
                email='admin@example.com',
                password='pass123',
                is_superuser=False
            )

    def test_user_str_representation(self):
        """Rappresentazione stringa dell'utente"""
        user = Utente.objects.create_user(
            email='test@example.com',
            password='pass123'
        )
        self.assertEqual(str(user), 'test@example.com')


class TimeEntryModelTest(TestCase):
    """Test del modello TimeEntry"""

    def setUp(self):
        self.user = Utente.objects.create_user(
            email='test@example.com',
            password='pass123'
        )

    def test_create_time_entry_success(self):
        """Creazione time entry valida"""
        entry = TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        
        self.assertEqual(entry.utente, self.user)
        self.assertEqual(entry.type, TimeEntry.EntryType.LAVORO_ORDINARIO)
        self.assertEqual(entry.ore_tot, Decimal('8.00'))
        self.assertEqual(entry.validation_level, TimeEntry.ValidationLevel.AUTO)

    def test_time_entry_choices_are_valid(self):
        """Verifica che i choices per type siano corretti"""
        # Test tutti i tipi di entry
        for entry_type in TimeEntry.EntryType:
            entry = TimeEntry.objects.create(
                utente=self.user,
                type=entry_type,
                ore_tot=Decimal('4.00'),
                data=date.today() - timedelta(days=entry_type.value)  # Date diverse
            )
            self.assertEqual(entry.type, entry_type)

    def test_time_entry_validation_level_default(self):
        """Validation level default è AUTO"""
        entry = TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.FERIE,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        self.assertEqual(entry.validation_level, TimeEntry.ValidationLevel.AUTO)

    def test_time_entry_unique_constraint(self):
        """Vincolo di unicità su utente, data, type"""
        TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        
        # Tentativo di creare entry duplicata
        with self.assertRaises(Exception):
            TimeEntry.objects.create(
                utente=self.user,
                type=TimeEntry.EntryType.LAVORO_ORDINARIO,
                ore_tot=Decimal('4.00'),
                data=date.today()
            )

    def test_time_entry_decimal_precision(self):
        """Precisione decimale per ore_tot"""
        entry = TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.50'),
            data=date.today()
        )
        self.assertEqual(entry.ore_tot, Decimal('8.50'))


# ============================================================
# AUTHENTICATION TESTS
# ============================================================

class AuthenticationAPITest(TestCase):
    """Test delle API di autenticazione"""

    def setUp(self):
        self.client = APIClient()
        self.user = Utente.objects.create_user(
            email='test@example.com',
            password='testpass123',
            nome='Test',
            cognome='User'
        )
        self.login_url = reverse('presenze:login')  # Aggiusta il name in base a urls.py
        self.logout_url = reverse('presenze:logout')

    def test_login_with_email_success(self):
        """Login con email e password corretti"""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['token_type'], 'Bearer')
        self.assertEqual(response.data['user']['email'], 'test@example.com')

    def test_login_with_wrong_password_fails(self):
        """Login con password errata"""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_login_with_nonexistent_email_fails(self):
        """Login con email inesistente"""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_without_credentials_fails(self):
        """Login senza credenziali"""
        response = self.client.post(self.login_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_success(self):
        """Logout con token valido"""
        # Login per ottenere token
        login_response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        token = login_response.data['token']
        
        # Setup client con token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        # Logout
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verifica che il token sia stato invalidato
        response = self.client.get('/presenze/api/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_token_fails(self):
        """Logout senza token"""
        self.client.credentials()
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================
# SERIALIZER TESTS
# ============================================================

class TimeEntrySerializerTest(TestCase):
    """Test del TimeEntrySerializer"""

    def setUp(self):
        self.user = Utente.objects.create_user(
            email='test@example.com',
            password='pass123'
        )

    def test_serializer_create_basic(self):
        """Creazione base di time entry tramite serializer"""
        data = {
            'utente_id': self.user.id,
            'type': TimeEntry.EntryType.LAVORO_ORDINARIO,
            'ore_tot': '8.00',
            'data': str(date.today())
        }
        
        from .serializer import TimeEntrySerializer
        serializer = TimeEntrySerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        entry = serializer.save()
        
        self.assertEqual(entry.utente, self.user)
        self.assertEqual(entry.ore_tot, Decimal('8.00'))

    def test_serializer_lavoro_ordinario_split(self):
        """Split automatico quando lavoro ordinario > 8 ore"""
        data = {
            'utente_id': self.user.id,
            'type': TimeEntry.EntryType.LAVORO_ORDINARIO,
            'ore_tot': '10.00',
            'data': str(date.today())
        }
        
        from .serializer import TimeEntrySerializer
        serializer = TimeEntrySerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        entry = serializer.save()
        
        # Verifica entry lavoro ordinario (8 ore)
        self.assertEqual(entry.ore_tot, Decimal('8.00'))
        
        # Verifica entry banca ore creata (2 ore)
        banca_entry = TimeEntry.objects.filter(
            utente=self.user,
            type=TimeEntry.EntryType.VERSAMENTO_BANCA_ORE,
            data=date.today()
        ).first()
        
        self.assertIsNotNone(banca_entry)
        self.assertEqual(banca_entry.ore_tot, Decimal('2.00'))


# ============================================================
# PERMISSION TESTS
# ============================================================

class PermissionTest(TestCase):
    """Test dei permessi e autorizzazioni"""

    def setUp(self):
        self.client = APIClient()
        
        # Utente standard
        self.user = Utente.objects.create_user(
            email='user@example.com',
            password='pass123'
        )
        
        # Superuser
        self.admin = Utente.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )

    def test_user_can_access_own_data(self):
        """Utente standard può accedere ai propri dati"""
        # Crea time entry per l'utente
        TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        
        # Login come user
        login_response = self.client.post('/presenze/api/login/', {
            'email': 'user@example.com',
            'password': 'pass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        # Prova ad accedere alle proprie entries
        response = self.client.get('/presenze/api/time-entries/from-month/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_access_other_user_data(self):
        """Utente standard NON può accedere a dati di altri utenti"""
        # Crea time entry per un altro utente
        other_user = Utente.objects.create_user(
            email='other@example.com',
            password='pass123'
        )
        other_entry = TimeEntry.objects.create(
            utente=other_user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        
        # Login come user
        login_response = self.client.post('/presenze/api/login/', {
            'email': 'user@example.com',
            'password': 'pass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        # Prova ad accedere all'entry dell'altro utente (dovrebbe fallire o filtrare)
        response = self.client.get(f'/presenze/api/time-entries/{other_entry.id}/')
        
        # Dovrebbe restituire 404 o 403
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ])

    def test_superuser_can_access_all_data(self):
        """Superuser può accedere a tutti i dati"""
        # Crea time entry per un utente
        TimeEntry.objects.create(
            utente=self.user,
            type=TimeEntry.EntryType.LAVORO_ORDINARIO,
            ore_tot=Decimal('8.00'),
            data=date.today()
        )
        
        # Login come admin
        login_response = self.client.post('/presenze/api/login/', {
            'email': 'admin@example.com',
            'password': 'adminpass123'
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        # Superuser dovrebbe poter accedere a tutte le entries
        response = self.client.get('/presenze/api/time-entries/from-month/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
