# UIpresenze - Project Context

## Project Overview

**UIpresenze** is a frontend web application for attendance/time tracking management. It is built as a Single Page Application (SPA) using **SvelteKit** with **TypeScript**, designed to consume a backend API (likely Django-based, as indicated by the nginx proxy configuration).

### Core Technologies

| Category | Technology |
|----------|------------|
| **Framework** | SvelteKit 2.x |
| **Language** | TypeScript 5.x |
| **Styling** | Tailwind CSS 4.x |
| **UI Components** | Konstra UI, FontAwesome Icons, date-picker-svelte |
| **Build Tool** | Vite 7.x |
| **Testing** | Vitest 3.x (client + server), Playwright |
| **Linting/Formatting** | ESLint 9.x, Prettier 3.x |
| **Deployment** | Docker (multi-stage: Node builder + Nginx) |

### Architecture

- **SPA with Static Adapter**: Uses `@sveltejs/adapter-static` for static site generation with fallback to `index.html` for client-side routing.
- **Bearer Token Authentication**: Client-side auth with token stored in localStorage and Svelte store (`$lib/stores/auth.ts`).
- **API Proxy**: Development server proxies `/presenze` requests to `http://localhost:7999`. Production uses nginx to proxy to a `backend:7999` service.
- **State Management**: Svelte stores for auth, time entries, hour balance, and user data.

### Project Structure

```
src/
├── lib/
│   ├── api.ts              # API client with auth token handling
│   ├── components/         # Reusable UI components
│   ├── context/            # Svelte context providers
│   ├── hooks/              # Client/server hooks
│   ├── images/             # Static image assets
│   ├── services/           # Business logic services
│   │   ├── automobili.ts   # Vehicles service
│   │   ├── contratti.ts    # Contracts service
│   │   ├── timeEntries.ts  # Time entry service
│   │   ├── trasferte.ts    # Business trips service
│   │   └── users.ts        # Users service
│   └── stores/             # Svelte stores
│       ├── auth.ts         # Authentication state
│       ├── hourBalanceExtra.ts
│       ├── timeEntryReload.ts
│       └── timeEntryUser.ts
├── routes/
│   ├── auto/               # Vehicles module
│   ├── login/              # Login page
│   ├── preMenu/            # Pre-menu module
│   ├── presences/          # Presences/attendance module
│   ├── profilo/            # User profile
│   ├── trasferte/          # Business trips module
│   ├── +error.svelte       # Error page
│   ├── +layout.svelte      # Root layout
│   ├── +page.svelte        # Home page
│   └── +page.ts            # Home page logic (prerendered)
├── theme/                  # Theme configuration
├── app.css                 # Global styles (Tailwind)
├── app.d.ts                # TypeScript declarations
├── app.html                # HTML template
├── hooks.client.ts         # Client-side hooks
└── hooks.server.ts         # Server-side hooks (minimal, bearer-only)
```

## Building and Running

### Development

```bash
# Install dependencies
npm install

# Start dev server (with hot reload)
npm run dev

# Start dev server on specific port
npm run dev -- --port 3000
```

The dev server proxies `/presenze` API calls to `http://localhost:7999`. Ensure the backend is running.

### Production Build

```bash
# Build static assets
npm run build

# Preview production build locally
npm run preview
```

### Docker

```bash
# Build Docker image
docker build -t uipresenze .

# Run container
docker run -p 80:80 uipresenze
```

### Testing

```bash
# Run all tests
npm test

# Run unit tests in watch mode
npm run test:unit

# Run client-side tests (browser via Playwright)
npm run test:unit -- --project=client

# Run server-side tests (Node.js)
npm run test:unit -- --project=server
```

### Code Quality

```bash
# Type check
npm run check

# Type check (watch mode)
npm run check:watch

# Lint code
npm run lint

# Format code
npm run format
```

## Development Conventions

### Code Style

- **Tabs** for indentation (`useTabs: true`)
- **Single quotes** for strings (`singleQuote: true`)
- **No trailing commas** (`trailingComma: "none"`)
- **Max line width**: 100 characters
- **Svelte files**: Parsed with `prettier-plugin-svelte`
- **Tailwind classes**: Sorted automatically via `prettier-plugin-tailwindcss`

### TypeScript

- **Strict mode** enabled
- **Module resolution**: `bundler`
- **Path aliases**: SvelteKit defaults (`$lib`, `$app`, `$env`)
- **Svelte files**: Use `.svelte.ts` for TypeScript in Svelte contexts

### Testing Practices

- **Client tests**: Svelte component tests using Vitest browser mode (Playwright/Chromium)
- **Server tests**: Node.js environment for non-UI logic
- **Test files**: `*.test.ts` or `*.spec.ts` alongside source files
- **Assertions**: Required (`requireAssertions: true`)

### Git & Contribution

- `.gitignore` excludes build artifacts, `.svelte-kit/`, `node_modules/`
- `.npmrc` enforces engine strictness
- Pre-commit checks should include: `npm run lint && npm run check`

## Key Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Dependencies, scripts, project metadata |
| `svelte.config.js` | SvelteKit config, static adapter, mdsvex for markdown |
| `vite.config.ts` | Vite + Vitest config, Tailwind plugin, test projects |
| `tsconfig.json` | TypeScript compiler options |
| `tailwind.config.ts` | Tailwind CSS configuration |
| `eslint.config.js` | ESLint flat config with TypeScript + Svelte |
| `.prettierrc` | Prettier formatting rules |
| `Dockerfile` | Multi-stage build for production |
| `nginx.conf` | Nginx config for SPA routing + backend proxy |

## Environment Variables

- `PUBLIC_API_BASE`: Base URL for the backend API (used in `$lib/api.ts`)

## Authentication Flow

1. User submits credentials to `/login/` endpoint via `getToken()`
2. Token returned and stored in `auth` store + localStorage
3. Subsequent API requests include `Authorization: Bearer <token>` header
4. On logout, token cleared and redirect to `/login`

## Notes

- The project uses **mdsvex** for markdown/Svelte hybrid files (`.svx` extension)
- **Better-SQLite3** is listed as a dependency but may be for build-time or optional use
- The backend API is expected at `/presenze/` path with Django-style conventions
