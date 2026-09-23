import { describe, expect, it } from 'vitest';
import type { JiraHistoryIssue } from '$lib/services/jira';
import { resolveValues } from '../core/filterState';
import type { FilterValues } from '../core/types';
import { applyCmFilters, cmTasksFilters } from './apply';

function issue(key: string, projectKey: string, seconds: number) {
  return {
    key,
    fields: {
      project: { key: projectKey },
      worklog_authors: [{ displayName: 'Anna', timeSpentSeconds: seconds }]
    }
  } satisfies JiraHistoryIssue;
}

const values = (changes: FilterValues = {}) => resolveValues(cmTasksFilters, changes);
const keys = (items: JiraHistoryIssue[]) => items.map((item) => item.key);

describe('filtri Task CM', () => {
  const issues = [issue('CM-1', 'OPS', 3600), issue('OPS-2', 'CMX', 1800), issue('ABC-3', 'ABC', 3600)];

  it('cerca il marcatore dove indicato', () => {
    expect(keys(applyCmFilters(issues, [], values(), 'CM').issues)).toEqual(['CM-1', 'OPS-2']);
    expect(keys(applyCmFilters(issues, [], values({ markerScope: 'issue' }), 'CM').issues)).toEqual([
      'CM-1'
    ]);
    expect(
      keys(applyCmFilters(issues, [], values({ markerScope: 'project' }), 'CM').issues)
    ).toEqual(['OPS-2']);
  });

  it('marcatore personalizzato e quota su tutto il periodo', () => {
    const result = applyCmFilters(issues, [], values({ marker: 'abc' }), 'CM');
    expect(result.marker).toBe('ABC');
    expect(keys(result.issues)).toEqual(['ABC-3']);
    expect(result.periodSeconds).toBe(9000);
  });
});
