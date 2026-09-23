import { describe, expect, it } from 'vitest';
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import { resolveValues } from '../core/filterState';
import type { FilterValues } from '../core/types';
import { applyJiraHistoryFilters, jiraHistoryFilters } from './apply';

function issue(key: string, authors: [string, number][]) {
  return {
    key,
    fields: {
      summary: `Titolo ${key}`,
      project: { key: key.split('-')[0], name: key.split('-')[0] },
      issuetype: { name: 'Task', subtask: false },
      status: { name: 'In corso' },
      worklog_authors: authors.map(([displayName, timeSpentSeconds]) => ({
        displayName,
        timeSpentSeconds
      }))
    }
  } satisfies JiraHistoryIssue;
}

function entry(issueKey: string, date: string, author: string, seconds: number): ChartWorklogEntry {
  return { issueKey, date, author, seconds, projectKey: issueKey.split('-')[0] };
}

const values = (changes: FilterValues = {}) => resolveValues(jiraHistoryFilters, changes);

describe('filtri Ore Jira', () => {
  const issues = [
    issue('ABC-1', [
      ['Anna', 7200],
      ['Luca', 3600]
    ]),
    issue('DEF-2', [['Luca', 1800]])
  ];
  const entries = [
    entry('ABC-1', '2026-03-02', 'Anna', 7200),
    entry('ABC-1', '2026-03-07', 'Luca', 3600),
    entry('DEF-2', '2026-03-03', 'Luca', 1800)
  ];

  it('senza filtri restituisce tutto invariato', () => {
    const result = applyJiraHistoryFilters(issues, entries, values());
    expect(result.issues).toEqual(issues);
    expect(result.entries).toHaveLength(3);
  });

  it('i filtri sui worklog ricalcolano le ore per persona', () => {
    const result = applyJiraHistoryFilters(issues, entries, values({ authors: ['Luca'] }));
    expect(result.issues.map((item) => item.key)).toEqual(['ABC-1', 'DEF-2']);
    expect(result.issues[0].fields?.worklog_authors).toEqual([
      { displayName: 'Luca', timeSpentSeconds: 3600 }
    ]);
  });

  it('i giorni della settimana escludono il sabato', () => {
    // Il 7 marzo 2026 cade di sabato.
    const result = applyJiraHistoryFilters(
      issues,
      entries,
      values({ weekdays: ['0', '1', '2', '3', '4'] })
    );
    expect(result.entries.map((item) => item.date)).toEqual(['2026-03-02', '2026-03-03']);
  });

  it('progetti, regex e soglia di ore agiscono sulla issue', () => {
    expect(applyJiraHistoryFilters(issues, entries, values({ projects: ['DEF'] })).issues).toHaveLength(1);
    expect(applyJiraHistoryFilters(issues, entries, values({ keyPattern: '^abc-' })).issues).toHaveLength(1);
    const heavy = applyJiraHistoryFilters(issues, entries, values({ issueHours: { min: 1, max: null } }));
    expect(heavy.issues.map((item) => item.key)).toEqual(['ABC-1']);
    expect(heavy.entries.every((item) => item.issueKey === 'ABC-1')).toBe(true);
  });
});
