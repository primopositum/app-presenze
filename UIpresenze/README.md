# UIpresenze - Frontend SvelteKit

Frontend dell'applicazione Gestionale Presenze Trasferte, sviluppato con **SvelteKit**, **TypeScript** e **TailwindCSS**.

## 🚀 Avvio Rapido

### Sviluppo locale

```bash
# Installa dipendenze
npm install

# Avvia server di sviluppo (con proxy al backend su :7999)
npm run dev
```

Il frontend sarà disponibile su http://localhost:5173

### Docker

```bash
# Dalla root del progetto
docker compose up --build
```

Frontend: http://localhost:3623

## 📦 Script Disponibili

| Comando | Descrizione |
|---------|-------------|
| `npm run dev` | Avvia server sviluppo |
| `npm run build` | Build produzione |
| `npm run preview` | Anteprima build |
| `npm run check` | Type check TypeScript |
| `npm run lint` | Linting code |
| `npm run format` | Formattazione Prettier |
| `npm test` | Esegui test |

## 📚 Documentazione Completa

Per la documentazione dettagliata di componenti, servizi e architetture, vedi [`DOCUMENTAZIONE.md`](DOCUMENTAZIONE.md).

## 🔐 Autenticazione

L'applicazione utilizza **Bearer Token** per l'autenticazione. Il token viene:
- Ricevuto dopo il login
- Salvato in localStorage
- Incluso automaticamente in tutte le richieste API

## 🏗️ Architettura

```
src/
├── lib/
│   ├── api.ts              # Client API
│   ├── components/         # Componenti UI
│   ├── services/           # Servizi business logic
│   └── stores/             # Store Svelte (stato globale)
├── routes/                 # Routing SvelteKit
│   ├── login/
│   ├── presences/
│   ├── trasferte/
│   ├── auto/
│   └── profilo/
└── theme/
    └── palette.js          # Colori dell'app
```

## 🎨 Stack Tecnologico

- **Framework**: SvelteKit 2.x
- **Linguaggio**: TypeScript 5.x
- **Styling**: TailwindCSS 4.x
- **Build**: Vite 7.x
- **Test**: Vitest + Playwright

## 📝 Convenzioni di Sviluppo

- **Indentazione**: Tab
- **Quote**: Singole (`'`)
- **Componenti**: PascalCase (es. `TimeEntryCard.svelte`)
- **File**: kebab-case (es. `time-entries.ts`)

## 🤝 Contribuire

Leggi le linee guida generali nella [`CONTRIBUTING.md`](../CONTRIBUTING.md) alla root del progetto.
