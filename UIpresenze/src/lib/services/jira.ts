import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type JiraSearchParams = {
  jql: string;
  fields?: string;
  maxResults?: number;
};

export type JiraTimesheetActivity = {
  issue_key: string;
  issue_summary: string;
  project_key?: string;
  project_name?: string;
  worklog_id?: string;
  author?: string;
  started?: string;
  time_spent?: string;
  time_spent_seconds?: number;
  comment?: string;
};

export type JiraTimesheetResponse = {
  date: string;
  count: number;
  activities: JiraTimesheetActivity[];
};

async function request(path: string, params: Record<string, string>) {
  const endpoint = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '') {
      searchParams.set(key, value);
    }
  });
  const query = searchParams.toString();
  const url = query ? `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}` : endpoint;

  const res = await authFetch(url, { method: 'GET' }, true);
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const message = (isJson && (data?.error || data?.detail || data?.errorMessages?.[0])) || res.statusText;
    throw new Error(message || 'Request failed');
  }

  return data as any;
}

export function jiraSearch(params: JiraSearchParams) {
  return request('/jira/search/', {
    jql: params.jql ?? '',
    fields: params.fields ?? 'summary,status,priority,assignee,created,updated,issuetype,project',
    maxResults: String(params.maxResults ?? 20)
  });
}

export function jiraTimesheet(date: string) {
  return request('/jira/timesheet/', { date }) as Promise<JiraTimesheetResponse>;
}
