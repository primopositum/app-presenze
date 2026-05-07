import base64
from datetime import date

import requests
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _jira_credentials():
    domain = getattr(settings, "JIRA_DOMAIN", "")
    email = getattr(settings, "JIRA_EMAIL", "")
    api_token = getattr(settings, "JIRA_API_TOKEN", "")

    if not domain or not email or not api_token:
        return None, Response(
            {"error": "Configurazione Jira mancante (JIRA_DOMAIN/JIRA_EMAIL/JIRA_API_TOKEN)"},
            status=500,
        )
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


class JiraProxyView(APIView):
    """
    Proxy verso le API Jira REST v3.
    Evita il blocco CORS chiamando Jira lato server.

    Impostazioni richieste in settings.py:
        JIRA_DOMAIN
        JIRA_EMAIL
        JIRA_API_TOKEN
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        jql = request.GET.get("jql", "")
        fields_raw = request.GET.get("fields", "summary,status,priority,assignee,created,updated")
        max_results = request.GET.get("maxResults", 20)

        creds, error_response = _jira_credentials()
        if error_response:
            return error_response
        domain, email, api_token = creds

        url = f"https://{domain}/rest/api/3/search/jql"
        fields = [field.strip() for field in fields_raw.split(",") if field.strip()]
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
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

        creds, error_response = _jira_credentials()
        if error_response:
            return error_response
        domain, email, api_token = creds
        headers = _jira_headers(email, api_token)

        search_url = f"https://{domain}/rest/api/3/search/jql"
        jql = f'worklogDate = "{target_date.isoformat()}"'
        start_at = 0
        issues = []

        try:
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

