import base64
import calendar
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import requests
from django.db.models import Sum
from django.http import StreamingHttpResponse
from django.utils import timezone as django_timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import JiraCredentials, JiraGlobals, TimeEntry, Utente


##########################################################################################################################################################################################################################################
#setup
##########################################################################################################################################################################################################################################
def _normalize_jira_domain(raw_domain: str) -> str:
    value = (raw_domain or "").strip()
    if not value:
        return ""
    # Accetta sia "azienda.atlassian.net" sia URL completi.
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path or "").strip()
    host = host.split("/")[0].strip().lower()
    return host


def _jira_credentials_for_user(user):
    jira_global = JiraGlobals.objects.order_by("id").first()
    if not jira_global or not (jira_global.domain or "").strip():
        return None, Response({"error": "Dominio Jira globale non configurato"}, status=400)

    try:
        creds = user.jira_credentials
    except JiraCredentials.DoesNotExist:
        return None, Response({"error": "Credenziali Jira non configurate"}, status=400)

    domain = _normalize_jira_domain(jira_global.domain)
    email = (creds.jira_email or "").strip()
    api_token = (creds.jira_token or "").strip()
    if not domain or not email or not api_token:
        return None, Response({"error": "Credenziali Jira incomplete"}, status=400)

    return (domain, email, api_token), None


def _jira_headers(email: str, api_token: str):
    credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }


def _extract_comment_text(node):
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_extract_comment_text(child) for child in node)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return "".join(_extract_comment_text(child) for child in node.get("content", []))
    return str(node)


def _jira_comment_payload(comment):
    if comment is None:
        return None
    if isinstance(comment, dict):
        return comment

    text = str(comment).strip()
    if not text:
        return None

    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            }
        ],
    }


def _fetch_issue_worklogs(domain: str, issue_key: str, headers: dict):
    url = f"https://{domain}/rest/api/3/issue/{issue_key}/worklog"
    start_at = 0
    all_worklogs = []

    while True:
        params = {
            "startAt": start_at,
            "maxResults": 100,
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json() or {}
        worklogs = payload.get("worklogs", [])
        all_worklogs.extend(worklogs)

        start_at += len(worklogs)
        total = int(payload.get("total", 0))
        if start_at >= total or not worklogs:
            break

    return all_worklogs

def _parse_started_value(request):
    def _format_started_iso(value: datetime) -> str:
        ms_part = value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23]
        return f"{ms_part}{value.strftime('%z')}"

    def _parse_tz_offset(raw_value: str):
        value = (raw_value or "").strip()
        if not value:
            return None, None
        if not value.startswith(("+", "-")):
            return None, "Formato tz non valido (usa +0200, +02:00, -0500)"

        normalized = value.replace(":", "")
        if len(normalized) != 5 or not normalized[1:].isdigit():
            return None, "Formato tz non valido (usa +0200, +02:00, -0500)"

        sign = 1 if normalized[0] == "+" else -1
        hours = int(normalized[1:3])
        minutes = int(normalized[3:5])
        if hours > 23 or minutes > 59:
            return None, "Formato tz non valido (usa +0200, +02:00, -0500)"

        delta = timedelta(hours=hours, minutes=minutes) * sign
        return dt_timezone(delta), None

    started_raw = (request.data.get("started") or request.query_params.get("started") or "").strip()
    if started_raw:
        normalized = started_raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None, "Formato started non valido. Usa ISO datetime (es. 2026-05-07T09:00:00.000+0200)"

        if parsed.tzinfo is None:
            parsed = django_timezone.make_aware(parsed, django_timezone.get_current_timezone())
        return _format_started_iso(parsed), None

    date_raw = (request.data.get("date") or request.query_params.get("date") or "").strip()
    time_raw = (request.data.get("time") or request.query_params.get("time") or "").strip()
    tz_raw = (request.data.get("tz") or request.query_params.get("tz") or "").strip()

    if not date_raw and not time_raw:
        return None, None

    if not date_raw:
        return None, "Parametro date obbligatorio quando passi time"

    try:
        target_date = date.fromisoformat(date_raw)
    except ValueError:
        return None, "Formato date non valido (usa YYYY-MM-DD)"

    if not time_raw:
        target_time = time(9, 0, 0)
    else:
        time_candidate = time_raw
        if len(time_candidate) == 5:
            time_candidate = f"{time_candidate}:00"
        try:
            target_time = time.fromisoformat(time_candidate)
        except ValueError:
            return None, "Formato time non valido (usa HH:MM o HH:MM:SS)"

    combined = datetime.combine(target_date, target_time)
    if tz_raw:
        tz_info, tz_error = _parse_tz_offset(tz_raw)
        if tz_error:
            return None, tz_error
        aware = combined.replace(tzinfo=tz_info)
        return _format_started_iso(aware), None

    aware = django_timezone.make_aware(combined, django_timezone.get_current_timezone())
    return _format_started_iso(aware), None


def _jira_issue_payload(worklog_payload):
    fields = (worklog_payload or {}).get("fields", {}) or {}
    timetracking = fields.get("timetracking", {}) or {}
    return {
        "key": worklog_payload.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status", {}) or {}).get("name"),
        "project": fields.get("project", {}),
        "timetracking": {
            "originalEstimate": timetracking.get("originalEstimate"),
            "remainingEstimate": timetracking.get("remainingEstimate"),
            "timeSpent": timetracking.get("timeSpent"),
            "originalEstimateSeconds": timetracking.get("originalEstimateSeconds"),
            "remainingEstimateSeconds": timetracking.get("remainingEstimateSeconds"),
            "timeSpentSeconds": timetracking.get("timeSpentSeconds"),
        },
    }


def _jira_error_response(exc):
    try:
        detail = exc.response.json()
    except Exception:
        detail = {"error": str(exc)}
    return Response(detail, status=exc.response.status_code)


def _parse_started_datetime(started_value: str):
    try:
        parsed = datetime.fromisoformat((started_value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = django_timezone.make_aware(parsed, django_timezone.get_current_timezone())
    return parsed


def _local_date_from_started(started_value: str):
    parsed = _parse_started_datetime(started_value)
    if not parsed:
        return None
    return parsed.astimezone(django_timezone.get_current_timezone()).date()


def _parse_scope_preset(scope_value_raw: str):
    scope_value = str(scope_value_raw or "").strip()
    if not scope_value:
        return None, ""
    match = re.match(r"^(project|filter|labels|space)\s*=\s*(.+)$", scope_value, flags=re.IGNORECASE)
    if not match:
        return None, scope_value
    scope_type = str(match.group(1) or "").strip().lower()
    if scope_type == "space":
        scope_type = "labels"
    scope_value = str(match.group(2) or "").strip()
    return scope_type, scope_value


def _extract_project_key_for_statuses(scope_type_raw: str, scope_value_raw: str):
    scope_type = str(scope_type_raw or "").strip().lower()
    scope_value = str(scope_value_raw or "").strip()

    preset_type, preset_value = _parse_scope_preset(scope_value)
    if preset_type:
        scope_type = preset_type
        scope_value = preset_value

    if scope_type != "project":
        return ""

    project_key = str(scope_value or "").strip()
    if not project_key:
        return ""
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", project_key):
        return ""
    return project_key


def _status_category_rank(category_key: str):
    key = str(category_key or "").strip().casefold()
    if key in {"new", "todo", "to do", "to-do"}:
        return 0
    if key in {"indeterminate", "in progress", "in-progress"}:
        return 1
    if key in {"done", "complete", "completed"}:
        return 2
    return 3


def _normalize_status_rows(status_rows):
    normalized = []
    seen_names = set()
    for row in status_rows or []:
        if not isinstance(row, dict):
            continue

        name = str(row.get("name") or "").strip()
        if not name:
            continue
        name_key = name.casefold()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)

        status_category = row.get("statusCategory", {}) or {}
        category_key = str(status_category.get("key") or "").strip()
        category_name = str(status_category.get("name") or "").strip()
        normalized.append(
            {
                "id": str(row.get("id") or ""),
                "name": name,
                "category_key": category_key,
                "category_name": category_name,
            }
        )

    normalized.sort(key=lambda item: (_status_category_rank(item.get("category_key")), (item.get("name") or "").casefold()))
    return normalized


def _extract_statuses_from_project_payload(payload):
    rows = []
    if not isinstance(payload, list):
        return rows
    for issue_type in payload:
        statuses = (issue_type or {}).get("statuses", []) or []
        if isinstance(statuses, list):
            rows.extend(statuses)
    return rows


def _sum_worked_seconds_for_user_day(user, target_date: date) -> int:
    if not target_date:
        return 0
    rows = (
        TimeEntry.objects.filter(utente=user, data=target_date, type__in=[1, 3])
        .values("type")
        .annotate(total=Sum("ore_tot"))
    )

    worked_hours = 0.0
    for row in rows:
        entry_type = int(row.get("type") or 0)
        hours = float(row.get("total") or 0)
        if entry_type in (1, 3):
            worked_hours += hours


    return max(0, int(round(worked_hours * 3600)))


_TIME_SPENT_TOKEN_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([wdhms])", re.IGNORECASE)
_TIME_SPENT_SECONDS_BY_UNIT = {
    "s": 1,
    "m": 60,
    "h": 3600,
    # Jira defaults: 1 giorno = 8h, 1 settimana = 5 giorni.
    "d": 8 * 3600,
    "w": 5 * 8 * 3600,
}

_PRIORITY_NAME_ORDER = {
    "blocker": 0,
    "highest": 0,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "normal": 3,
    "low": 4,
    "minor": 4,
    "lowest": 5,
    "trivial": 5,
}
_WORKLOG_ENRICH_MAX_WORKERS = 8


def _parse_time_spent_to_seconds(time_spent: str):
    text = str(time_spent or "").strip().lower()
    if not text:
        return None

    matches = list(_TIME_SPENT_TOKEN_RE.finditer(text))
    if not matches:
        return None

    normalized = "".join(f"{m.group(1)}{m.group(2).lower()}" for m in matches)
    compact = re.sub(r"\s+", "", text)
    if normalized != compact:
        return None

    total_seconds = 0.0
    for match in matches:
        raw_value = match.group(1).replace(",", ".")
        unit = match.group(2).lower()
        value = float(raw_value)
        if value <= 0:
            return None
        total_seconds += value * _TIME_SPENT_SECONDS_BY_UNIT[unit]

    seconds_int = int(round(total_seconds))
    return seconds_int if seconds_int > 0 else None


def _jira_priority_sort_key(issue_payload):
    fields = (issue_payload or {}).get("fields", {}) or {}
    priority = fields.get("priority", {}) or {}
    priority_name = str(priority.get("name") or "").strip().lower()
    name_rank = _PRIORITY_NAME_ORDER.get(priority_name, 99)

    priority_id_raw = str(priority.get("id") or "").strip()
    priority_id_rank = int(priority_id_raw) if priority_id_raw.isdigit() else 999999

    issue_key = str((issue_payload or {}).get("key") or "").strip()
    return (name_rank, priority_id_rank, issue_key)


def _sort_issues_by_priority(search_payload):
    if not isinstance(search_payload, dict):
        return search_payload

    issues = search_payload.get("issues")
    if not isinstance(issues, list):
        return search_payload

    search_payload["issues"] = sorted(issues, key=_jira_priority_sort_key)
    return search_payload


def _split_jql_order_by(jql: str):
    value = str(jql or "").strip()
    if not value:
        return "", ""

    match = re.search(r"\s+ORDER\s+BY\s+", value, flags=re.IGNORECASE)
    if not match:
        return value, ""

    return value[:match.start()].strip(), value[match.start():].strip()


def _exclude_completata_for_scope_jql(jql: str):
    base_jql, order_by = _split_jql_order_by(jql)
    if not base_jql:
        return jql

    # Applica la regola solo alle query scope usate dai preset filter[].
    if not re.match(r"^\s*(filter|project|labels)\s*=", base_jql, flags=re.IGNORECASE):
        return jql

    # Evita doppie condizioni equivalenti.
    if re.search(r'status\s*!=\s*"Completata"', base_jql, flags=re.IGNORECASE):
        return jql
    if re.search(r'status\s+NOT\s+IN\s*\([^)]*"Completata"[^)]*\)', base_jql, flags=re.IGNORECASE):
        return jql

    filtered = f'{base_jql} AND status != "Completata"'
    return f"{filtered} {order_by}".strip() if order_by else filtered


def _is_scope_filter_jql(jql: str):
    base_jql, _order_by = _split_jql_order_by(jql)
    if not base_jql:
        return False
    return bool(re.match(r"^\s*(filter|project|labels)\s*=", base_jql, flags=re.IGNORECASE))


def _drop_completata_issues_case_insensitive(search_payload):
    if not isinstance(search_payload, dict):
        return
    issues = search_payload.get("issues")
    if not isinstance(issues, list):
        return

    filtered = []
    for issue in issues:
        fields = (issue or {}).get("fields", {}) or {}
        status = (fields.get("status", {}) or {}).get("name", "")
        status_name = str(status or "").strip().casefold()
        if status_name == "completata":
            continue
        filtered.append(issue)

    search_payload["issues"] = filtered


def _jql_looks_completed_history(jql: str):
    text = str(jql or "").lower()
    if not text:
        return False

    return (
        ("statuscategory" in text and "done" in text)
        or '"completed"' in text
        or '"completata"' in text
    )


def _worklog_seconds_by_author(domain: str, issue_key: str, headers: dict):
    totals = {}
    worklogs = _fetch_issue_worklogs(domain, issue_key, headers)
    for worklog in worklogs:
        seconds = int(worklog.get("timeSpentSeconds") or 0)
        if seconds <= 0:
            continue
        author = (worklog.get("author") or {}) if isinstance(worklog, dict) else {}
        author_name = str(author.get("displayName") or "").strip() or "Unassigned"
        totals[author_name] = totals.get(author_name, 0) + seconds
    return totals


def _enrich_completed_issues_with_worklog_authors(search_payload, domain: str, headers: dict):
    if not isinstance(search_payload, dict):
        return
    logs = search_payload.setdefault("worklog_enrich_logs", [])

    def _push_log(level: str, message: str, issue_key: str = ""):
        # Evita payload troppo grandi su errori massivi.
        if not isinstance(logs, list):
            return
        if len(logs) >= 100:
            if len(logs) == 100:
                logs.append(
                    {
                        "level": "warning",
                        "message": "Limite log raggiunto (100): ulteriori dettagli omessi.",
                    }
                )
            return
        row = {"level": level, "message": message}
        if issue_key:
            row["issue_key"] = issue_key
        logs.append(row)

    issues = search_payload.get("issues")
    if not isinstance(issues, list):
        _push_log("error", "Arricchimento Jira non eseguito: campo 'issues' mancante o non valido.")
        search_payload["worklog_enrich_error"] = True
        return

    issue_rows = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        issue_key = str(issue.get("key") or "").strip()
        fields = issue.get("fields")
        if not issue_key or not isinstance(fields, dict):
            continue
        issue_rows.append((issue_key, fields))

    if not issue_rows:
        search_payload["worklog_enrich_meta"] = {
            "enabled": True,
            "candidate_issues": 0,
            "enriched_issues": 0,
            "failed_issues": 0,
        }
        return

    max_workers = min(_WORKLOG_ENRICH_MAX_WORKERS, len(issue_rows))
    if max_workers <= 1:
        # Fallback: mantiene il comportamento anche su ambienti con un solo worker.
        max_workers = 1
    failed_issues = 0
    enriched_issues = 0

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_worklog_seconds_by_author, domain, issue_key, headers): (issue_key, fields)
                for issue_key, fields in issue_rows
            }

            for future in as_completed(future_map):
                issue_key, fields = future_map[future]
                try:
                    totals = future.result()
                except requests.exceptions.RequestException as exc:
                    # Non bloccare l'intera risposta, ma esporre il motivo al frontend.
                    failed_issues += 1
                    _push_log(
                        "error",
                        f"Errore richiesta Jira durante lettura worklog: {exc}",
                        issue_key=issue_key,
                    )
                    continue
                except Exception as exc:
                    failed_issues += 1
                    _push_log(
                        "error",
                        f"Errore inatteso durante arricchimento worklog: {exc}",
                        issue_key=issue_key,
                    )
                    continue

                if not totals:
                    continue

                sorted_authors = sorted(
                    totals.items(),
                    key=lambda item: (-item[1], item[0].lower()),
                )
                workers = [
                    {"displayName": name, "timeSpentSeconds": seconds}
                    for name, seconds in sorted_authors
                ]

                # Manteniamo il contratto FE invariato: assignee.displayName esiste sempre.
                top_name, top_seconds = sorted_authors[0]
                fields["assignee"] = {"displayName": top_name}

                # Metadati aggiuntivi utili per debug/estensioni future.
                fields["worklog_authors"] = workers
                fields["worklog_primary_author"] = {
                    "displayName": top_name,
                    "timeSpentSeconds": top_seconds,
                }
                enriched_issues += 1
    except Exception as exc:
        failed_issues = max(failed_issues, 1)
        _push_log("error", f"Errore generale arricchimento Jira worklog: {exc}")

    search_payload["worklog_enrich_meta"] = {
        "enabled": True,
        "candidate_issues": len(issue_rows),
        "enriched_issues": enriched_issues,
        "failed_issues": failed_issues,
    }
    if failed_issues > 0:
        search_payload["worklog_enrich_error"] = True


def _jira_current_account_id(domain: str, headers: dict):
    url = f"https://{domain}/rest/api/3/myself"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    payload = response.json() or {}
    return str(payload.get("accountId") or "").strip()


def _year_worklog_jql(target_year: int) -> str:
    # Buffer di un anno: include issue chiuse a cavallo ma con worklog nell'anno target.
    return (
        f'(statusCategory = Done OR status in ("Completed","Completata"))'
        f' AND resolutiondate >= "{date(target_year - 1, 1, 1).isoformat()}"'
        f' AND resolutiondate <= "{date(target_year + 1, 1, 1).isoformat()}"'
        f' ORDER BY updated DESC'
    )


def _completed_history_jql(target_year: int | None = None) -> str:
    year_filter = ""
    if target_year is not None:
        year_filter = (
            f' AND resolutiondate >= "{date(target_year, 1, 1).isoformat()}"'
            f' AND resolutiondate <= "{date(target_year, 12, 31).isoformat()}"'
        )
    return f'(statusCategory = Done OR status in ("Completed","Completata")){year_filter} ORDER BY updated DESC'


def _completed_history_fields() -> list[str]:
    return [
        "summary",
        "status",
        "assignee",
        "issuetype",
        "parent",
        "project",
        "timetracking",
        "timespent",
        "aggregatetimespent",
        "timeestimate",
        "aggregatetimeestimate",
        "timeoriginalestimate",
        "aggregatetimeoriginalestimate",
        "created",
        "updated",
        "resolutiondate",
    ]


def _fetch_jira_search_all(domain: str, headers: dict, jql: str, fields: list[str], start_at: int = 0, page_size: int = 100):
    search_url = f"https://{domain}/rest/api/3/search/jql"
    collected_issues = []
    total = 0
    payload = {}
    next_page_token = None

    while True:
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": page_size,
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        else:
            params["startAt"] = max(0, int(start_at or 0))

        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        page_payload = response.json() or {}
        if not payload:
            payload = page_payload

        batch = page_payload.get("issues", [])
        if isinstance(batch, list):
            collected_issues.extend(batch)

        total = int(page_payload.get("total", len(collected_issues)) or len(collected_issues))

        # Controlla se ci sono altre pagine tramite token
        next_page_token = page_payload.get("nextPageToken")
        is_last = page_payload.get("isLast", True)

        if is_last or not next_page_token or not batch:
            break

    payload["issues"] = collected_issues
    payload["startAt"] = start_at
    payload["maxResults"] = len(collected_issues)
    payload["total"] = len(collected_issues)  # il total di Jira non è affidabile con token pagination
    return payload


def _completed_history_payload(domain: str, headers: dict, target_year: int | None = None):
    jql = _completed_history_jql(target_year)
    payload = _fetch_jira_search_all(domain, headers, jql, _completed_history_fields())
    _enrich_completed_issues_with_worklog_authors(payload, domain, headers)
    _sort_issues_by_priority(payload)
    payload["view"] = "completed"
    payload["year"] = target_year if target_year is not None else "all"
    payload["jql"] = jql
    return payload


def _search_issues_for_year_worklog(domain: str, headers: dict, target_year: int):
    search_url = f"https://{domain}/rest/api/3/search/jql"
    jql = _year_worklog_jql(target_year)
    start_at = 0
    issues = []

    while True:
        params = {
            "jql": jql,
            "fields": ["summary", "project", "status", "assignee"],
            "startAt": start_at,
            "maxResults": 100,
        }
        search_response = requests.get(search_url, params=params, headers=headers, timeout=10)
        search_response.raise_for_status()
        payload = search_response.json() or {}
        batch = payload.get("issues", [])
        if isinstance(batch, list):
            issues.extend(batch)

        start_at += len(batch) if isinstance(batch, list) else 0
        total = int(payload.get("total", 0))
        if start_at >= total or not batch:
            break

    return issues, jql


def _build_year_worklog_payload(
    domain: str,
    headers: dict,
    target_year: int,
    issues: list,
    progress_cb=None,
):
    projects_map = {}
    total_worklogs = 0
    total_seconds = 0
    total_issues = 0
    total = len(issues)

    for idx, issue in enumerate(issues):
        issue_key = str((issue or {}).get("key") or "").strip()
        if not issue_key:
            if progress_cb:
                progress_cb(idx + 1, total)
            continue

        fields = (issue.get("fields") or {}) if isinstance(issue, dict) else {}
        project = fields.get("project", {}) or {}
        project_key = str(project.get("key") or "N/D").strip() or "N/D"
        project_name = str(project.get("name") or "Progetto non disponibile").strip() or "Progetto non disponibile"

        worklogs = _fetch_issue_worklogs(domain, issue_key, headers)

        # La issue viene inclusa solo se ha almeno un worklog nell'anno target.
        # Ma una volta inclusa, portiamo TUTTI i suoi worklog.
        has_worklog_in_target_year = any(
            _local_date_from_started(str(wl.get("started") or "")) and
            _local_date_from_started(str(wl.get("started") or "")).year == target_year
            for wl in worklogs
        )
        if not has_worklog_in_target_year:
            if progress_cb:
                progress_cb(idx + 1, total)
            continue

        issue_worklogs = []
        issue_total_seconds = 0

        for worklog in worklogs:
            started_value = str(worklog.get("started") or "")
            local_day = _local_date_from_started(started_value)
            if not local_day:
                continue  # worklog senza data valida: scartato

            seconds = int(worklog.get("timeSpentSeconds") or 0)
            author = worklog.get("author", {}) or {}
            comment = _extract_comment_text(worklog.get("comment")).strip()
            issue_worklogs.append(
                {
                    "worklog_id": worklog.get("id"),
                    "author": author.get("displayName"),
                    "author_account_id": author.get("accountId"),
                    "started": started_value,
                    "date": local_day.isoformat(),
                    "time_spent": worklog.get("timeSpent"),
                    "time_spent_seconds": seconds,
                    "comment": comment,
                }
            )
            if seconds > 0:
                issue_total_seconds += seconds

        if issue_worklogs:
            issue_worklogs.sort(key=lambda item: item.get("started") or "", reverse=True)
            total_worklogs += len(issue_worklogs)
            total_seconds += issue_total_seconds
            total_issues += 1

            if project_key not in projects_map:
                projects_map[project_key] = {
                    "project_key": project_key,
                    "project_name": project_name,
                    "issues": [],
                    "issues_count": 0,
                    "worklogs_count": 0,
                    "total_seconds": 0,
                }

            projects_map[project_key]["issues"].append(
                {
                    "issue_key": issue_key,
                    "issue_summary": fields.get("summary"),
                    "status": (fields.get("status", {}) or {}).get("name"),
                    "assignee": author.get("displayName"),
                    "worklogs_count": len(issue_worklogs),
                    "total_seconds": issue_total_seconds,
                    "worklogs": issue_worklogs,
                }
            )
            projects_map[project_key]["issues_count"] += 1
            projects_map[project_key]["worklogs_count"] += len(issue_worklogs)
            projects_map[project_key]["total_seconds"] += issue_total_seconds

        if progress_cb:
            progress_cb(idx + 1, total)

    projects = list(projects_map.values())
    for project_row in projects:
        project_row["issues"].sort(key=lambda item: (item.get("issue_key") or ""))
    projects.sort(key=lambda item: (item.get("project_key") or ""))

    return {
        "projects_count": len(projects),
        "issues_count": total_issues,
        "worklogs_count": total_worklogs,
        "total_seconds": total_seconds,
        "projects": projects,
    }
##########################################################################################################################################################################################################################################
#functions
##########################################################################################################################################################################################################################################

def _sum_jira_logged_seconds_for_user_day(domain: str, headers: dict, account_id: str, target_date: date) -> int:
    if not account_id:
        return 0

    search_url = f"https://{domain}/rest/api/3/search/jql"
    jql = f'worklogAuthor = currentUser() AND worklogDate = "{target_date.isoformat()}"'
    start_at = 0
    issues = []

    while True:
        params = {
            "jql": jql,
            "fields": ["summary"],
            "startAt": start_at,
            "maxResults": 100,
        }
        search_response = requests.get(search_url, params=params, headers=headers, timeout=10)
        search_response.raise_for_status()
        payload = search_response.json() or {}
        batch = payload.get("issues", [])
        issues.extend(batch)

        start_at += len(batch)
        total = int(payload.get("total", 0))
        if start_at >= total or not batch:
            break

    total_logged_seconds = 0
    for issue in issues:
        issue_key = str(issue.get("key") or "").strip()
        if not issue_key:
            continue
        worklogs = _fetch_issue_worklogs(domain, issue_key, headers)
        for worklog in worklogs:
            author_account_id = str((worklog.get("author") or {}).get("accountId") or "").strip()
            if author_account_id != account_id:
                continue
            worklog_date = _local_date_from_started(str(worklog.get("started") or ""))
            if worklog_date != target_date:
                continue
            seconds = int(worklog.get("timeSpentSeconds") or 0)
            if seconds > 0:
                total_logged_seconds += seconds

    return total_logged_seconds


def _jira_timesheet_activity(issue, worklog):
    fields = issue.get("fields", {}) or {}
    project = fields.get("project", {}) or {}
    author = worklog.get("author", {}) or {}
    return {
        "issue_key": issue.get("key"),
        "issue_summary": fields.get("summary", ""),
        "project_key": project.get("key"),
        "project_name": project.get("name"),
        "worklog_id": worklog.get("id"),
        "author": author.get("displayName"),
        "started": str(worklog.get("started", "")),
        "time_spent": worklog.get("timeSpent"),
        "time_spent_seconds": worklog.get("timeSpentSeconds"),
        "comment": _extract_comment_text(worklog.get("comment")).strip(),
    }


def _fetch_jira_timesheet_issues(domain: str, headers: dict, account_id: str, start_date: date, end_date: date):
    search_url = f"https://{domain}/rest/api/3/search/jql"
    jql = (
        f'worklogAuthor = "{account_id}"'
        f' AND worklogDate >= "{start_date.isoformat()}"'
        f' AND worklogDate <= "{end_date.isoformat()}"'
    )
    start_at = 0
    issues = []

    while True:
        params = {
            "jql": jql,
            "fields": ["summary", "project"],
            "startAt": start_at,
            "maxResults": 100,
        }
        search_response = requests.get(search_url, params=params, headers=headers, timeout=10)
        search_response.raise_for_status()
        payload = search_response.json() or {}
        batch = payload.get("issues", [])
        if isinstance(batch, list):
            issues.extend(batch)

        start_at += len(batch) if isinstance(batch, list) else 0
        total = int(payload.get("total", 0))
        if start_at >= total or not batch:
            break

    return issues


def _jira_timesheet_payload_for_user(target_user, start_date: date, end_date: date):
    creds, error_response = _jira_credentials_for_user(target_user)
    if error_response:
        return None, error_response
    domain, email, api_token = creds
    headers = _jira_headers(email, api_token)

    current_account_id = _jira_current_account_id(domain, headers)
    if not current_account_id:
        return None, Response({"error": "Impossibile identificare l'account Jira corrente"}, status=502)

    issues = _fetch_jira_timesheet_issues(domain, headers, current_account_id, start_date, end_date)
    days = {}
    activities_count = 0

    for issue in issues:
        key = issue.get("key")
        if not key:
            continue

        worklogs = _fetch_issue_worklogs(domain, key, headers)
        for worklog in worklogs:
            author = worklog.get("author", {}) or {}
            author_account_id = str(author.get("accountId") or "").strip()
            if author_account_id != current_account_id:
                continue

            started = str(worklog.get("started", ""))
            local_day = _local_date_from_started(started)
            if not local_day or local_day < start_date or local_day > end_date:
                continue

            day_key = local_day.isoformat()
            days.setdefault(day_key, {"date": day_key, "count": 0, "activities": []})
            days[day_key]["activities"].append(_jira_timesheet_activity(issue, worklog))
            days[day_key]["count"] += 1
            activities_count += 1

    for day_payload in days.values():
        day_payload["activities"].sort(key=lambda item: item.get("started") or "", reverse=True)

    return {
        "utente_email": target_user.email,
        "jira_email": email,
        "account_id": current_account_id,
        "count": activities_count,
        "days": dict(sorted(days.items())),
    }, None


def _jira_user_monthly_worklog_payload(user, target_year: int, account_id: str = "", target_month: int | None = None):
    if target_month is not None and (target_month < 1 or target_month > 12):
        raise ValueError("Formato month non valido (usa 1-12)")

    creds, error_response = _jira_credentials_for_user(user)
    if error_response:
        error_payload = getattr(error_response, "data", {}) or {}
        error_msg = str(error_payload.get("error") or "Credenziali Jira non configurate")
        raise ValueError(error_msg)

    domain, email, api_token = creds
    headers = _jira_headers(email, api_token)

    resolved_account_id = str(account_id or "").strip()
    if not resolved_account_id:
        resolved_account_id = _jira_current_account_id(domain, headers)

    if not resolved_account_id:
        raise ValueError("account_id non trovato")

    if target_month:
        month_start = date(target_year, target_month, 1)
        month_end = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
        jql_start = month_start.isoformat()
        jql_end = month_end.isoformat()
    else:
        jql_start = date(target_year, 1, 1).isoformat()
        jql_end = date(target_year, 12, 31).isoformat()

    jql = (
        f'worklogAuthor = "{resolved_account_id}"'
        f' AND worklogDate >= "{jql_start}"'
        f' AND worklogDate <= "{jql_end}"'
    )

    search_url = f"https://{domain}/rest/api/3/search/jql"
    start_at = 0
    issues = []

    while True:
        params = {
            "jql": jql,
            "fields": ["summary", "project"],
            "startAt": start_at,
            "maxResults": 100,
        }
        resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json() or {}
        batch = payload.get("issues", [])
        if isinstance(batch, list):
            issues.extend(batch)

        start_at += len(batch) if isinstance(batch, list) else 0
        if start_at >= int(payload.get("total", 0)) or not batch:
            break

    # Riallinea l'autore principale da worklog anche nel flusso usato dal controllo ore PDF.
    _enrich_completed_issues_with_worklog_authors({"issues": issues}, domain, headers)

    monthly_seconds: dict[int, int] = {m: 0 for m in range(1, 13)}
    monthly_by_project: dict[int, dict[str, int]] = {m: {} for m in range(1, 13)}

    for issue in issues:
        issue_key = str(issue.get("key") or "").strip()
        if not issue_key:
            continue

        fields = issue.get("fields", {}) or {}
        project = fields.get("project", {}) or {}
        project_key = str(project.get("key") or "N/D").strip() or "N/D"

        worklogs = _fetch_issue_worklogs(domain, issue_key, headers)
        for worklog in worklogs:
            author = worklog.get("author", {}) or {}
            if author.get("accountId") != resolved_account_id:
                continue

            started_value = str(worklog.get("started") or "")
            local_day = _local_date_from_started(started_value)
            if not local_day or local_day.year != target_year:
                continue
            if target_month and local_day.month != target_month:
                continue

            seconds = int(worklog.get("timeSpentSeconds") or 0)
            if seconds <= 0:
                continue

            month = local_day.month
            monthly_seconds[month] += seconds
            monthly_by_project[month][project_key] = (
                monthly_by_project[month].get(project_key, 0) + seconds
            )

    months_to_emit = [target_month] if target_month else list(range(1, 13))
    months_out = []
    for m in months_to_emit:
        secs = monthly_seconds[m]
        months_out.append(
            {
                "month": m,
                "month_name": date(target_year, m, 1).strftime("%B"),
                "total_seconds": secs,
                "total_hours": round(secs / 3600, 2),
                "by_project": [
                    {"project_key": pk, "seconds": s, "hours": round(s / 3600, 2)}
                    for pk, s in sorted(monthly_by_project[m].items())
                ],
            }
        )

    if target_month:
        total_seconds = monthly_seconds[target_month]
    else:
        total_seconds = sum(monthly_seconds.values())

    return {
        "year": target_year,
        "month": target_month,
        "account_id": resolved_account_id,
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "months": months_out,
    }


class JiraProxyView(APIView):
    """
    Proxy verso le API Jira REST v3.
    Evita il blocco CORS chiamando Jira lato server.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        jql = _exclude_completata_for_scope_jql(request.GET.get("jql", ""))
        fields_raw = request.GET.get("fields", "summary,status,priority,assignee,created,updated")
        max_results_raw = request.GET.get("maxResults")
        start_at_raw = request.GET.get("startAt", 0)
        try:
            start_at = max(0, int(str(start_at_raw).strip() or 0))
        except (TypeError, ValueError):
            start_at = 0

        fetch_all_pages = str(max_results_raw or "").strip().lower() in {"0", "all", "*"}
        if max_results_raw in (None, ""):
            max_results = 300 if _jql_looks_completed_history(jql) else 20
        elif fetch_all_pages:
            max_results = 100
        else:
            max_results = max_results_raw

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds

        url = f"https://{domain}/rest/api/3/search/jql"
        fields = [field.strip() for field in fields_raw.split(",") if field.strip()]
        priority_requested = any(field.lower() == "priority" for field in fields)
        if not priority_requested:
            fields.append("priority")
        params = {
            "jql": jql,
            "fields": fields,
        }
        headers = _jira_headers(email, api_token)

        try:
            if fetch_all_pages:
                collected_issues = []
                page_start = start_at
                total = 0
                payload = {}
                status_code = 200

                while True:
                    page_params = {
                        **params,
                        "maxResults": max_results,
                        "startAt": page_start,
                    }
                    response = requests.get(url, params=page_params, headers=headers, timeout=10)
                    response.raise_for_status()
                    status_code = response.status_code
                    page_payload = response.json() or {}
                    if not payload:
                        payload = page_payload

                    batch = page_payload.get("issues", [])
                    if isinstance(batch, list):
                        collected_issues.extend(batch)

                    total = int(page_payload.get("total", len(collected_issues)) or len(collected_issues))
                    page_start += len(batch) if isinstance(batch, list) else 0
                    if page_start >= total or not batch:
                        break

                payload["issues"] = collected_issues
                payload["startAt"] = start_at
                payload["maxResults"] = len(collected_issues)
                payload["total"] = total
            else:
                request_params = {
                    **params,
                    "maxResults": max_results,
                    "startAt": start_at,
                }
                response = requests.get(url, params=request_params, headers=headers, timeout=10)
                response.raise_for_status()
                status_code = response.status_code
                payload = response.json()

            if _is_scope_filter_jql(jql):
                _drop_completata_issues_case_insensitive(payload)

            if _jql_looks_completed_history(jql):
                _enrich_completed_issues_with_worklog_authors(payload, domain, headers)

            _sort_issues_by_priority(payload)

            if not priority_requested and isinstance(payload, dict):
                for issue in payload.get("issues", []):
                    issue_fields = (issue or {}).get("fields")
                    if isinstance(issue_fields, dict):
                        issue_fields.pop("priority", None)

            return Response(payload, status=status_code)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = {"error": str(e)}
            return Response(detail, status=e.response.status_code)
        except requests.exceptions.RequestException as e: 
            return Response({"error": str(e)}, status=502)


class JiraStatusesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope_type = (request.GET.get("scopeType") or "").strip()
        scope_value = (request.GET.get("scopeValue") or "").strip()

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        project_key = _extract_project_key_for_statuses(scope_type, scope_value)
        source = "global"
        url = f"https://{domain}/rest/api/3/status"
        if project_key:
            source = "project"
            url = f"https://{domain}/rest/api/3/project/{project_key}/statuses"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json() or []

            if source == "project":
                status_rows = _extract_statuses_from_project_payload(payload)
            else:
                status_rows = payload if isinstance(payload, list) else []

            statuses = _normalize_status_rows(status_rows)
            return Response(
                {
                    "source": source,
                    "project_key": project_key or None,
                    "count": len(statuses),
                    "statuses": statuses,
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)


class JiraWorklogsTodayView(APIView):
    """
    Restituisce le attivita Jira (worklog) registrate in una specifica data.

    Endpoint:
        GET  /api/jira/timesheet/?date=YYYY-MM-DD
        POST /api/jira/timesheet/ { "date": "YYYY-MM-DD", "email": "utente@example.com" }

    I superuser possono passare nel body/query una mail target con una delle chiavi:
    email, mail, utente_email, jira_email.
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _request_value(request, *keys):
        for key in keys:
            value = request.data.get(key)
            if value not in (None, ""):
                return str(value).strip()
        for key in keys:
            value = request.query_params.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""

    def _target_user_from_request(self, request):
        target_email = self._request_value(request, "email", "mail", "utente_email", "jira_email")
        if not target_email:
            return request.user, None

        if not request.user.is_superuser:
            if target_email.casefold() == str(request.user.email or "").strip().casefold():
                return request.user, None
            return None, Response({"error": "Solo un superuser puo richiedere i worklog di un altro utente"}, status=403)

        target_user = Utente.objects.filter(email__iexact=target_email).first()
        if target_user:
            return target_user, None

        jira_creds = (
            JiraCredentials.objects.select_related("utente")
            .filter(jira_email__iexact=target_email)
            .first()
        )
        if jira_creds:
            return jira_creds.utente, None

        return None, Response({"error": f"Utente/Jira credentials non trovati per la mail {target_email}"}, status=404)

    def _handle(self, request):
        date_raw = self._request_value(request, "date")
        if not date_raw:
            return Response({"error": "Parametro date obbligatorio (YYYY-MM-DD)"}, status=400)

        try:
            target_date = date.fromisoformat(date_raw)
        except ValueError:
            return Response({"error": "Formato date non valido (usa YYYY-MM-DD)"}, status=400)

        target_user, target_error = self._target_user_from_request(request)
        if target_error:
            return target_error

        try:
            payload, error_response = _jira_timesheet_payload_for_user(target_user, target_date, target_date)
            if error_response:
                return error_response
            day_payload = (payload.get("days") or {}).get(target_date.isoformat(), {})
            activities = day_payload.get("activities", [])
            return Response(
                {
                    "date": target_date.isoformat(),
                    "utente_email": target_user.email,
                    "jira_email": payload.get("jira_email"),
                    "count": len(activities),
                    "activities": activities,
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = {"error": str(e)}
            return Response(detail, status=e.response.status_code)
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=502)

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)


class JiraWorklogsMonthView(APIView):
    """
    Restituisce i worklog Jira di un mese, raggruppati per giorno e utente.

    Endpoint:
        GET  /api/jira/timesheet/month/?year=YYYY&month=MM
        GET  /api/jira/timesheet/month/?date=YYYY-MM-DD
        POST /api/jira/timesheet/month/ { "year": YYYY, "month": MM, "email": "utente@example.com" }
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _request_value(request, *keys):
        return JiraWorklogsTodayView._request_value(request, *keys)

    def _target_user_from_request(self, request):
        return JiraWorklogsTodayView()._target_user_from_request(request)

    @staticmethod
    def _parse_month(request):
        date_raw = JiraWorklogsTodayView._request_value(request, "date")
        if date_raw:
            try:
                parsed_date = date.fromisoformat(date_raw)
            except ValueError:
                return None, None, Response({"error": "Formato date non valido (usa YYYY-MM-DD)"}, status=400)
            return parsed_date.year, parsed_date.month, None

        year_raw = JiraWorklogsTodayView._request_value(request, "year")
        month_raw = JiraWorklogsTodayView._request_value(request, "month")
        if not year_raw or not month_raw:
            return None, None, Response({"error": "Parametri obbligatori: year e month oppure date"}, status=400)

        try:
            target_year = int(year_raw)
            target_month = int(month_raw)
            if target_year < 1900 or target_year > 3000 or target_month < 1 or target_month > 12:
                raise ValueError
        except ValueError:
            return None, None, Response({"error": "Formato year/month non valido"}, status=400)

        return target_year, target_month, None

    def _handle(self, request):
        target_year, target_month, parse_error = self._parse_month(request)
        if parse_error:
            return parse_error

        target_user, target_error = self._target_user_from_request(request)
        if target_error:
            return target_error

        month_start = date(target_year, target_month, 1)
        month_end = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])

        try:
            user_payload, error_response = _jira_timesheet_payload_for_user(target_user, month_start, month_end)
            if error_response:
                return error_response

            users = [user_payload]
            days = {}
            for payload in users:
                utente_email = payload.get("utente_email")
                jira_email = payload.get("jira_email")
                for day_key, day_payload in (payload.get("days") or {}).items():
                    day_row = days.setdefault(day_key, {"date": day_key, "count": 0, "users": {}})
                    activities = day_payload.get("activities") or []
                    day_row["users"][utente_email] = {
                        "utente_email": utente_email,
                        "jira_email": jira_email,
                        "count": len(activities),
                        "activities": activities,
                    }
                    day_row["count"] += len(activities)

            return Response(
                {
                    "year": target_year,
                    "month": target_month,
                    "start_date": month_start.isoformat(),
                    "end_date": month_end.isoformat(),
                    "count": sum(user.get("count", 0) for user in users),
                    "users_count": len(users),
                    "users": users,
                    "days": dict(sorted(days.items())),
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)


class JiraUserMonthlyWorklogView(APIView):
    """
    Restituisce la somma degli worklog mensili registrati da un utente su Jira.

    Endpoint:
        GET /api/jira/worklogs/user-monthly/?year=YYYY&account_id=AAA&month=MM
        GET /api/jira/worklogs/user-monthly/?year=YYYY  <- usa l'utente corrente
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        year_raw = (request.GET.get("year") or "").strip()
        if not year_raw:
            return Response({"error": "Parametro year obbligatorio (YYYY)"}, status=400)

        try:
            target_year = int(year_raw)
            if target_year < 1900 or target_year > 3000:
                raise ValueError
        except ValueError:
            return Response({"error": "Formato year non valido (usa YYYY)"}, status=400)

        month_raw = (request.GET.get("month") or "").strip()
        target_month = None
        if month_raw:
            try:
                target_month = int(month_raw)
                if target_month < 1 or target_month > 12:
                    raise ValueError
            except ValueError:
                return Response({"error": "Formato month non valido (usa 1-12)"}, status=400)

        account_id = (request.GET.get("account_id") or "").strip() or ""

        try:
            payload = _jira_user_monthly_worklog_payload(
                user=request.user,
                target_year=target_year,
                account_id=account_id,
                target_month=target_month,
            )
            return Response(payload)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)


class JiraWorklogView(APIView):
    """
    Restituisce dati storico Jira filtrati.

    Endpoint:
        GET /api/jira/worklogs/year/?view=tree&year=YYYY
        GET /api/jira/worklogs/year/?view=completed&year=YYYY|all
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        view_mode = (request.GET.get("view") or "tree").strip().lower()
        if view_mode not in {"tree", "completed"}:
            return Response({"error": "Parametro view non valido (usa tree o completed)"}, status=400)

        year_raw = (request.GET.get("year") or "").strip()
        if view_mode == "completed" and year_raw.lower() in {"", "all", "tutti"}:
            year_raw = ""
        if view_mode == "tree" and not year_raw:
            return Response({"error": "Parametro year obbligatorio (YYYY)"}, status=400)

        target_year = None
        try:
            if year_raw and year_raw.lower() != "all":
                target_year = int(year_raw)
                if target_year < 1900 or target_year > 3000:
                    raise ValueError
        except ValueError:
            return Response({"error": "Formato year non valido (usa YYYY)"}, status=400)

        if view_mode == "tree" and target_year is None:
            return Response({"error": "Parametro year obbligatorio (YYYY)"}, status=400)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        try:
            if view_mode == "completed":
                return Response(_completed_history_payload(domain, headers, target_year))

            issues, jql = _search_issues_for_year_worklog(domain, headers, target_year)
            payload = _build_year_worklog_payload(domain, headers, target_year, issues)

            return Response(
                {
                    "view": "tree",
                    "year": target_year,
                    "jql": jql,
                    **payload,
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as e:
            return _jira_error_response(e)
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=502)


class JiraWorklogStreamView(APIView):
    """
    Stream SSE dei worklog annuali Jira con progresso incrementale.

    Endpoint:
        GET /api/jira/worklogs/year/stream/?year=YYYY
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        year_raw = (request.GET.get("year") or "").strip()
        if not year_raw:
            return Response({"error": "Parametro year obbligatorio (YYYY)"}, status=400)

        try:
            target_year = int(year_raw)
            if target_year < 1900 or target_year > 3000:
                raise ValueError
        except ValueError:
            return Response({"error": "Formato year non valido (usa YYYY)"}, status=400)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        try:
            issues, jql = _search_issues_for_year_worklog(domain, headers, target_year)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as e:
            return _jira_error_response(e)
        except requests.exceptions.RequestException as e:
            return Response({"error": str(e)}, status=502)

        def event_stream():
            try:
                total = len(issues)
                yield f"data: {json.dumps({'type': 'start', 'total': total}, ensure_ascii=False)}\n\n"

                projects_map = {}
                total_worklogs = 0
                total_seconds = 0
                total_issues = 0

                for idx, issue in enumerate(issues):
                    issue_key = str((issue or {}).get("key") or "").strip()
                    if issue_key:
                        fields = (issue.get("fields") or {}) if isinstance(issue, dict) else {}
                        project = fields.get("project", {}) or {}
                        project_key = str(project.get("key") or "N/D").strip() or "N/D"
                        project_name = str(project.get("name") or "Progetto non disponibile").strip() or "Progetto non disponibile"

                        issue_worklogs = []
                        issue_total_seconds = 0
                        worklogs = _fetch_issue_worklogs(domain, issue_key, headers)
                        for worklog in worklogs:
                            started_value = str(worklog.get("started") or "")
                            local_day = _local_date_from_started(started_value)
                            if not local_day or local_day.year != target_year:
                                continue

                            seconds = int(worklog.get("timeSpentSeconds") or 0)
                            author = worklog.get("author", {}) or {}
                            comment = _extract_comment_text(worklog.get("comment")).strip()
                            issue_worklogs.append(
                                {
                                    "worklog_id": worklog.get("id"),
                                    "author": author.get("displayName"),
                                    "author_account_id": author.get("accountId"),
                                    "started": started_value,
                                    "date": local_day.isoformat(),
                                    "time_spent": worklog.get("timeSpent"),
                                    "time_spent_seconds": seconds,
                                    "comment": comment,
                                }
                            )
                            if seconds > 0:
                                issue_total_seconds += seconds

                        if issue_worklogs:
                            issue_worklogs.sort(key=lambda item: item.get("started") or "", reverse=True)
                            total_worklogs += len(issue_worklogs)
                            total_seconds += issue_total_seconds
                            total_issues += 1

                            if project_key not in projects_map:
                                projects_map[project_key] = {
                                    "project_key": project_key,
                                    "project_name": project_name,
                                    "issues": [],
                                    "issues_count": 0,
                                    "worklogs_count": 0,
                                    "total_seconds": 0,
                                }

                            projects_map[project_key]["issues"].append(
                                {
                                    "issue_key": issue_key,
                                    "issue_summary": fields.get("summary"),
                                    "status": (fields.get("status", {}) or {}).get("name"),
                                    "assignee": author.get("displayName"),
                                    "worklogs_count": len(issue_worklogs),
                                    "total_seconds": issue_total_seconds,
                                    "worklogs": issue_worklogs,
                                }
                            )
                            projects_map[project_key]["issues_count"] += 1
                            projects_map[project_key]["worklogs_count"] += len(issue_worklogs)
                            projects_map[project_key]["total_seconds"] += issue_total_seconds

                    yield f"data: {json.dumps({'type': 'progress', 'loaded': idx + 1, 'total': total}, ensure_ascii=False)}\n\n"

                projects = list(projects_map.values())
                for project_row in projects:
                    project_row["issues"].sort(key=lambda item: (item.get("issue_key") or ""))
                projects.sort(key=lambda item: (item.get("project_key") or ""))

                done_payload = {
                    "type": "done",
                    "year": target_year,
                    "jql": jql,
                    "projects_count": len(projects),
                    "issues_count": total_issues,
                    "worklogs_count": total_worklogs,
                    "total_seconds": total_seconds,
                    "projects": projects,
                }
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            except requests.exceptions.RequestException as exc:
                err_payload = {"type": "error", "error": str(exc)}
                yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class JiraIssueTimeView(APIView):
    """
    Gestione timetracking e worklog di una issue Jira.

    Endpoint:
        GET /api/jira/time/<issue_key>/?[started=...|date=YYYY-MM-DD&time=HH:MM]
        PUT /api/jira/time/<issue_key>/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, issue_key: str):
        issue_key_clean = (issue_key or "").strip()
        if not issue_key_clean:
            return Response({"error": "Issue key obbligatoria"}, status=400)

        started_value, parse_error = _parse_started_value(request)
        if parse_error:
            return Response({"error": parse_error}, status=400)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        issue_url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}"
        worklog_url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}/worklog"
        issue_params = {
            "fields": "summary,status,project,timetracking",
        }
        worklog_params = {
            "startAt": 0,
            "maxResults": 100,
        }
        if started_value:
            try:
                started_dt = datetime.fromisoformat(started_value.replace("Z", "+00:00"))
            except ValueError:
                return Response({"error": "Formato data/ora non valido"}, status=400)
            if started_dt.tzinfo is None:
                started_dt = django_timezone.make_aware(started_dt, django_timezone.get_current_timezone())
            worklog_params["startedAfter"] = int(started_dt.timestamp() * 1000)

        try:
            issue_response = requests.get(issue_url, params=issue_params, headers=headers, timeout=10)
            issue_response.raise_for_status()
            all_worklogs = []
            start_at = 0
            while True:
                page_params = {**worklog_params, "startAt": start_at}
                worklog_response = requests.get(worklog_url, params=page_params, headers=headers, timeout=10)
                worklog_response.raise_for_status()
                page_payload = worklog_response.json() or {}
                page_worklogs = page_payload.get("worklogs", [])
                all_worklogs.extend(page_worklogs)
                start_at += len(page_worklogs)
                page_total = int(page_payload.get("total", 0))
                if start_at >= page_total or not page_worklogs:
                    break

            issue_payload = issue_response.json() or {}
            return Response(
                {
                    "issue": _jira_issue_payload(issue_payload),
                    "worklogs": all_worklogs,
                    "worklogs_count": len(all_worklogs),
                    "filters": {
                        "started": started_value,
                    },
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

    def put(self, request, issue_key: str):
        issue_key_clean = (issue_key or "").strip()
        if not issue_key_clean:
            return Response({"error": "Issue key obbligatoria"}, status=400)

        original_estimate = (request.data.get("originalEstimate") or "").strip()
        remaining_estimate = (request.data.get("remainingEstimate") or "").strip()

        if not original_estimate and not remaining_estimate:
            return Response(
                {"error": "Passa almeno uno tra originalEstimate e remainingEstimate"},
                status=400,
            )

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)
        headers["Content-Type"] = "application/json"

        payload = {"fields": {"timetracking": {}}}
        if original_estimate:
            payload["fields"]["timetracking"]["originalEstimate"] = original_estimate
        if remaining_estimate:
            payload["fields"]["timetracking"]["remainingEstimate"] = remaining_estimate

        url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}"
        try:
            response = requests.put(url, headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 204):
                verify_response = requests.get(
                    url,
                    params={"fields": "summary,status,project,timetracking"},
                    headers=headers,
                    timeout=10,
                )
                verify_response.raise_for_status()
                return Response(
                    {
                        "ok": True,
                        "issue": _jira_issue_payload(verify_response.json() or {}),
                    }
                )

            response.raise_for_status()
            return Response(response.json(), status=response.status_code)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)


class JiraIssueWorklogView(APIView):
    """
    Gestione creazione, modifica e cancellazione worklog Jira.

    Endpoint:
        POST   /api/jira/time/<issue_key>/log/
        PUT    /api/jira/time/<issue_key>/log/<worklog_id>/
        DELETE /api/jira/time/<issue_key>/log/<worklog_id>/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, issue_key: str):
        issue_key_clean = (issue_key or "").strip()
        if not issue_key_clean:
            return Response({"error": "Issue key obbligatoria"}, status=400)

        time_spent = (request.data.get("timeSpent") or "").strip()
        if not time_spent:
            return Response({"error": "Parametro obbligatorio: timeSpent"}, status=400)
        new_worklog_seconds = _parse_time_spent_to_seconds(time_spent)
        if not new_worklog_seconds:
            return Response(
                {"error": "Formato timeSpent non valido. Esempi: 2h, 1h 30m, 45m."},
                status=400,
            )

        started_value, parse_error = _parse_started_value(request)
        if parse_error:
            return Response({"error": parse_error}, status=400)
        if not started_value:
            return Response(
                {"error": "Parametro obbligatorio: started oppure coppia date + time"},
                status=400,
            )

        comment = _jira_comment_payload(request.data.get("comment"))

        payload = {
            "timeSpent": time_spent,
            "started": started_value,
        }
        if comment is not None:
            payload["comment"] = comment

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)
        headers["Content-Type"] = "application/json"

        target_date = _local_date_from_started(started_value)
        if not target_date:
            return Response({"error": "Formato started non valido"}, status=400)

        worked_seconds = _sum_worked_seconds_for_user_day(request.user, target_date)
        if worked_seconds <= 0:
            return Response(
                {
                    "error": (
                        f"Impossibile registrare worklog: nessuna ora lavorata disponibile per il giorno "
                        f"{target_date.isoformat()} (type 1 + 3)."
                    )
                },
                status=409,
            )

        try:
            account_id = _jira_current_account_id(domain, headers)
            logged_seconds = _sum_jira_logged_seconds_for_user_day(domain, headers, account_id, target_date)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

        if logged_seconds >= worked_seconds:
            worked_hours = round(worked_seconds / 3600, 2)
            logged_hours = round(logged_seconds / 3600, 2)
            return Response(
                {
                    "error": (
                        f"Copertura Jira gia al limite per {target_date.isoformat()}: "
                        f"{logged_hours}h loggate su {worked_hours}h lavorate."
                    )
                },
                status=409,
            )

        projected_seconds = logged_seconds + new_worklog_seconds
        if projected_seconds > worked_seconds:
            worked_hours = round(worked_seconds / 3600, 2)
            logged_hours = round(logged_seconds / 3600, 2)
            new_hours = round(new_worklog_seconds / 3600, 2)
            projected_hours = round(projected_seconds / 3600, 2)
            return Response(
                {
                    "error": (
                        f"Inserimento non consentito per {target_date.isoformat()}: "
                        f"{logged_hours}h gia loggate + {new_hours}h richieste = {projected_hours}h, "
                        f"oltre le {worked_hours}h lavorate."
                    )
                },
                status=409,
            )

        url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}/worklog"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return Response(response.json(), status=response.status_code)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

    def put(self, request, issue_key: str, worklog_id: str):
        issue_key_clean = (issue_key or "").strip()
        worklog_id_clean = (worklog_id or "").strip()
        if not issue_key_clean:
            return Response({"error": "Issue key obbligatoria"}, status=400)
        if not worklog_id_clean:
            return Response({"error": "Worklog id obbligatorio"}, status=400)

        time_spent = (request.data.get("timeSpent") or "").strip()
        if not time_spent:
            return Response({"error": "Parametro obbligatorio: timeSpent"}, status=400)
        new_worklog_seconds = _parse_time_spent_to_seconds(time_spent)
        if not new_worklog_seconds:
            return Response(
                {"error": "Formato timeSpent non valido. Esempi: 2h, 1h 30m, 45m."},
                status=400,
            )

        started_value, parse_error = _parse_started_value(request)
        if parse_error:
            return Response({"error": parse_error}, status=400)
        if not started_value:
            return Response(
                {"error": "Parametro obbligatorio: started oppure coppia date + time"},
                status=400,
            )

        comment = _jira_comment_payload(request.data.get("comment"))

        payload = {
            "timeSpent": time_spent,
            "started": started_value,
        }
        if comment is not None:
            payload["comment"] = comment

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)
        headers["Content-Type"] = "application/json"

        target_date = _local_date_from_started(started_value)
        if not target_date:
            return Response({"error": "Formato started non valido"}, status=400)

        worked_seconds = _sum_worked_seconds_for_user_day(request.user, target_date)
        if worked_seconds <= 0:
            return Response(
                {
                    "error": (
                        f"Impossibile aggiornare worklog: nessuna ora lavorata disponibile per il giorno "
                        f"{target_date.isoformat()} (type 1 + 3)."
                    )
                },
                status=409,
            )

        detail_url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}/worklog/{worklog_id_clean}"
        try:
            detail_response = requests.get(detail_url, headers=headers, timeout=10)
            detail_response.raise_for_status()
            detail_payload = detail_response.json() or {}

            account_id = _jira_current_account_id(domain, headers)
            logged_seconds = _sum_jira_logged_seconds_for_user_day(domain, headers, account_id, target_date)

            current_author_id = str((detail_payload.get("author") or {}).get("accountId") or "").strip()
            current_started = str(detail_payload.get("started") or "")
            current_date = _local_date_from_started(current_started)
            current_seconds = int(detail_payload.get("timeSpentSeconds") or 0)
            if (
                current_author_id
                and current_author_id == account_id
                and current_date == target_date
                and current_seconds > 0
            ):
                logged_seconds = max(0, logged_seconds - current_seconds)

            projected_seconds = logged_seconds + new_worklog_seconds
            if projected_seconds > worked_seconds:
                worked_hours = round(worked_seconds / 3600, 2)
                logged_hours = round(logged_seconds / 3600, 2)
                new_hours = round(new_worklog_seconds / 3600, 2)
                projected_hours = round(projected_seconds / 3600, 2)
                return Response(
                    {
                        "error": (
                            f"Aggiornamento non consentito per {target_date.isoformat()}: "
                            f"{logged_hours}h gia loggate + {new_hours}h richieste = {projected_hours}h, "
                            f"oltre le {worked_hours}h lavorate."
                        )
                    },
                    status=409,
                )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

        url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}/worklog/{worklog_id_clean}"
        try:
            response = requests.put(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return Response(response.json(), status=response.status_code)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)

    def delete(self, request, issue_key: str, worklog_id: str):
        issue_key_clean = (issue_key or "").strip()
        worklog_id_clean = (worklog_id or "").strip()
        if not issue_key_clean:
            return Response({"error": "Issue key obbligatoria"}, status=400)
        if not worklog_id_clean:
            return Response({"error": "Worklog id obbligatorio"}, status=400)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        url = f"https://{domain}/rest/api/3/issue/{issue_key_clean}/worklog/{worklog_id_clean}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code in (200, 202, 204):
                return Response({"ok": True}, status=200)
            response.raise_for_status()
            return Response(status=response.status_code)
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)


class JiraUpdateState(APIView):
    """
    Aggiorna lo stato Jira di una work/issue tramite transizione.

    Endpoint:
        PUT /api/jira/work/<work_key>/state/
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, work_key: str):
        work_key_clean = (work_key or "").strip()
        if not work_key_clean:
            return Response({"error": "Work key obbligatoria"}, status=400)

        transition_id = str(request.data.get("transition_id") or "").strip()
        target_status = str(request.data.get("status") or request.data.get("to_status") or "").strip()
        if not transition_id and not target_status:
            return Response(
                {"error": "Parametro obbligatorio: transition_id oppure status"},
                status=400,
            )

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)
        headers["Content-Type"] = "application/json"

        transitions_url = f"https://{domain}/rest/api/3/issue/{work_key_clean}/transitions"

        try:
            transitions_res = requests.get(transitions_url, headers=headers, timeout=10)
            transitions_res.raise_for_status()
            transitions_payload = transitions_res.json() or {}
            transitions = transitions_payload.get("transitions", []) or []
            if not transitions:
                return Response({"error": "Nessuna transizione disponibile per la work indicata"}, status=409)

            selected_transition = None
            if transition_id:
                for tr in transitions:
                    tr_id = str((tr or {}).get("id") or "").strip()
                    if tr_id == transition_id:
                        selected_transition = tr
                        break
                if not selected_transition:
                    return Response(
                        {"error": f"transition_id non valida per la work {work_key_clean}"},
                        status=400,
                    )
            else:
                target_cf = target_status.casefold()
                for tr in transitions:
                    tr_name = str((tr or {}).get("name") or "").strip()
                    to_name = str(((tr or {}).get("to") or {}).get("name") or "").strip()
                    if tr_name.casefold() == target_cf or to_name.casefold() == target_cf:
                        selected_transition = tr
                        break
                if not selected_transition:
                    available = [
                        {
                            "id": str((tr or {}).get("id") or ""),
                            "name": str((tr or {}).get("name") or ""),
                            "to_status": str(((tr or {}).get("to") or {}).get("name") or ""),
                        }
                        for tr in transitions
                    ]
                    return Response(
                        {
                            "error": f"Stato '{target_status}' non trovato tra le transizioni disponibili",
                            "available_transitions": available,
                        },
                        status=400,
                    )

            selected_id = str((selected_transition or {}).get("id") or "").strip()
            selected_to = str(((selected_transition or {}).get("to") or {}).get("name") or "").strip()
            post_payload = {"transition": {"id": selected_id}}

            update_res = requests.post(transitions_url, headers=headers, json=post_payload, timeout=10)
            update_res.raise_for_status()

            return Response(
                {
                    "ok": True,
                    "work_key": work_key_clean,
                    "transition_id": selected_id,
                    "to_status": selected_to,
                }
            )
        except requests.exceptions.Timeout:
            return Response({"error": "Timeout connessione a Jira"}, status=504)
        except requests.exceptions.HTTPError as exc:
            return _jira_error_response(exc)
        except requests.exceptions.RequestException as exc:
            return Response({"error": str(exc)}, status=502)


class JiraCredentialsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            creds = request.user.jira_credentials
        except JiraCredentials.DoesNotExist:
            return Response({"configured": False, "jira_email": ""})

        return Response(
            {
                "configured": True,
                "jira_email": creds.jira_email,
            }
        )

    def post(self, request):
        jira_email = (request.data.get("jira_email") or "").strip()
        jira_token = (request.data.get("jira_token") or "").strip()

        if not jira_email or not jira_token:
            return Response(
                {"error": "Campi obbligatori: jira_email, jira_token"},
                status=400,
            )

        creds, _created = JiraCredentials.objects.get_or_create(utente=request.user)
        creds.jira_email = jira_email
        creds.jira_token = jira_token
        creds.save()

        return Response({"ok": True, "configured": True})


class JiraCredentialsTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Difesa extra: per ogni utente deve esistere al massimo 1 record.
        existing_count = JiraCredentials.objects.filter(utente=request.user).count()
        if existing_count > 1:
            return Response(
                {"error": "Configurazione Jira non valida: trovate credenziali duplicate per utente"},
                status=409,
            )

        try:
            creds = request.user.jira_credentials
        except JiraCredentials.DoesNotExist:
            return Response(
                {
                    "configured": False,
                    "token_present": False,
                    "token_valid": None,
                }
            )

        token = (creds.jira_token or "").strip()
        if not token:
            return Response(
                {
                    "configured": False,
                    "token_present": False,
                    "token_valid": None,
                }
            )

        jira_global = JiraGlobals.objects.order_by("id").first()
        raw_domain = (jira_global.domain or "") if jira_global else ""
        domain = _normalize_jira_domain(raw_domain) if jira_global else ""
        email = (creds.jira_email or "").strip()

        if not domain:
            return Response(
                {
                    "configured": True,
                    "token_present": True,
                    "token_valid": False,
                    "error": "Dominio Jira globale non configurato",
                    "jira_global_id": getattr(jira_global, "id", None),
                    "domain_used": domain,
                    "domain_raw": raw_domain,
                }
            )

        if not email:
            return Response(
                {
                    "configured": True,
                    "token_present": True,
                    "token_valid": False,
                    "error": "Email Jira non configurata",
                    "jira_global_id": getattr(jira_global, "id", None),
                    "domain_used": domain,
                }
            )

        url = f"https://{domain}/rest/api/3/myself"
        headers = _jira_headers(email, token)
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return Response(
                    {
                        "configured": True,
                        "token_present": True,
                        "token_valid": True,
                        "masked_token": "*****",
                        "jira_global_id": getattr(jira_global, "id", None),
                        "domain_used": domain,
                        "jira_email": email,
                    }
                )

            if response.status_code in (401, 403):
                return Response(
                    {
                        "configured": True,
                        "token_present": True,
                        "token_valid": False,
                        "error": f"Token Jira non valido o senza permessi (email usata: {email}, domain: {domain})",
                        "jira_global_id": getattr(jira_global, "id", None),
                        "domain_used": domain,
                        "jira_email": email,
                    }
                )

            return Response(
                {
                    "configured": True,
                    "token_present": True,
                    "token_valid": False,
                    "error": f"Verifica token Jira fallita (HTTP {response.status_code})",
                    "jira_global_id": getattr(jira_global, "id", None),
                    "domain_used": domain,
                    "jira_email": email,
                }
            )
        except requests.exceptions.Timeout:
            return Response(
                {
                    "configured": True,
                    "token_present": True,
                    "token_valid": False,
                    "error": "Timeout connessione a Jira",
                    "jira_global_id": getattr(jira_global, "id", None),
                    "domain_used": domain,
                    "jira_email": email,
                }
            )
        except requests.exceptions.RequestException as exc:
            return Response(
                {
                    "configured": True,
                    "token_present": True,
                    "token_valid": False,
                    "error": str(exc),
                    "jira_global_id": getattr(jira_global, "id", None),
                    "domain_used": domain,
                    "jira_email": email,
                }
            )

    def post(self, request):
        token = (request.data.get("token") or request.data.get("jira_token") or "").strip()
        jira_email = (request.data.get("jira_email") or "").strip()
        if not token:
            return Response({"error": "Parametro obbligatorio: token (oppure jira_token)"}, status=400)

        # Difesa extra: per ogni utente deve esistere al massimo 1 record.
        existing_count = JiraCredentials.objects.filter(utente=request.user).count()
        if existing_count > 1:
            return Response(
                {"error": "Configurazione Jira non valida: trovate credenziali duplicate per utente"},
                status=409,
            )

        creds, _created = JiraCredentials.objects.get_or_create(utente=request.user)
        if jira_email:
            creds.jira_email = jira_email
        elif not (creds.jira_email or "").strip():
            # Fallback solo al primo inserimento quando non esiste ancora una mail Jira.
            creds.jira_email = request.user.email
        creds.jira_token = token
        creds.save()

        return Response({"ok": True, "configured": True, "jira_email": creds.jira_email})

    def put(self, request):
        return self.post(request)


class UpdateJiraFiltersView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1"}:
                return True, None
            if normalized in {"false", "0"}:
                return False, None
        return None, "Parametro booleano non valido: append"

    @staticmethod
    def _normalize_filter_scope(raw_value: str):
        value = (raw_value or "").strip()
        if not value:
            return ""
        if "=" not in value:
            return value

        left, right = value.split("=", 1)
        scope_type = left.strip().lower()
        scope_value = right.strip()
        if scope_type in {"project", "filter"}:
            return f"{scope_type} = {scope_value}"
        return value

    @staticmethod
    def _get_jira_globals_root():
        jira_global = JiraGlobals.objects.filter(id=1).first()
        if jira_global:
            return jira_global

        seed = JiraGlobals.objects.order_by("id").first()
        if seed:
            return JiraGlobals.objects.create(
                id=1,
                domain=(seed.domain or "").strip(),
                filters=list(seed.filters or []),
                JiraControl=bool(getattr(seed, "JiraControl", True)),
            )

        return JiraGlobals.objects.create(id=1, domain="", filters=[], JiraControl=True)

    def get(self, request):
        jira_global = self._get_jira_globals_root()
        return Response(
            {
                "filters": list(jira_global.filters or []),
                "JiraControl": bool(getattr(jira_global, "JiraControl", True)),
            }
        )

    def post(self, request):
        filter_value = self._normalize_filter_scope(request.data.get("filter") or "")
        append_raw = request.data.get("append")
        if append_raw in (None, ""):
            append_value = True
            error = None
        else:
            append_value, error = self._parse_bool(append_raw)

        if not filter_value:
            return Response({"error": "Parametro obbligatorio: filter"}, status=400)
        if error:
            return Response({"error": error}, status=400)

        jira_global = self._get_jira_globals_root()

        filters = list(jira_global.filters or [])
        if append_value:
            if filter_value not in filters:
                filters.append(filter_value)
        else:
            filters = [
                item
                for item in filters
                if self._normalize_filter_scope(item) != filter_value
            ]

        jira_global.filters = filters
        jira_global.save(update_fields=["filters"])

        return Response({"ok": True, "filters": jira_global.filters})

    def put(self, request):
        return self.post(request)

