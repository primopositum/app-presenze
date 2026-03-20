# UIpresenze - Documentazione Completa

## Panoramica del Progetto

**UIpresenze** è un'applicazione web frontend per la gestione delle presenze e del tracking orario dei dipendenti. È sviluppata come **Single Page Application (SPA)** utilizzando **SvelteKit** con **TypeScript**, progettata per consumare le API di un backend (probabilmente Django-based, come indicato dalla configurazione nginx).

L'applicazione permette agli utenti di:
- Registrare le ore lavorate giornaliere
- Gestire ferie, permessi, malattie e altre tipologie di assenza
- Monitorare il saldo ore (banca ore)
- Gestire le trasferte aziendali con spese e scontrini
- Gestire il parco auto aziendale
- Validare mensilmente le presenze
- Generare report PDF delle presenze

---

## Stack Tecnologico

| Categoria | Tecnologia | Versione |
|-----------|------------|----------|
| **Framework** | SvelteKit | 2.43.x |
| **Linguaggio** | TypeScript | 5.9.x |
| **Runtime UI** | Svelte | 5.39.x |
| **Styling** | Tailwind CSS | 4.1.x |
| **Build Tool** | Vite | 7.1.x |
| **Testing** | Vitest + Playwright | 3.2.x |
| **Linting** | ESLint + Prettier | 9.x / 3.x |
| **Deployment** | Docker (Node + Nginx) | - |

### Dipendenze Principali

#### Development
- `@sveltejs/kit` - Framework SvelteKit
- `@sveltejs/adapter-static` - Adattatore per build statica
- `@tailwindcss/vite` - Plugin Vite per Tailwind CSS 4
- `@tailwindcss/forms`, `@tailwindcss/typography` - Plugin Tailwind
- `eslint-plugin-svelte` - Supporto ESLint per Svelte
- `mdsvex` - Supporto per file markdown in Svelte (.svx)
- `vitest`, `@vitest/browser` - Framework di testing
- `playwright` - Browser automation per test E2E

#### Produzione
- `@fortawesome/svelte-fontawesome` - Icone FontAwesome
- `@node-rs/argon2` - Hashing password (lato backend)
- `better-sqlite3` - Database SQLite (opzionale/build-time)
- `date-picker-svelte` - Componente date picker
- `konsta` - Libreria UI components mobile-style
- `mode-watcher` - Gestione dark/light mode
- `svelte-motion` - Animazioni per Svelte
- `emoji-mart` - Picker emoji

---

## Architettura del Progetto

### Struttura delle Directory

```
UIpresenze/
├── src/
│   ├── lib/                      # Libreria condivisa
│   │   ├── api.ts                # Client API con gestione auth
│   │   ├── components/           # Componenti UI riutilizzabili
│   │   │   ├── ctx/              # Context provider (TimeEntryFormProvider)
│   │   │   ├── loader/           # Componenti di loading
│   │   │   ├── ui/               # Componenti UI base
│   │   │   ├── AutoCard.svelte   # Card gestione auto
│   │   │   ├── ButtonGradient.svelte
│   │   │   ├── ChangeMonth.svelte
│   │   │   ├── ChangePasswordCard.svelte
│   │   │   ├── CreateTrasfertaForm.svelte
│   │   │   ├── ErrorCard.svelte
│   │   │   ├── FormSpesa.svelte
│   │   │   ├── Header.svelte     # Header di navigazione
│   │   │   ├── HippoSign.svelte  # Widget informativo ore
│   │   │   ├── HourBalance.svelte
│   │   │   ├── IconLinkBar.svelte
│   │   │   ├── LoadReceipts.svelte
│   │   │   ├── MapsPlugin.svelte
│   │   │   ├── Notification.svelte
│   │   │   ├── PreSetWeek.svelte
│   │   │   ├── ProfileCard.svelte
│   │   │   ├── SpeseCard.svelte
│   │   │   ├── TimeEntriesCalendar.svelte
│   │   │   ├── TimeEntryCard.svelte
│   │   │   └── TrasferteCard.svelte
│   │   ├── context/              # Provider di contesto Svelte
│   │   ├── hooks/                # Hook personalizzati
│   │   ├── images/               # Asset immagine
│   │   ├── services/             # Servizi business logic
│   │   │   ├── automobili.ts     # Gestione parco auto
│   │   │   ├── contratti.ts      # Gestione contratti
│   │   │   ├── timeEntries.ts    # Gestione ore/presenze
│   │   │   ├── trasferte.ts      # Gestione trasferte
│   │   │   └── users.ts          # Gestione utenti
│   │   └── stores/               # Store Svelte per stato globale
│   │       ├── auth.ts           # Stato autenticazione
│   │       ├── hourBalanceExtra.ts
│   │       ├── timeEntryReload.ts
│   │       └── timeEntryUser.ts
│   ├── routes/                   # Routing SvelteKit (file-based)
│   │   ├── auto/                 # Modulo gestione auto
│   │   ├── login/                # Pagina di login
│   │   ├── preMenu/              # Menu intermedio
│   │   ├── presences/            # Modulo presenze (core)
│   │   ├── profilo/              # Profilo utente
│   │   ├── trasferte/            # Modulo trasferte
│   │   ├── +error.svelte         # Pagina errore
│   │   ├── +layout.svelte        # Layout root
│   │   ├── +page.svelte          # Home page
│   │   └── +page.ts              # Logica home (prerendered)
│   ├── theme/
│   │   └── palette.js            # Palette colori dell'app
│   ├── app.css                   # Stili globali + Tailwind
│   ├── app.d.ts                  # Dichiarazioni TypeScript
│   ├── app.html                  # Template HTML base
│   ├── hooks.client.ts           # Hook lato client
│   └── hooks.server.ts           # Hook lato server
├── static/                       # Asset statici pubblici
│   ├── fonts/                    # Font personalizzati (Infinity)
│   ├── adam.png
│   ├── appresenze.png
│   ├── favicon.svg
│   ├── logo1.png
│   ├── logo2.png
│   ├── presence.png
│   ├── robots.txt
│   └── trasferte.png
├── build/                        # Output build produzione
├── .svelte-kit/                  # Generati da SvelteKit
├── node_modules/                 # Dipendenze npm
├── Dockerfile                    # Configurazione Docker
├── nginx.conf                    # Configurazione Nginx
├── package.json                  # Dipendenze e script
├── svelte.config.js              # Configurazione Svelte
├── tailwind.config.ts            # Configurazione Tailwind
├── tsconfig.json                 # Configurazione TypeScript
├── vite.config.ts                # Configurazione Vite + Vitest
├── vitest-setup-client.ts        # Setup test client
├── eslint.config.js              # Configurazione ESLint
├── .prettierrc                   # Configurazione Prettier
└── .npmrc                        # Configurazione npm
```

### Flusso di Autenticazione

L'applicazione utilizza un sistema di **Bearer Token** per l'autenticazione:

1. **Login**: L'utente inserisce email e password nella pagina `/login`
2. **Token Request**: Le credenziali vengono inviate a `/api/login/`
3. **Token Storage**: Il token ricevuto viene salvato in:
   - `localStorage` (chiave: `auth_state`)
   - Store Svelte `$auth` (reattivo)
4. **Richieste API**: Ogni richiesta include l'header `Authorization: Bearer <token>`
5. **Logout**: Il token viene rimosso e l'utente viene reindirizzato a `/login`

**Gestione Token Scaduto**: Se una richiesta riceve risposta `401 Unauthorized`, il sistema:
- Esegue automaticamente il logout
- Reindirizza alla pagina di login

### Gestione Utenti e Permessi

L'applicazione distingue tra due tipi di utenti:

| Tipo Utente | Permessi |
|-------------|----------|
| **Utente Standard** | Può gestire solo le proprie presenze, trasferte, profilo |
| **Superuser** | Può gestire presenze e profili di tutti gli utenti |

Il ruolo `is_superuser` viene verificato in tempo reale dallo store `$auth.user`.

---

## Moduli e Funzionalità

### 1. Modulo Presenze (`/presences`)

Il cuore dell'applicazione. Permette di:

- **Visualizzare calendario mensile** con ore lavorate per giorno
- **Inserire modifiche ore** per giorno specifico
- **Tipologie di registrazione**:
  - Tipo 1: Lavoro ordinario
  - Tipo 2: Ferie
  - Tipo 3: Versamento banca ore
  - Tipo 4: Prelievo banca ore
  - Tipo 5: Malattia
  - Tipo 6: Permesso ordinario
  - Tipo 7: Permesso studio
  - Tipo 8: Permesso 104
  - Tipo 9: Permesso ex festività
  - Tipo 10: Permesso ROL
  - Tipo 11: Congedo maternità/paternità
  - Tipo 12: Sciopero
  - Tipo 13: Festività

- **Validazione mensile**: Conferma definitiva delle presenze del mese (non più modificabili)
- **Generazione PDF**: Scarica report PDF delle presenze mensili
- **Note giornaliere**: Aggiungi note testuali a ciascun giorno
- **Calcolo ore attese**: Confronta ore lavorate vs ore contrattuali previste

**Componenti chiave**:
- `TimeEntriesCalendar.svelte` - Griglia calendario mensile
- `TimeEntryCard.svelte` - Form inserimento/modifica ore
- `HippoSign.svelte` - Widget riepilogo ore mese
- `HourBalance.svelte` - Card saldo ore

### 2. Modulo Trasferte (`/trasferte`)

Gestione delle trasferte aziendali:

- **Creazione trasferta**: Data, azienda, indirizzo
- **Associazione automobile**: Selezione auto dal parco aziendale
- **Gestione spese**:
  - Tipo 1: Vitto
  - Tipo 2: Alloggio
  - Tipo 3: Viaggio
  - Tipo 4: Altro
- **Upload scontrini**: Caricamento file giustificativi
- **Download dossier**: PDF riepilogativo trasferta
- **Validazione**: Approvazione trasferta da parte del responsabile

**API Service**: `src/lib/services/trasferte.ts`

### 3. Modulo Auto (`/auto`)

Gestione parco auto aziendale:

- **Elenco auto**: Visualizza tutte le auto attive/archiviate
- **Dettagli auto**: Marca, alimentazione, descrizione, coefficiente
- **Gestione coefficienti**: Modifica coefficienti di utilizzo
- **Upload PDF**: Caricamento documenti auto (es. bollette carburante)
- **Archiviazione**: Disattivazione auto senza eliminazione definitiva

**Tipi di alimentazione**:
- Benzina
- Diesel
- GPL
- Metano
- Elettrico
- Ibrida

**API Service**: `src/lib/services/automobili.ts`

### 4. Modulo Profilo (`/profilo`)

Gestione profilo utente:

- **Visualizzazione dati**: Nome, cognome, email, ruolo
- **Saldo ore**:
  - Saldo sospeso (ore non validate)
  - Saldo validato (ore confermate)
- **Contratti**:
  - Data assunzione
  - Data fine (se presente)
  - Tipologia contratto
  - Ore settimanali per giorno (Lun-Ven)
- **Cambio password**: Modifica password in sicurezza
- **Gestione superuser**: I superuser vedono tutti i profili utente

**API Service**: `src/lib/services/users.ts`

---

## Servizi API

### Struttura Comune

Tutti i servizi seguono un pattern comune per le richieste HTTP:

```typescript
async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path}`;
  const headers = new Headers(opts.headers || {});
  
  // Aggiungi Content-Type se c'è body JSON
  if (opts.json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  
  // Aggiungi token auth se presente
  const token = getAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const res = await fetch(url, { ...opts, headers });
  
  // Gestione errori
  if (!res.ok) {
    const message = /* estrai messaggio errore */;
    throw new Error(message);
  }
  
  return data;
}
```

### `timeEntries.ts` - Gestione Presenze

**Tipi**:
```typescript
type TimeEntry = {
  id: number;
  utente: string;
  type: number;           // 1-13 (vedi tabella sopra)
  ore_tot: string;        // Ore totali (formato decimale)
  data: string;           // YYYY-MM-DD
  validation_level: number; // 0=bozza, 1=inviato, 2=validato
  note?: string | null;
};
```

**Funzioni principali**:
| Funzione | Descrizione |
|----------|-------------|
| `getTimeEntriesFromMonth({ date, utenteId })` | Ottiene tutte le presenze del mese |
| `createTimeEntry(entry)` | Crea nuova registrazione ore |
| `updateTimeEntry(teId, entry)` | Modifica registrazione esistente |
| `deleteTimeEntry(teId)` | Elimina registrazione |
| `createTimeEntryRangeOverride(entry)` | Applica ore a un range di date |
| `updateTimeEntryValidation(entry)` | Valida un intero mese |
| `getMeseScorsoPdf(params)` | Genera PDF presenze |

### `trasferte.ts` - Gestione Trasferte

**Tipi**:
```typescript
type Trasferta = {
  id: number;
  utente_id: number;
  utente_nome: string;
  utente_cognome: string;
  automobile?: number | null;  // ID auto associata
  data: string;                 // YYYY-MM-DD
  azienda: string;
  indirizzo: string | null;
  note: string | null;
  validation_level: ValidationLevel; // 1=in attesa, 2=validata
};

type Spesa = {
  id: number;
  t_id: number;        // ID trasferta
  type: number;        // 1=Vitto, 2=Alloggio, 3=Viaggio, 4=Altro
  importo: string;
};
```

**Funzioni principali**:
| Funzione | Descrizione |
|----------|-------------|
| `getTrasferte(params)` | Lista trasferte (filtrabile) |
| `createTrasferta(payload)` | Crea nuova trasferta |
| `updateTrasferta(tId, payload)` | Modifica trasferta |
| `validateTrasferta(trId)` | Valida trasferta |
| `deleteTrasferta(tId)` | Elimina trasferta |
| `getSpeseByTrasferta(tId)` | Ottiene spese di una trasferta |
| `createSpesa(tId, payload)` | Aggiunge spesa a trasferta |
| `updateSpesa(sId, payload)` | Modifica spesa |
| `deleteSpesa(sId)` | Elimina spesa |
| `getScontriniByTrasferta(tId)` | Lista scontrini |
| `uploadScontrinoByTrasferta(tId, file)` | Carica scontrino |
| `getScontrinoByTrasferta(tId, filename)` | Download scontrino |
| `deleteScontrinoByTrasferta(tId, filename)` | Elimina scontrino |
| `getTrasfertaDossier(uId, data)` | PDF dossier trasferta |

### `automobili.ts` - Gestione Auto

**Tipi**:
```typescript
type Automobile = {
  id?: number;
  a_id?: number;           // ID alternativo
  marca: string;
  alimentazione: string;
  descrizione: string;
  is_active: boolean;
  coefficiente: number;    // Coefficiente di utilizzo
  data_creaz: string;
  data_upd: string;
};
```

**Funzioni principali**:
| Funzione | Descrizione |
|----------|-------------|
| `getAutomobili(params)` | Lista auto (filtrabile per stato) |
| `createAutomobile(payload)` | Crea nuova auto |
| `getAutomobileDetail(pk)` | Dettagli auto |
| `updateAutomobile(pk, payload)` | Modifica auto |
| `patchAutomobile(pk, payload)` | Update parziale |
| `updateAutomobileCoeff(pk, coefficiente)` | Aggiorna coefficiente |
| `updateAutomobileIsActive(pk, is_active)` | Attiva/disattiva |
| `deleteAutomobile(pk)` | Archivia/elimina auto |
| `uploadPDFauto(auto_id, file, mese_anno)` | Carica PDF auto |
| `getPDFautoCurrentMonthList()` | Lista PDF mese corrente |

### `users.ts` - Gestione Utenti

**Tipi**:
```typescript
type User = {
  id: number;
  nome: string;
  cognome?: string;
  email?: string;
  is_superuser?: boolean;
  saldo: {
    data: string;
    valore_saldo_sospeso: string;
    valore_saldo_validato: string;
  };
  contratti: Contratto[];
};

type Contratto = {
  data_ass: string;          // Data assunzione
  data_fine: string | null;  // Data fine
  is_active: boolean;
  tipologia: string;
  ore_sett: [
    string, string, string, string, string  // Lun-Ven
  ];
};
```

**Funzioni principali**:
| Funzione | Descrizione |
|----------|-------------|
| `fetchUsers()` | Lista tutti gli utenti (solo superuser) |
| `fetchProfiles()` | Ottieni profilo corrente |
| `refreshProfileUser()` | Aggiorna store profilo |
| `changePassword(entry)` | Cambia password |

### `contratti.ts` - Gestione Contratti

**Funzioni principali**:
| Funzione | Descrizione |
|----------|-------------|
| `updateContrattoOre(u_id, ore_sett)` | Aggiorna ore settimanali |
| `createContratto(u_id, contratto)` | Crea nuovo contratto |

---

## Store Svelte (Gestione Stato)

### `auth.ts` - Autenticazione

```typescript
type AuthState = {
  isAuthed: boolean;
  token: string | null;
  user: User | null;
};
```

**Metodi**:
- `init()` - Inizializza da localStorage
- `login(token, user)` - Effettua login
- `logout(options)` - Effettua logout
- `setUser(user)` - Aggiorna dati utente

### `timeEntryUser.ts` - Utente Corrente (Presenze)

Store dedicato per il contesto presenze. Mantiene i dati utente sincronizzati con il modulo presenze.

### `hourBalanceExtra.ts` - Saldo Extra

Permette di mostrare un saldo ore "aggiuntivo" (es. saldo del mese corrente non ancora validato).

```typescript
type HourBalanceExtra = {
  title: string;
  saldo: number;
  color?: [string, string];  // Gradiente colori
};
```

### `timeEntryReload.ts` - Trigger Ricarica

Store segnale per triggerare ricaricamenti dati nel modulo presenze.

---

## Configurazione e Build

### Variabili d'Ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `PUBLIC_API_BASE` | URL base delle API backend | Richiesta |

Configurare in `.env`:
```bash
PUBLIC_API_BASE=http://localhost:7999
```

### Script npm

```bash
# Sviluppo
npm run dev              # Avvia server sviluppo (hot reload)
npm run dev -- --port 3000  # Porta personalizzata

# Build
npm run build            # Build produzione
npm run preview          # Anteprima build produzione

# Quality
npm run check            # Type check TypeScript
npm run check:watch      # Type check in watch mode
npm run lint             # Lint code (ESLint + Prettier)
npm run format           # Formatta code con Prettier

# Test
npm test                 # Esegui tutti i test
npm run test:unit        # Test unitari in watch mode
```

### Configurazione TypeScript

```json
{
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "strict": true,
    "moduleResolution": "bundler",
    "skipLibCheck": true,
    "sourceMap": true
  }
}
```

### Configurazione Prettier

```json
{
  "useTabs": true,
  "singleQuote": true,
  "trailingComma": "none",
  "printWidth": 100,
  "plugins": ["prettier-plugin-svelte", "prettier-plugin-tailwindcss"]
}
```

**Convenzioni di stile**:
- **Indentazione**: Tab (non spazi)
- **Quote**: Singole (`'`)
- **Trailing comma**: Assenti
- **Lunghezza riga**: Max 100 caratteri

---

## Testing

### Configurazione Vitest

Il progetto utilizza **due progetti di test separati**:

1. **Client** (browser):
   - Ambiente: Browser (Playwright/Chromium)
   - File: `src/**/*.svelte.{test,spec}.{js,ts}`
   - Esclude: `src/lib/server/**`

2. **Server** (Node.js):
   - Ambiente: Node
   - File: `src/**/*.{test,spec}.{js,ts}`
   - Esclude: `src/**/*.svelte.{test,spec}.{js,ts}`

### Scrivere Test

**Test Componenti Svelte**:
```typescript
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import MyComponent from './MyComponent.svelte';

describe('MyComponent', () => {
  it('renders correctly', () => {
    const { container } = render(MyComponent, { props: { /* ... */ } });
    expect(container).toBeTruthy();
  });
});
```

**Test Servizi**:
```typescript
import { describe, it, expect, vi } from 'vitest';
import { getTimeEntriesFromMonth } from '$lib/services/timeEntries';

describe('timeEntries service', () => {
  it('fetches entries correctly', async () => {
    // Mock fetch...
  });
});
```

---

## Deployment

### Docker Build

Il `Dockerfile` utilizza una build **multi-stage**:

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:1.27-alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Comandi**:
```bash
# Build immagine
docker build -t uipresenze .

# Run container
docker run -p 80:80 uipresenze

# Docker Compose (con backend)
docker-compose up -d
```

### Configurazione Nginx

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: tutti i path servono index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy al backend Django
    location /presenze/ {
        proxy_pass http://backend:7999/presenze/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Deploy in Produzione

1. **Build locale**:
   ```bash
   npm run build
   ```

2. **Upload file statici**: Copia il contenuto di `build/` sul server web

3. **Configura reverse proxy**: Imposta nginx/Apache per:
   - Servire file statici
   - Proxyare `/presenze/` al backend
   - Gestire HTTPS (consigliato)

---

## Design System

### Palette Colori

Definita in `src/theme/palette.js`:

```javascript
{
  primary: { main: '#3695CF', contrastText: '#ffffff' },
  secondary: { main: '#E47B30', contrastText: '#ffffff' },
  background: { default: '#f8fafc', paper: '#ffffff' },
  text: { heading: '#334', primary: '#0f172a', muted: '#94a3b8' },
  state: { success: '#22c55e', danger: '#b00020', info: '#2563eb' },
  gradient: { from: '#44BCFF', via: '#FF44EC', to: '#FF675E' }
}
```

### Tailwind CSS

**Configurazione personalizzata** in `src/app.css`:

```css
@theme {
  --color-primary: #0ea5e9;
  --color-secondary: #9333ea;
  --color-accent: #f59e0b;
  --color-surface: #ffffff;
  --color-background: #f7f7fb;
  
  /* Font */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Mono', monospace;
  --font-infinity: 'Infinity', 'Inter', sans-serif;
}
```

**Font personalizzati**:
- **Infinity**: Font principale per titoli (caricato da `/fonts/`)
- **Fira Mono**: Font monospace per codice
- **Inter**: Font di sistema per testo

### Componenti UI

**ButtonGradient.svelte**:
- Bottone con gradiente animato
- Utilizzato per azioni primarie (Login, Logout, ecc.)

**HourBalance.svelte**:
- Card fluttuante per saldo ore
- Effetto hover con espansione
- Gradiente personalizzabile

**HippoSign.svelte**:
- Widget informativo ore mensili
- Mostra: ore svolte, ore da dare, ore rimanenti

**LoaderOverlay.svelte**:
- Overlay di loading a tutto schermo
- Utilizzato durante operazioni async

---

## Hook Personalizzati

### `handleFetch` (client)

Intercetta tutte le richieste fetch per aggiungere automaticamente il token di autenticazione:

```typescript
export const handleFetch: HandleFetch = async ({ request, fetch }) => {
  const token = get(auth).token;
  if (token) {
    const headers = new Headers(request.headers);
    if (!headers.has('authorization')) {
      headers.set('authorization', `Bearer ${token}`);
    }
    const res = await fetch(new Request(request, { headers }));
    
    // Gestione 401: logout automatico
    if (res.status === 401) {
      auth.logout({ redirect: false });
      await goto('/login');
    }
    return res;
  }
  return fetch(request);
};
```

### `handle` (server)

Hook server minimale (bearer-only):

```typescript
export const handle: Handle = async ({ event, resolve }) => {
  return resolve(event);
};
```

---

## Best Practices di Sviluppo

### 1. Gestione Errori API

Tutte le chiamate API devono essere avvolte in try-catch:

```typescript
try {
  const data = await getTimeEntriesFromMonth({ date: new Date() });
  entries = data.results;
} catch (e: any) {
  error = e?.message || 'Errore imprevisto';
}
```

### 2. Store Reattivi

Utilizzare sempre il prefisso `$` per accedere ai valori degli store in template:

```svelte
<script>
  import { auth } from '$lib/stores/auth';
</script>

{#if $auth.isAuthed}
  <p>Benvenuto, {$auth.user.nome}</p>
{/if}
```

### 3. Type Safety

Definire sempre i tipi per props, API response, e stati:

```typescript
type TimeEntry = {
  id: number;
  data: string;
  ore_tot: string;
};

export let entries: TimeEntry[] = [];
```

### 4. Gestione Loading

Utilizzare `LoaderOverlay` per operazioni async lunghe:

```svelte
<script>
  let loading = false;
  
  async function submit() {
    loading = true;
    try {
      await apiCall();
    } finally {
      loading = false;
    }
  }
</script>

<LoaderOverlay show={loading} />
```

### 5. Validazione Form

Validare sempre i dati prima di inviare:

```typescript
function validate() {
  if (!email.includes('@')) {
    error = 'Email non valida';
    return false;
  }
  if (password.length < 8) {
    error = 'Password troppo corta';
    return false;
  }
  return true;
}
```

---

## Risoluzione Problemi Comuni

### 1. Errore "401 Unauthorized"

**Causa**: Token scaduto o non valido

**Soluzione**:
- Effettuare logout e login nuovamente
- Verificare che il backend sia raggiungibile
- Controllare che `PUBLIC_API_BASE` sia configurato correttamente

### 2. Errore CORS in Sviluppo

**Causa**: Backend non configurato per accettare richieste dal frontend

**Soluzione**:
- Verificare che il proxy Vite sia attivo (`vite.config.ts`)
- Assicurarsi che il backend permetta CORS da `localhost:5173`

### 3. Build Fallisce con Errori TypeScript

**Causa**: Errori di tipo nel codice

**Soluzione**:
```bash
npm run check  # Identifica errori
npm run check:watch  # Monitora in tempo reale
```

### 4. Store Non Si Aggiorna

**Causa**: Modifica diretta invece di usare metodi dello store

**Soluzione**:
```typescript
// ❌ SBAGLIATO
$auth.user = newUser;

// ✅ CORRETTO
auth.setUser(newUser);
```

### 5. PDF Non Viene Generato

**Causa**: Backend non risponde o errore di autorizzazione

**Soluzione**:
- Verificare di essere autenticati
- Controllare che l'utente abbia le autorizzazioni
- Verificare i log del backend

---

## Glossario

| Termine | Significato |
|---------|-------------|
| **Banca Ore** | Sistema di accumulo ore lavorate in eccesso |
| **Validazione** | Conferma definitiva delle presenze mensili |
| **Superuser** | Utente con permessi di amministratore |
| **Trasferta** | Missione lavorativa fuori sede |
| **Dossier** | Pacchetto documenti di una trasferta |
| **Coefficient**e | Fattore moltiplicativo per calcolo rimborsi auto |
| **ROL** | Riduzione Orario di Lavoro (permessi retribuiti) |
| **104** | Permesso per assistenza disabili (Legge 104/92) |

---

## Risorse Utili

- [Documentazione Svelte](https://svelte.dev/docs)
- [Documentazione SvelteKit](https://kit.svelte.dev/docs)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vitest Docs](https://vitest.dev/)

---

## Contatti e Supporto

Per segnalazioni di bug o richieste di funzionalità, contattare il team di sviluppo.

**Ultimo aggiornamento**: Marzo 2026
**Versione**: 0.0.1
