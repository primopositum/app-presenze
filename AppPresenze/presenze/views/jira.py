import base64
import re
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import requests
from django.db.models import Sum
from django.utils import timezone as django_timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import JiraCredentials, JiraGlobals, TimeEntry


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


def _jira_current_account_id(domain: str, headers: dict):
    url = f"https://{domain}/rest/api/3/myself"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    payload = response.json() or {}
    return str(payload.get("accountId") or "").strip()


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


class JiraProxyView(APIView):
    """
    Proxy verso le API Jira REST v3.
    Evita il blocco CORS chiamando Jira lato server.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        jql = request.GET.get("jql", "")
        fields_raw = request.GET.get("fields", "summary,status,priority,assignee,created,updated")
        max_results = request.GET.get("maxResults", 20)
        start_at = request.GET.get("startAt", 0)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds

        url = f"https://{domain}/rest/api/3/search/jql"
        fields = [field.strip() for field in fields_raw.split(",") if field.strip()]
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
            "startAt": start_at,
        }
        headers = _jira_headers(email, api_token)

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return Response(response.json(), status=response.status_code)
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


class JiraWorklogsTodayView(APIView):
    """
    Restituisce le attivita Jira (worklog) registrate in una specifica data.

    Endpoint:
        GET /api/jira/worklogs/today/?date=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_raw = (request.GET.get("date") or "").strip()
        if not date_raw:
            return Response({"error": "Parametro date obbligatorio (YYYY-MM-DD)"}, status=400)

        try:
            target_date = date.fromisoformat(date_raw)
        except ValueError:
            return Response({"error": "Formato date non valido (usa YYYY-MM-DD)"}, status=400)

        creds, error_response = _jira_credentials_for_user(request.user)
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        search_url = f"https://{domain}/rest/api/3/search/jql"
        jql = f'worklogDate = "{target_date.isoformat()}"'
        start_at = 0
        issues = []

        try:
            current_account_id = _jira_current_account_id(domain, headers)
            if not current_account_id:
                return Response({"error": "Impossibile identificare l'account Jira corrente"}, status=502)

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
                issues.extend(batch)

                start_at += len(batch)
                total = int(payload.get("total", 0))
                if start_at >= total or not batch:
                    break

            activities = []
            target_prefix = target_date.isoformat()

            for issue in issues:
                key = issue.get("key")
                if not key:
                    continue
                fields = issue.get("fields", {}) or {}
                summary = fields.get("summary", "")
                project = fields.get("project", {}) or {}

                worklogs = _fetch_issue_worklogs(domain, key, headers)
                for worklog in worklogs:
                    started = str(worklog.get("started", ""))
                    if not started.startswith(target_prefix):
                        continue

                    author = worklog.get("author", {}) or {}
                    author_account_id = str(author.get("accountId") or "").strip()
                    if author_account_id != current_account_id:
                        continue
                    comment = _extract_comment_text(worklog.get("comment")).strip()
                    activities.append(
                        {
                            "issue_key": key,
                            "issue_summary": summary,
                            "project_key": project.get("key"),
                            "project_name": project.get("name"),
                            "worklog_id": worklog.get("id"),
                            "author": author.get("displayName"),
                            "started": started,
                            "time_spent": worklog.get("timeSpent"),
                            "time_spent_seconds": worklog.get("timeSpentSeconds"),
                            "comment": comment,
                        }
                    )

            activities.sort(key=lambda item: item.get("started") or "", reverse=True)
            return Response(
                {
                    "date": target_date.isoformat(),
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
            )

        return JiraGlobals.objects.create(id=1, domain="", filters=[])

    def get(self, request):
        jira_global = self._get_jira_globals_root()
        return Response({"filters": list(jira_global.filters or [])})

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

