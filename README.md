# Gestionale Presenze Trasferte

Sistema completo di gestione presenze e trasferte aziendali. Include backend Django REST API e frontend SvelteKit.

## 🚀 Funzionalità Principali

- **Gestione Presenze**: Registrazione delle presenze giornaliere con validazione
- **Trasferte**: Creazione e gestione trasferte con spese associate
- **Scontrini**: Upload e gestione scontrini per le trasferte
- **Report PDF**: Generazione automatica di report presenze e trasferte
- **Gestione Flotte**: Registro automobili aziendali con documentazione
- **UI Moderna**: Frontend reattivo sviluppato con SvelteKit + TailwindCSS
- **API REST**: Backend completo per integrazioni
- **Autenticazione**: Sistema di login con token Bearer

## 🛠️ Stack Tecnologico

| Componente | Tecnologia |
|------------|------------|
| **Backend** | Django 5.2 + Django REST Framework |
| **Frontend** | SvelteKit + TypeScript + TailwindCSS |
| **Database** | PostgreSQL (o SQLite per sviluppo) |
| **Container** | Docker + Docker Compose |
| **Linguaggi** | Python 3.12+, Node.js 20+ |

## 📋 Prerequisiti

- Python 3.12+
- Node.js 20+ (per sviluppo frontend)
- Docker e Docker Compose (opzionale ma consigliato)
- PostgreSQL (opzionale, il progetto supporta SQLite in fallback)

## 🚀 Installazione e Avvio

### Opzione A: Docker Compose (Consigliata)

1. Clona il repository:
```bash
git clone https://github.com/tuo-username/GestionalePresenzeTrasferte.git
cd GestionalePresenzeTrasferte
```

2. Copia i file di esempio per le variabili d'ambiente:
```bash
cp AppPresenze/.env.example AppPresenze/.env
cp UIPresenze/.env.example UIPresenze/.env
```

3. Modifica `AppPresenze/.env` con le tue configurazioni (se usi PostgreSQL)

4. Avvia tutti i servizi (backend + frontend):
```bash
docker compose up --build
```

5. Accesso all'applicazione:
   - **Frontend**: http://localhost:3623
   - **Backend API**: http://localhost:7999

### Opzione B: Avvio Locale (Sviluppo)

#### Backend (Django)

```bash
cd AppPresenze

# Crea virtualenv
python -m venv .venv

# Attiva virtualenv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Applica migrazioni
python manage.py migrate

# Crea superutente admin
python manage.py createsuperuser

# Avvia server di sviluppo
python manage.py runserver 0.0.0.0:7999
```

#### Frontend (SvelteKit)

Apri un nuovo terminale:

```bash
cd UIPresenze

# Installa dipendenze
npm install

# Avvia server di sviluppo (proxy automatico al backend su :7999)
npm run dev
```

Il frontend sarà disponibile su `http://localhost:5173`

## 👤 Primo Accesso

Dopo aver avviato il server, crea un utente amministratore:

```bash
cd AppPresenze
python manage.py createsuperuser
```

Segui le istruzioni per impostare email e password.

## 📚 Documentazione

La documentazione completa si trova nella cartella [`docs/`](docs/):

- [`how-to-install.md`](docs/how-to-install.md) - Guida all'installazione dettagliata
- [`endpoints.md`](docs/endpoints.md) - Referenza completa delle API
- [`guida-utente-minima.md`](docs/guida-utente-minima.md) - Guida per utenti finali

## 🔌 API Endpoints

Prefisso comune: `/presenze/api/`

### Autenticazione
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/login/` | Login e ottenimento token |
| POST | `/logout/` | Logout e invalidazione token |
| POST | `/getToken/` | Richiedi token con credenziali |

### Profile
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET, PUT | `/profile/` | Leggi/modifica profilo utente |
| POST | `/change-password/` | Cambia password |

### Time Entries
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/time-entries/` | Crea nuova presenza |
| GET | `/time-entries/from-month/` | Lista presenze per mese |
| PUT, DELETE | `/time-entries/<id>/` | Modifica/elimina presenza |

### Trasferte
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/trasferte/` | Lista trasferte |
| POST | `/trasferte/create/` | Crea trasferta |
| PUT | `/trasferte/<id>/` | Aggiorna trasferta |
| DELETE | `/trasferte/<id>/delete/` | Elimina trasferta |

### Spese e Scontrini
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET, POST | `/trasferte/<id>/spese/` | Gestione spese |
| GET, POST | `/trasferte/<id>/scontrini/` | Upload scontrini |
| DELETE | `/trasferte/<id>/scontrini/<file>/delete/` | Elimina scontrino |

### Automobili
| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET, POST | `/automobili/` | Gestione flotta auto |
| PUT, DELETE | `/automobili/<id>/` | Modifica/elimina auto |

Per il riferimento completo, vedi [`docs/endpoints.md`](docs/endpoints.md).

## 🔐 Variabili d'Ambiente

### Backend (`AppPresenze/.env`)

```ini
# Database (opzionale - se assente usa SQLite)
DB_NAME=gestionaledb
DB_USER=postgres
DB_PASSWORD=tua_password
DB_HOST=localhost
DB_PORT=5432

# Django Settings
SECRET_KEY=tua-secret-key-generata
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Porte
PORT=7999
```

### Frontend (`UIPresenze/.env`)

```ini
# Porta per sviluppo locale
PORT=5173

# Backend API URL (opzionale, default: http://localhost:7999)
# PUBLIC_API_URL=http://localhost:7999
```

## 📁 Struttura del Progetto

```
GestionalePresenzeTrasferte/
├── AppPresenze/              # Backend Django
│   ├── AppPresenze/          # Configurazione Django
│   ├── presenze/             # Applicazione principale
│   │   ├── models.py         # Modelli DB
│   │   ├── serializer.py     # Serializers API
│   │   ├── views/            # Views (auth, timeentries, trasferte...)
│   │   ├── tests.py          # Test backend ✨
│   │   └── urls.py           # Routing API
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── UIPresenze/               # Frontend SvelteKit
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts        # API client
│   │   │   ├── services/     # Servizi business logic
│   │   │   ├── stores/       # Store Svelte (auth, etc.)
│   │   │   ├── components/   # Componenti UI
│   │   │   └── *.test.ts     # Test frontend ✨
│   │   └── routes/           # Routing SvelteKit
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── docs/                     # Documentazione
│   ├── TESTING.md            # Guida ai test ✨
│   ├── endpoints.md
│   └── how-to-install.md
├── data/                     # Dati persistenti (generato)
│   ├── scontrini/
│   └── pdf/
├── docker-compose.yml
├── LICENSE
└── README.md
```

## 🧪 Sviluppo

### Applicare migrazioni (Backend)
```bash
cd AppPresenze
python manage.py makemigrations
python manage.py migrate
```

### Eseguire i Test

**Backend (Django):**
```bash
cd AppPresenze

# Tutti i test
python manage.py test

# Test specifici
python manage.py test presenze.tests.AuthenticationAPITest

# Con coverage
coverage run --source='.' manage.py test
coverage report
```

**Frontend (SvelteKit):**
```bash
cd UIPresenze

# Tutti i test
npm test

# Watch mode (auto-rerun)
npm run test:unit

# Test specifici
npm run test -- src/lib/stores/auth.test.ts

# Con coverage
npm run test -- --coverage
```

Per una guida completa ai test, vedi [`docs/TESTING.md`](docs/TESTING.md).

## 🐛 Risoluzione Problemi

### Il frontend non si connette al backend
- Verifica che il backend sia in esecuzione su porta 7999
- In Docker, il proxy nginx è già configurato correttamente
- In sviluppo locale, vite.config.ts include già il proxy

### Errori di build Docker
- Pulisci la cache: `docker compose build --no-cache`
- Verifica di avere Docker Desktop aggiornato

### Problemi con node_modules
- Elimina `UIPresenze/node_modules` e reinstalla: `npm ci`

## 🤝 Contribuire

I contributi sono benvenuti! Per favore:

1. Forka il progetto
2. Crea un branch per la tua feature (`git checkout -b feature/nuova-funzionalita`)
3. Commita le modifiche (`git commit -m 'Aggiunta nuova funzionalità'`)
4. Pusha il branch (`git push origin feature/nuova-funzionalita`)
5. Apri una Pull Request

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT - vedi il file [LICENSE](LICENSE) per i dettagli.

## ⚠️ Avviso Importante

Prima di pubblicare il repository:
- Non commitare mai file `.env` con credenziali reali
- Genera una nuova `SECRET_KEY` per Django
- Elimina eventuali log o backup con dati sensibili

## 📞 Supporto

Per problemi, bug o domande, apri una issue su GitHub o consulta la documentazione nella cartella `docs/`.
