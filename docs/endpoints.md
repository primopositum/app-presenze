# Elenco Endpoint API

Prefisso comune: `/presenze/api/`  
Autenticazione: Bearer token su quasi tutte le rotte.

## Profilo e account

| Metodo | Path | Cosa fa |
|---|---|---|
| GET,PUT | `/profile/` | Legge/aggiorna profilo utente autenticato |
| POST | `/change-password/` | Cambia password utente autenticato |
| GET | `/users/` | Lista utenti |

## Auth

| Metodo | Path | Cosa fa |
|---|---|---|
| POST | `/getToken/` | Rilascia token da email/username + password |
| POST | `/login/` | Login e rilascio token |
| POST | `/logout/` | Logout e invalidazione token |

## Time Entries

| Metodo | Path | Cosa fa |
|---|---|---|
| POST | `/time-entries/` | Crea TimeEntry |
| POST | `/time-entries/range-override/` | Crea/aggiorna TimeEntry su intervallo date |
| GET | `/time-entries/from-month/` | Ritorna TimeEntry per mese corrente + precedente con filtri |
| GET,PUT,DELETE | `/time-entries/<te_id>/` | Dettaglio, modifica, cancellazione TimeEntry |
| PATCH | `/time-entries/<te_id>/validation/` | Aggiorna validation_level della singola entry |
| PATCH | `/time-entries/bulk-validate-month/` | Validazione massiva del mese |

## PDF

| Metodo | Path | Cosa fa |
|---|---|---|
| GET | `/pdf/` | PDF presenze mese scorso |
| GET | `/trasferte/pdf/` | PDF trasferte mese scorso |

## Trasferte

| Metodo | Path | Cosa fa |
|---|---|---|
| GET | `/trasferte/` | Lista trasferte (con filtri query param) |
| POST | `/trasferte/create/` | Crea trasferta |
| PUT | `/trasferte/<t_id>/` | Aggiorna trasferta |
| PATCH | `/trasferte/<tr_id>/validation/` | Valida trasferta (tipicamente admin) |
| DELETE | `/trasferte/<t_id>/delete/` | Elimina trasferta |
| GET | `/trasferte/<u_id>/<data>/dossier/` | Genera ZIP contenente scontrini, pdf della auto, e pdf generato delle trasferte del mese scelto |

## Spese

| Metodo | Path | Cosa fa |
|---|---|---|
| GET | `/trasferte/<t_id>/spese/` | Lista spese di una trasferta |
| POST | `/trasferte/<t_id>/spese/create/` | Crea spesa su trasferta |
| PUT,DELETE | `/spese/<s_id>/` | Modifica o elimina spesa |

## Scontrini

| Metodo | Path | Cosa fa |
|---|---|---|
| GET,POST | `/trasferte/<t_id>/scontrini/` | Lista o upload scontrini |
| GET | `/trasferte/<t_id>/scontrini/<filename>/` | Scarica/visualizza singolo scontrino |
| DELETE | `/trasferte/<t_id>/scontrini/<filename>/delete/` | Elimina scontrino |

## Automobili

| Metodo | Path | Cosa fa |
|---|---|---|
| GET,POST | `/automobili/` | Lista o crea automobile |
| GET,PUT,PATCH | `/automobili/<pk>/` | Dettaglio e update automobile |
| DELETE | `/automobili/<pk>/delete/` | Elimina/archivia automobile |
| PATCH | `/automobili/<pk>/patch/` | Patch mirata (`coefficiente`, `is_active`) |
| POST | `/automobili/<auto_id>/PDFauto/` | Upload PDF auto del mese |
| GET | `/automobili/PDFauto/mese-corrente/` | Lista PDF auto del mese corrente |

## Note rapide su permessi

- Utente normale: in genere puo operare solo sulle proprie risorse.
- Superuser/admin: puo operare anche su risorse altrui e su livelli di validazione admin.

