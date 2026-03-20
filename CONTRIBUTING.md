# Contribuire a Gestionale Presenze Trasferte

Grazie per il tuo interesse nel contribuire a questo progetto! Questo documento fornisce linee guida per contribuire al progetto.

## 📋 Come Contribuire

### 1. Segnalare Bug

Prima di creare una issue, verifica che non esista già una issue simile.

Quando crei una issue per un bug, includi:
- Descrizione chiara del problema
- Passi per riprodurre il bug
- Comportamento atteso vs comportamento effettivo
- Screenshot (se applicabile)
- Ambiente (OS, browser, versioni)

### 2. Suggerire Funzionalità

Le proposte di nuove funzionalità sono benvenute! Crea una issue con:
- Descrizione della funzionalità
- Caso d'uso e benefici
- Eventuali esempi o mockup

### 3. Inviare Pull Request

#### Prerequisiti
- Python 3.12+ (per il backend)
- Node.js 20+ (per il frontend)
- Git

#### Processo

1. **Forka il repository**

2. **Crea un branch per la tua feature**:
   ```bash
   git checkout -b feature/nome-feature
   ```
   
   Convenzioni naming branch:
   - `feature/nome-feature` - nuove funzionalità
   - `fix/nome-bug` - correzione bug
   - `docs/descrizione` - documentazione
   - `refactor/descrizione` - refactoring codice

3. **Apporta le modifiche**
   
   Backend (Django):
   ```bash
   cd AppPresenze
   python manage.py test  # Esegui i test
   ```
   
   Frontend (Svelte):
   ```bash
   cd UIPresenze
   npm run test  # Esegui i test
   npm run lint  # Esegui linting
   ```

4. **Commit delle modifiche**:
   ```bash
   git add .
   git commit -m "feat: descrizione chiara del cambiamento"
   ```
   
   Convenzioni commit (Conventional Commits):
   - `feat:` - nuova funzionalità
   - `fix:` - correzione bug
   - `docs:` - documentazione
   - `style:` - formattazione
   - `refactor:` - refactoring
   - `test:` - test
   - `chore:` - manutenzione

5. **Push del branch**:
   ```bash
   git push origin feature/nome-feature
   ```

6. **Apri una Pull Request** su GitHub

## 📐 Linee Guida di Codice

### Backend (Django)

- Segui [PEP 8](https://pep8.org/) per lo stile Python
- Usa type hints quando possibile
- Scrivi test per nuove funzionalità
- Documenta le API con docstring

### Frontend (Svelte)

- Usa TypeScript per tutto il nuovo codice
- Segui le convenzioni di stile del progetto (vedi `.prettierrc`)
- Componenti Svelte: usa `<script lang="ts">`
- Scrivi test per componenti e servizi

### Commit Message

Formato: `<type>: <descrizione>`

Esempi:
```
feat: aggiunta validazione massiva presenze
fix: corretto calcolo ore festività
docs: aggiornato README con istruzioni Docker
refactor: ottimizzato caricamento trasferte
```

## 🧪 Testing

### Backend
```bash
cd AppPresenze
python manage.py test presenze
```

### Frontend
```bash
cd UIPresenze
npm run test
```

## 📝 Documentazione

- Aggiorna il README.md se cambi funzionalità
- Documenta nuove API in `docs/endpoints.md`
- Usa commenti solo quando necessario (il codice dovrebbe essere auto-esplicativo)

## 🔍 Code Review

Tutte le PR vengono revisionate. Assicurati che:
- I test passano
- Il codice segue lo stile del progetto
- Non ci sono console.log o debug code
- La documentazione è aggiornata

## 💬 Comunicazione

Per domande o discussioni:
- Apri una issue su GitHub
- Commenta sulle PR esistenti

Grazie per contribuire! 🎉
