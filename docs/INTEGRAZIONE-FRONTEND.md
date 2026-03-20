# Riepilogo Integrazione Frontend-Backend

Questo documento riepiloga le modifiche apportate per integrare il frontend SvelteKit nel repository unico con il backend Django.

## 📁 Struttura Finale del Repository

```
GestionalePresenzeTrasferte/
├── AppPresenze/              # Backend Django
│   ├── AppPresenze/          # Configurazione Django
│   ├── presenze/             # Applicazione principale
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore         # NUOVO
│   ├── .env.example          # NUOVO
│   └── backup.example.json   # NUOVO (dati esempio sanitized)
│
├── UIPresenze/               # Frontend SvelteKit (INTEGRATO)
│   ├── src/                  # Codice sorgente
│   ├── static/               # Asset statici
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf            # Proxy al backend
│   ├── .dockerignore         # NUOVO
│   ├── .env.example          # NUOVO
│   ├── README.md             # AGGIORNATO
│   └── DOCUMENTAZIONE.md     # Documentazione completa
│
├── data/                     # NUOVO - Dati persistenti
│   ├── scontrini/
│   └── pdf/
│
├── docs/                     # Documentazione
│   ├── README.md             # AGGIORNATO
│   ├── how-to-install.md
│   ├── endpoints.md
│   └── guida-utente-minima.md
│
├── scripts/                  # Script utility
│
├── docker-compose.yml        # AGGIORNATO - Servizi backend + frontend
├── .gitignore                # AGGIORNATO - Regole per Python + Node
├── LICENSE                   # NUOVO - MIT License
├── README.md                 # AGGIORNATO - Documentazione completa
└── CONTRIBUTING.md           # NUOVO - Linee guida contributi
```

## 🔄 Modifiche Apportate

### File Creati

| File | Scopo |
|------|-------|
| `LICENSE` | Licenza MIT per open source |
| `README.md` | Documentazione principale aggiornata |
| `CONTRIBUTING.md` | Linee guida per contributori |
| `AppPresenze/.env.example` | Template variabili backend |
| `AppPresenze/.dockerignore` | Ottimizzazione build Docker backend |
| `AppPresenze/backup.example.json` | Dati esempio sanitized |
| `UIPresenze/.env.example` | Template variabili frontend |
| `UIPresenze/.dockerignore` | Ottimizzazione build Docker frontend |
| `UIPresenze/README.md` | Documentazione frontend |
| `docs/README.md` | Panoramica documentazione |
| `data/` | Directory per dati persistenti |

### File Modificati

| File | Modifiche |
|------|-----------|
| `docker-compose.yml` | Integrato servizio UI, rimosso path hardcoded, aggiunta rete |
| `.gitignore` | Aggiunte regole per Node.js, Svelte, Vite |
| `AppPresenze/.gitignore` | Semplificato (ora usa root .gitignore) |

### File Eliminati

| File | Motivo |
|------|--------|
| `AppPresenze/backup.JSON` | Conteneva dati sensibili reali |
| `debug.log` | File di log con dati potenzialmente sensibili |
| `package-lock.json` (root) | Residuo non necessario |

## 🚀 Come Avviare il Progetto

### Docker (Consigliato)

```bash
# Dalla root del progetto
docker compose up --build
```

- Frontend: http://localhost:3623
- Backend: http://localhost:7999

### Sviluppo Locale

#### Backend
```bash
cd AppPresenze
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:7999
```

#### Frontend (nuovo terminale)
```bash
cd UIPresenze
npm install
npm run dev
```

Frontend: http://localhost:5173 (con proxy automatico al backend)

## 🔗 Integrazione Frontend-Backend

### Proxy Sviluppo (Vite)
Configurato in `UIPresenze/vite.config.ts`:
```typescript
server: {
  proxy: {
    '/presenze': {
      target: 'http://localhost:7999',
      changeOrigin: true
    }
  }
}
```

### Proxy Produzione (Nginx)
Configurato in `UIPresenze/nginx.conf`:
```nginx
location /presenze/ {
    proxy_pass http://backend:7999/presenze/;
}
```

## 📝 Prossimi Passi (Opzionali)

1. **Aggiornare GitHub Actions** per CI/CD (test automatici)
2. **Aggiungere screenshot** al README.md
3. **Configurare environment variables** per produzione
4. **Aggiungere script di deployment** in `scripts/`

## ⚠️ Note Importanti

- **Non committare mai `.env`** con dati reali
- **Generare nuova SECRET_KEY** per Django in produzione
- **Usare HTTPS** in produzione (configurare nginx/traefik)
- **Backup regolari** della directory `data/`

## 🎯 Vantaggi della Struttura Monorepo

- ✅ Unico repository da gestire
- ✅ Versioning coordinato frontend/backend
- ✅ Docker Compose per avviare tutto insieme
- ✅ Documentazione centralizzata
- ✅ Più facile per i contributori

---

*Documento creato il: 2026-03-19*
