# How To Use

## Base URL

- Locale: `http://localhost:7999`
- Prefisso API: `/presenze/api/`
- Esempio completo: `http://localhost:7999/presenze/api/login/`

## 1) Login e token

Richiesta:

```bash
curl -X POST "http://localhost:7999/presenze/api/login/" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"utente@example.com\",\"password\":\"password\"}"
```

Risposta: token Bearer.

## 2) Usa il token nelle chiamate

```bash
curl "http://localhost:7999/presenze/api/profile/" ^
  -H "Authorization: Bearer <TOKEN>"
```

## 3) Flusso tipico TimeEntry

1. Crea entry: `POST /time-entries/`
2. Leggi/modifica/cancella entry: `GET/PUT/DELETE /time-entries/<te_id>/`
3. Valida singola entry: `PATCH /time-entries/<te_id>/validation/`
4. Valida mese in blocco: `PATCH /time-entries/bulk-validate-month/`

## 4) Flusso tipico Trasferta

1. Crea trasferta: `POST /trasferte/create/`
2. Carica scontrino: `POST /trasferte/<t_id>/scontrini/` (multipart, campo `file`)
3. Aggiungi spesa: `POST /trasferte/<t_id>/spese/create/`
4. Genera dossier mese: `GET /trasferte/<u_id>/<data>/dossier/`

## Errori comuni

- `401 Unauthorized`: token mancante o non valido.
- `403 Forbidden`: permessi insufficienti.
- `400 Bad Request`: payload o parametri non validi.
- `404 Not Found`: risorsa non trovata.

## Campi e formati importanti

- `data`: sempre `YYYY-MM-DD`
- `validation_level`:
  - `0`: auto
  - `1`: validato utente
  - `2`: validato admin

