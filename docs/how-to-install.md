# How To Install

## Prerequisiti

- Python 3.12+
- Docker + Docker Compose (opzionale ma consigliato)
- PostgreSQL (opzionale: il progetto puo usare SQLite in fallback)

## Opzione A: avvio con Docker Compose

1. Posizionati nella root del repo.
2. Verifica che il file `.env` esista in `AppPresenze/.env` se vuoi usare PostgreSQL.
3. Avvia:

```bash
docker compose up --build
```

4. Backend disponibile su `http://localhost:7999`

Note pratiche:
- Il compose monta volumi esterni per scontrini e PDF (`/mnt/scontrini`, `/mnt/pdf` nel container).
- La UI nel compose punta a `../UIpresenze` e gira su porta `3623`.

## Opzione B: avvio locale backend (senza Docker)

1. Entra in `AppPresenze`.
2. Crea virtualenv.
3. Installa dipendenze.
4. Applica migrazioni.
5. Avvia server.

```bash
cd AppPresenze
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:7999
```

Backend: `http://localhost:7999`

## Database

- Se `DB_NAME`, `DB_USER`, `DB_PASSWORD` (e host) sono presenti, usa PostgreSQL.
- Se mancano, usa SQLite (`AppPresenze/db.sqlite3`).

## Primo utente admin

```bash
cd AppPresenze
python manage.py createsuperuser
```

