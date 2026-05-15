import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type JiraSearchParams = {
  jql: string;
  fields?: string;
  maxResults?: number;
  startAt?: number;
};

export type JiraScopeType = 'project' | 'filter' | 'labels';

export type JiraScopePreset = {
  raw: string;
  type: JiraScopeType;
  value: string;
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

export type JiraIssueTimeFilter = {
  started?: string;
  date?: string;
  time?: string;
  tz?: string;
};

export type JiraWorklogPayload = {
  timeSpent: string;
  comment?: string;
  started?: string;
  date?: string;
  time?: string;
  tz?: string;
};

export type JiraIssueEstimatePayload = {
  originalEstimate?: string;
  remainingEstimate?: string;
};

export type JiraIssueTimeTracking = {
  originalEstimate?: string;
  remainingEstimate?: string;
  timeSpent?: string;
  originalEstimateSeconds?: number;
  remainingEstimateSeconds?: number;
  timeSpentSeconds?: number;
};

export type JiraIssueTimeSummary = {
  key?: string;
  summary?: string;
  status?: string;
  project?: { key?: string; name?: string };
  timetracking?: JiraIssueTimeTracking;
};

export type JiraIssueTimeResponse = {
  issue: JiraIssueTimeSummary;
  worklogs: any[];
  worklogs_count: number;
  filters: { started?: string | null };
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

async function requestJson(path: string, method: 'GET' | 'POST' | 'PUT' | 'DELETE', json?: Record<string, unknown>) {
  const endpoint = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers();
  if (json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await authFetch(
    endpoint,
    {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : undefined,
    },
    true
  );
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const message = (isJson && (data?.error || data?.detail || data?.errorMessages?.[0])) || res.statusText;
    throw new Error(message || 'Request failed');
  }

  return data as any;
}

export function parseScopePreset(raw: string): JiraScopePreset | null {
  const normalized = String(raw || '').trim();
  if (!normalized) return null;
  const match = normalized.match(/^(project|filter|labels|space)\s*=\s*(.+)$/i);
  if (!match) return null;
  const matchedType = match[1].toLowerCase();
  const type: JiraScopeType = matchedType === 'space' ? 'labels' : (matchedType as JiraScopeType);
  return {
    raw: normalized,
    type,
    value: match[2].trim(),
  };
}

export function formatScopePreset(type: JiraScopeType, value: string) {
  return `${type} = ${String(value || '').trim()}`;
}

export function jiraSearch(params: JiraSearchParams) {
  return request('/jira/search/', {
    jql: params.jql ?? '',
    fields: params.fields ?? 'summary,status,priority,assignee,created,updated,issuetype,project',
    maxResults: params.maxResults !== undefined ? String(params.maxResults) : '',
    startAt: String(params.startAt ?? 0),
  });
}

export function jiraTimesheet(date: string) {
  return request('/jira/timesheet/', { date }) as Promise<JiraTimesheetResponse>;
}

export function jiraFiltersGet() {
  return requestJson('/jira/filters/', 'GET') as Promise<{ filters: string[] }>;
}

export function jiraFiltersPost(filter: string, append = true) {
  return requestJson('/jira/filters/', 'POST', { filter, append }) as Promise<{ ok?: boolean; filters: string[] }>;
}

export function jiraIssueTime(issueKey: string, filter: JiraIssueTimeFilter = {}) {
  return request(`/jira/time/${encodeURIComponent(issueKey)}/`, {
    started: filter.started ?? '',
    date: filter.date ?? '',
    time: filter.time ?? '',
    tz: filter.tz ?? '',
  }) as Promise<JiraIssueTimeResponse>;
}

export function jiraAddWorklog(issueKey: string, payload: JiraWorklogPayload) {
  return requestJson(`/jira/time/${encodeURIComponent(issueKey)}/log/`, 'POST', payload as unknown as Record<string, unknown>);
}

export function jiraUpdateWorklog(issueKey: string, worklogId: string | number, payload: JiraWorklogPayload) {
  return requestJson(
    `/jira/time/${encodeURIComponent(issueKey)}/log/${encodeURIComponent(String(worklogId))}/`,
    'PUT',
    payload as unknown as Record<string, unknown>
  );
}

export function jiraDeleteWorklog(issueKey: string, worklogId: string | number) {
  return requestJson(`/jira/time/${encodeURIComponent(issueKey)}/log/${encodeURIComponent(String(worklogId))}/`, 'DELETE');
}

export function jiraUpdateIssueEstimate(issueKey: string, payload: JiraIssueEstimatePayload) {
  return requestJson(
    `/jira/time/${encodeURIComponent(issueKey)}/`,
    'PUT',
    payload as unknown as Record<string, unknown>
  ) as Promise<{ ok: boolean; issue: JiraIssueTimeSummary }>;
}
