import { jiraSearch } from '$lib/services/jira';

export type JiraSearchInput = {
  scopeType: 'project' | 'filter';
  scopeValue: string;
  assigneeFilter: string;
  maxResults: number;
};

export async function useJiraSearch(input: JiraSearchInput) {
  const scopeType = input.scopeType ?? 'project';
  const scopeValue = String(input.scopeValue ?? '').trim();

  if (!scopeValue) {
    throw new Error(scopeType === 'filter' ? 'Filtro Jira obbligatorio' : 'Project key obbligatoria');
  }

  const baseJql =
    scopeType === 'filter'
      ? `filter=${/^\d+$/.test(scopeValue) ? scopeValue : `"${scopeValue.replace(/"/g, '\\"')}"`}`
      : `project=${scopeValue}`;

  const jql = `${baseJql}${input.assigneeFilter ? ` AND assignee=${input.assigneeFilter}` : ''} ORDER BY created DESC`;
  const fields = 'summary,status,priority,assignee,created,updated,issuetype,project';

  return jiraSearch({
    jql,
    fields,
    maxResults: Number(input.maxResults ?? 20)
  });
}
