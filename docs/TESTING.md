# Testing Guide - Gestionale Presenze Trasferte

Guida completa per eseguire e scrivere test nel progetto.

## 📋 Panoramica

Il progetto include test per:
- **Backend Django**: Modelli, API, autenticazione, permessi
- **Frontend SvelteKit**: Store, servizi API, componenti

## 🚀 Eseguire i Test

### Backend (Django)

```bash
# Dalla cartella AppPresenze
cd AppPresenze

# Esegui tutti i test
python manage.py test

# Esegui test di una specifica app
python manage.py test presenze

# Esegui test specifici
python manage.py test presenze.tests.AuthenticationAPITest

# Esegui test con output dettagliato
python manage.py test --verbosity=2

# Esegui test e genera coverage report
coverage run --source='.' manage.py test
coverage report
coverage html  # Genera report HTML in htmlcov/
```

### Frontend (SvelteKit)

```bash
# Dalla cartella UIPresenze
cd UIPresenze

# Esegui tutti i test
npm test

# Esegui test in watch mode (auto-rerun)
npm run test:unit

# Esegui test una volta
npm run test -- --run

# Esegui test specifici
npm run test -- src/lib/stores/auth.test.ts

# Esegui test con coverage
npm run test -- --coverage
```

## 📁 Struttura dei Test

### Backend

```
AppPresenze/presenze/tests.py
├── UtenteModelTest          # Test modello Utente
├── TimeEntryModelTest       # Test modello TimeEntry
├── AuthenticationAPITest    # Test API auth (login/logout)
├── TimeEntrySerializerTest  # Test serializer
└── PermissionTest           # Test permessi e autorizzazioni
```

### Frontend

```
UIPresenze/src/
├── lib/
│   ├── api.test.ts              # Test API client
│   ├── stores/auth.test.ts      # Test auth store
│   └── components/ErrorCard.test.ts  # Test componenti
```

## ✍️ Scrivere Nuovi Test

### Backend - Esempi

#### Test di un Modello

```python
from django.test import TestCase
from .models import Trasferta

class TrasfertaModelTest(TestCase):
    def test_create_trasferta_success(self):
        """Creazione trasferta valida"""
        user = Utente.objects.create_user(
            email='test@example.com',
            password='pass123'
        )
        
        trasferta = Trasferta.objects.create(
            utente=user,
            data='2025-01-15',
            azienda='Azienda Test',
            indirizzo='Via Roma 1'
        )
        
        self.assertEqual(trasferta.azienda, 'Azienda Test')
        self.assertEqual(trasferta.validation_level, 1)  # In attesa
```

#### Test di una API

```python
from rest_framework.test import APIClient
from rest_framework import status

class TrasfertaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Utente.objects.create_user(
            email='test@example.com',
            password='pass123'
        )
    
    def test_create_trasferta_authenticated(self):
        """Crea trasferta con utente autenticato"""
        # Login
        login = self.client.post('/presenze/api/login/', {
            'email': 'test@example.com',
            'password': 'pass123'
        })
        token = login.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        # Crea trasferta
        response = self.client.post('/presenze/api/trasferte/create/', {
            'data': '2025-01-15',
            'azienda': 'Azienda Test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trasferta.objects.count(), 1)
```

### Frontend - Esempi

#### Test di un Servizio

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getTrasferte, createTrasferta } from '$lib/services/trasferte';

describe('Trasferte Service', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetModules();
  });

  it('should fetch trasferte list', async () => {
    // Mock auth
    const { auth } = await import('$lib/stores/auth');
    auth.login('test-token', { id: 1 });
    
    // Mock fetch
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 1, azienda: 'Test' }]
    });
    
    const result = await getTrasferte({});
    
    expect(result).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/trasferte/'),
      expect.any(Object)
    );
  });

  it('should handle API errors', async () => {
    const { auth } = await import('$lib/stores/auth');
    auth.login('token', { id: 1 });
    
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Bad request' })
    });
    
    await expect(getTrasferte({})).rejects.toThrow('Bad request');
  });
});
```

#### Test di un Componente

```typescript
import { render, screen, fireEvent } from '@testing-library/svelte';
import ButtonGradient from '$lib/components/ButtonGradient.svelte';

describe('ButtonGradient Component', () => {
  it('renders button with label', () => {
    render(ButtonGradient, {
      props: { label: 'Click me' }
    });
    
    expect(screen.getByRole('button', { name: 'Click me' }))
      .toBeInTheDocument();
  });

  it('calls onClick handler when clicked', async () => {
    const handleClick = vi.fn();
    
    render(ButtonGradient, {
      props: { 
        label: 'Click me',
        onClick: handleClick
      }
    });
    
    await fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

## 📊 Best Practices

### Backend

1. **Usa setUp() per dati comuni**: Evita duplicazione
2. **Test isolati**: Ogni test deve essere indipendente
3. **Usa transaction.atomic()**: Per test che modificano il DB
4. **Testa sia successi che fallimenti**: Casi happy path + edge cases
5. **Nomi descrittivi**: `test_login_with_valid_credentials_success`

### Frontend

1. **Mocka fetch/HTTP calls**: Non fare chiamate reali
2. **Testa reattività**: Verifica che gli store notifichino i cambiamenti
3. **Usa Testing Library**: Query per ruolo/accessibilità, non per classe CSS
4. **Mocka localStorage**: Per test di persistenza
5. **Testa errori**: Gestisci casi di fallback

## 🔧 Configurazione

### Backend

I test Django usano un database separato (`test_` prefisso). Configurazione in `settings.py`:

```python
# Il test runner usa DATABASES con nome 'test_' + DB_NAME
# Per PostgreSQL:
TEST_DATABASE_NAME = 'test_gestionaledb'
```

### Frontend

Configurazione Vitest in `vite.config.ts`:

```typescript
test: {
  include: ['src/**/*.{test,spec}.{js,ts}'],
  environment: 'node',
  globals: true,
  setupFiles: ['./vitest-setup-client.ts']
}
```

## 📈 Coverage Target

Obiettivi minimi di copertura:

| Componente | Target | Attuale |
|------------|--------|---------|
| Models     | 90%    | -       |
| Serializers| 80%    | -       |
| Views/API  | 70%    | -       |
| Auth       | 95%    | -       |
| Components | 60%    | -       |

## 🐛 Debug dei Test

### Backend

```bash
# Aggiungi print debugging
python manage.py test --debug-mode

# Usa pdb (Python debugger)
import pdb; pdb.set_trace()

# Test singolo con logging
python manage.py test presenze.tests.AuthenticationAPITest.test_login_success -v 3
```

### Frontend

```bash
# Console.log nei test
console.log('Debug:', variable)

# Test in watch mode per vedere cambiamenti in tempo reale
npm run test:unit -- --watch

# Ispeziona errori dettagliati
npm run test -- --reporter=verbose
```

## 📚 Risorse

- **Django Testing**: https://docs.djangoproject.com/en/stable/topics/testing/
- **DRF Testing**: https://www.django-rest-framework.org/api-guide/testing/
- **Vitest**: https://vitest.dev/
- **Testing Library**: https://testing-library.com/docs/svelte-testing-library/intro/
- **SvelteKit Testing**: https://kit.svelte.dev/docs/testing

## 🆘 Risoluzione Problemi

### "Database does not exist"

```bash
# Backend: assicurati che il DB sia configurato
python manage.py migrate
python manage.py test --keepdb
```

### "localStorage is not defined"

```typescript
// Frontend: mocka localStorage nei test
beforeEach(() => {
  localStorage.clear();
});
```

### "Import not found"

```bash
# Frontend: assicurati che i path siano corretti
# Usa alias $lib per src/lib
import { auth } from '$lib/stores/auth';
```

## 🎯 Prossimi Step

1. **Aggiungi test per servizi frontend**: `trasferte.ts`, `timeEntries.ts`
2. **Test di integrazione**: End-to-end con Playwright
3. **Test di performance**: Benchmark per query lente
4. **CI/CD**: Esegui test automaticamente su ogni push

---

*Ultimo aggiornamento: 2026-03-19*
