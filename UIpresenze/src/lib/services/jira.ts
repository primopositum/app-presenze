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

export type JiraCreatedWorklogResponse = {
  id?: string;
  started?: string;
  timeSpent?: string;
  timeSpentSeconds?: number;
  author?: { displayName?: string };
};

export type JiraWorklogCreatedEvent = {
  day: string;
  activity: JiraTimesheetActivity;
};

export type JiraTimesheetResponse = {
  date: string;
  utente_email?: string;
  jira_email?: string;
  count: number;
  activities: JiraTimesheetActivity[];
};

export type JiraTimesheetDayUser = {
  utente_email?: string;
  jira_email?: string;
  count: number;
  activities: JiraTimesheetActivity[];
};

export type JiraTimesheetMonthDay = {
  date: string;
  count: number;
  users: Record<string, JiraTimesheetDayUser>;
};

export type JiraTimesheetMonthUser = {
  utente_email?: string;
  jira_email?: string;
  account_id?: string;
  count: number;
  days: Record<string, { date: string; count: number; activities: JiraTimesheetActivity[] }>;
};

export type JiraTimesheetMonthResponse = {
  year: number;
  month: number;
  start_date: string;
  end_date: string;
  count: number;
  users_count: number;
  users: JiraTimesheetMonthUser[];
  days: Record<string, JiraTimesheetMonthDay>;
};

export type JiraTimesheetParams = {
  email?: string | null;
  mail?: string | null;
  utente_email?: string | null;
  jira_email?: string | null;
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

export type JiraUpdateStatePayload = {
  transition_id?: string | number;
  status?: string;
  to_status?: string;
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

export type JiraYearWorklogItem = {
  worklog_id?: string;
  author?: string;
  author_account_id?: string;
  started?: string;
  date?: string;
  time_spent?: string;
  time_spent_seconds?: number;
  comment?: string;
};

export type JiraYearWorklogIssue = {
  issue_key: string;
  issue_summary?: string;
  status?: string;
  assignee?: string;
  issue_type?: string;
  is_subtask?: boolean;
  parent_key?: string;
  parent_summary?: string;
  worklogs_count: number;
  total_seconds: number;
  worklogs: JiraYearWorklogItem[];
};

export type JiraYearWorklogProject = {
  project_key: string;
  project_name: string;
  issues_count: number;
  worklogs_count: number;
  total_seconds: number;
  issues: JiraYearWorklogIssue[];
};

export type JiraHistoryIssue = {
  id?: string;
  key: string;
  self?: string;
  fields?: {
    summary?: string;
    status?: { name?: string };
    assignee?: { displayName?: string } | null;
    issuetype?: { name?: string; subtask?: boolean } | null;
    parent?: { key?: string; fields?: { summary?: string } } | null;
    subtasks?: JiraHistoryIssue[];
    subtasks_enriched?: JiraHistoryIssue[];
    project?: { key?: string; name?: string };
    timespent?: number | null;
    aggregatetimespent?: number | null;
    timeestimate?: number | null;
    aggregatetimeestimate?: number | null;
    timeoriginalestimate?: number | null;
    aggregatetimeoriginalestimate?: number | null;
    timetracking?: {
      timeSpentSeconds?: number;
      originalEstimateSeconds?: number;
    } | null;
    created?: string;
    updated?: string;
    resolutiondate?: string | null;
    worklog_authors?: { displayName?: string; timeSpentSeconds?: number }[];
    worklog_primary_author?: { displayName?: string; timeSpentSeconds?: number };
  };
};

export type JiraYearWorklogResponse = {
  view?: 'tree';
  year: number;
  month?: number | 'all';
  jql: string;
  projects_count: number;
  issues_count: number;
  worklogs_count: number;
  total_seconds: number;
  projects: JiraYearWorklogProject[];
  // Issue con ore loggate nel periodo, senza filtro sullo stato corrente.
  worklog_issues_count?: number;
  worklog_issues?: JiraHistoryIssue[];
};

export type JiraYearWorklogProgress = {
  loaded: number;
  total: number;
};

export type JiraCompletedHistoryResponse = {
  view?: 'completed';
  year: number | 'all';
  month?: number | 'all';
  completed?: boolean;
  jql: string;
  total: number;
  startAt: number;
  maxResults: number;
  issues: JiraHistoryIssue[];
  worklog_enrich_error?: boolean;
  worklog_enrich_meta?: {
    enabled: boolean;
    candidate_issues: number;
    enriched_issues: number;
    failed_issues: number;
  };
  worklog_enrich_logs?: { level: string; message: string; issue_key?: string }[];
};

export type JiraStatusInfo = {
  id?: string;
  name: string;
  category_key?: string;
  category_name?: string;
};

export type JiraStatusesResponse = {
  source?: 'project' | 'global';
  project_key?: string | null;
  count: number;
  statuses: JiraStatusInfo[];
};

export type JiraFiltersResponse = {
  filters: string[];
  JiraControl?: boolean;
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

export function jiraTimesheet(date: string, params: JiraTimesheetParams = {}) {
  const targetEmail =
    String(params.email || params.utente_email || params.jira_email || params.mail || '').trim();

  if (targetEmail) {
    return requestJson('/jira/timesheet/', 'POST', {
      date,
      email: targetEmail,
    }) as Promise<JiraTimesheetResponse>;
  }

  return request('/jira/timesheet/', { date }) as Promise<JiraTimesheetResponse>;
}

export function jiraTimesheetMonth(year: number, month: number, params: JiraTimesheetParams = {}) {
  const targetEmail =
    String(params.email || params.utente_email || params.jira_email || params.mail || '').trim();

  if (targetEmail) {
    return requestJson('/jira/timesheet/month/', 'POST', {
      year,
      month,
      email: targetEmail,
    }) as Promise<JiraTimesheetMonthResponse>;
  }

  return request('/jira/timesheet/month/', {
    year: String(year),
    month: String(month),
  }) as Promise<JiraTimesheetMonthResponse>;
}

export function jiraWorklogsByYear(year: string | number, month: string | number = 'all') {
  return request('/jira/worklogs/year/', {
    view: 'tree',
    year: String(year ?? '').trim(),
    month: String(month ?? 'all').trim(),
  }) as Promise<JiraYearWorklogResponse>;
}

export async function jiraWorklogsByYearStream(
  year: string | number,
  month: string | number = 'all',
  onProgress?: (progress: JiraYearWorklogProgress) => void,
  signal?: AbortSignal
): Promise<JiraYearWorklogResponse> {
  const normalizedYear = String(year ?? '').trim();
  const normalizedMonth = String(month ?? 'all').trim();
  const params = new URLSearchParams({ year: normalizedYear, month: normalizedMonth });
  const url = `${BASE}/jira/worklogs/year/stream/?${params.toString()}`;
  const res = await authFetch(
    url,
    {
      method: 'GET',
      headers: { Accept: 'text/event-stream' },
      signal
    },
    true
  );

  if (!res.ok) {
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : await res.text();
    const message = (isJson && (data?.error || data?.detail)) || res.statusText;
    throw new Error(message || 'Request failed');
  }
  if (!res.body) {
    throw new Error('Stream worklog non disponibile');
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result: JiraYearWorklogResponse | null = null;

  const parseEvent = (eventBlock: string) => {
    const rawData = eventBlock
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!rawData) return;

    const event = JSON.parse(rawData);
    if (event.type === 'start') {
      onProgress?.({ loaded: 0, total: Number(event.total || 0) });
      return;
    }
    if (event.type === 'progress') {
      onProgress?.({ loaded: Number(event.loaded || 0), total: Number(event.total || 0) });
      return;
    }
    if (event.type === 'error') {
      throw new Error(String(event.error || 'Errore caricamento worklog annuali'));
    }
    if (event.type === 'done') {
      const { type: _type, ...payload } = event;
      result = payload as JiraYearWorklogResponse;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, '\n');

    let separatorIndex = buffer.indexOf('\n\n');
    while (separatorIndex >= 0) {
      const eventBlock = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      parseEvent(eventBlock);
      separatorIndex = buffer.indexOf('\n\n');
    }

    if (done) break;
  }

  if (buffer.trim()) parseEvent(buffer);
  if (!result) {
    throw new Error('Stream worklog terminato senza dati');
  }
  return result;
}

export function jiraCompletedHistory(
  year: string | number = 'all',
  month: string | number = 'all',
  // Storico completo: nessun filtro sullo stato corrente della issue.
  // Passa `true` per limitare il risultato alle sole issue Done/Completata.
  completed = false
) {
  const normalizedYear = String(year ?? 'all').trim().toLowerCase();
  return request('/jira/worklogs/year/', {
    view: 'completed',
    year: normalizedYear && normalizedYear !== 'all' ? normalizedYear : '',
    month: String(month ?? 'all').trim().toLowerCase(),
    completed: String(completed),
  }) as Promise<JiraCompletedHistoryResponse>;
}

export function jiraStatuses(scopeType = '', scopeValue = '') {
  return request('/jira/statuses/', {
    scopeType: String(scopeType || '').trim(),
    scopeValue: String(scopeValue || '').trim(),
  }) as Promise<JiraStatusesResponse>;
}

export function jiraFiltersGet() {
  return requestJson('/jira/filters/', 'GET') as Promise<JiraFiltersResponse>;
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
  return requestJson(
    `/jira/time/${encodeURIComponent(issueKey)}/log/`,
    'POST',
    payload as unknown as Record<string, unknown>
  ) as Promise<JiraCreatedWorklogResponse>;
}

export function jiraUpdateWorklog(issueKey: string, worklogId: string | number, payload: JiraWorklogPayload) {
  return requestJson(
    `/jira/time/${encodeURIComponent(issueKey)}/log/${encodeURIComponent(String(worklogId))}/`,
    'PUT',
    payload as unknown as Record<string, unknown>
  ) as Promise<JiraCreatedWorklogResponse>;
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

export function jiraUpdateState(workKey: string, payload: JiraUpdateStatePayload) {
  return requestJson(
    `/jira/work/${encodeURIComponent(workKey)}/state/`,
    'PUT',
    payload as unknown as Record<string, unknown>
  ) as Promise<{ ok: boolean; work_key: string; transition_id?: string; to_status?: string }>;
}
