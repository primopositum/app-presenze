import {
  jiraSearch,
  jiraFiltersGet,
  jiraFiltersPost,
  jiraIssueTime,
  jiraAddWorklog,
  jiraUpdateWorklog,
  jiraDeleteWorklog,
  jiraUpdateIssueEstimate,
  formatScopePreset,
  parseScopePreset,
  type JiraScopeType,
  type JiraIssueTimeFilter,
  type JiraWorklogPayload,
  type JiraIssueEstimatePayload,
} from '$lib/services/jira';

export type JiraSearchInput = {
  scopeType?: 'project' | 'filter' | 'labels';
  scopeValue: string;
  assigneeFilter: string;
  maxResults: number;
};

export async function useJiraSearch(input: JiraSearchInput) {
  const rawScopeType = input.scopeType;
  const rawScopeValue = String(input.scopeValue ?? '').trim();
  const parsedPreset = parseScopePreset(rawScopeValue);
  const scopeType = parsedPreset?.type ?? rawScopeType ?? inferScopeType(rawScopeValue);
  const scopeValue = parsedPreset?.value ?? rawScopeValue;

  if (!scopeValue) {
    if (scopeType === 'filter') throw new Error('Filtro Jira obbligatorio');
    if (scopeType === 'labels') throw new Error('Label Jira obbligatoria');
    throw new Error('Project key obbligatoria');
  }

  let baseJql = '';
  if (scopeType === 'filter') {
    baseJql = `filter=${/^\d+$/.test(scopeValue) ? scopeValue : `"${scopeValue.replace(/"/g, '\\"')}"`}`;
  } else if (scopeType === 'labels') {
    baseJql = `labels=${/^\d+$/.test(scopeValue) ? scopeValue : `"${scopeValue.replace(/"/g, '\\"')}"`}`;
  } else {
    baseJql = `project=${scopeValue}`;
  }

  const jql = `${baseJql}${input.assigneeFilter ? ` AND assignee=${input.assigneeFilter}` : ''} ORDER BY created DESC`;
  const fields =
    'summary,status,priority,assignee,created,updated,issuetype,project,comment,timetracking,timespent,aggregatetimespent,timeestimate,aggregatetimeestimate,timeoriginalestimate,aggregatetimeoriginalestimate';

  return jiraSearch({
    jql,
    fields,
    maxResults: Number(input.maxResults ?? 20)
  });
}

function inferScopeType(scopeValue: string): 'project' | 'filter' | 'labels' {
  const value = String(scopeValue || '').trim();
  if (!value) return 'filter';
  if (/^(labels|space)\s*=/i.test(value)) return 'labels';
  if (/^filter\s*=/i.test(value)) return 'filter';
  if (/^project\s*=/i.test(value)) return 'project';
  if (/^\d+$/.test(value)) return 'filter';
  // Tipico project key Jira: niente spazi, uppercase + numeri/underscore.
  if (!/\s/.test(value) && /^[A-Z][A-Z0-9_]*$/.test(value)) return 'project';
  return 'filter';
}

export async function useJiraFiltersGet() {
  return jiraFiltersGet();
}

export async function useJiraFiltersPost(scopeType: JiraScopeType, scopeValue: string, append = true) {
  const filter = formatScopePreset(scopeType, scopeValue);
  return jiraFiltersPost(filter, append);
}

export async function useJiraIssueTime(issueKey: string, filter: JiraIssueTimeFilter = {}) {
  return jiraIssueTime(issueKey, filter);
}

export async function useJiraAddWorklog(issueKey: string, payload: JiraWorklogPayload) {
  return jiraAddWorklog(issueKey, payload);
}

export async function useJiraUpdateWorklog(issueKey: string, worklogId: string | number, payload: JiraWorklogPayload) {
  return jiraUpdateWorklog(issueKey, worklogId, payload);
}

export async function useJiraDeleteWorklog(issueKey: string, worklogId: string | number) {
  return jiraDeleteWorklog(issueKey, worklogId);
}

export async function useJiraUpdateIssueEstimate(issueKey: string, payload: JiraIssueEstimatePayload) {
  return jiraUpdateIssueEstimate(issueKey, payload);
}

export { parseScopePreset, formatScopePreset };
export type { JiraScopeType };
