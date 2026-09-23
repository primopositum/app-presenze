import { describe, expect, it } from 'vitest';
import type { ChartRow } from '../../chartData';
import type { JiraHistoryIssue } from '$lib/services/jira';
import { NEUTRAL } from '../../palette';
import { FOCUS_COLOR, highlightRows, indexRows, median, standing } from './compare';
import { compareIssue } from './issueCompare';

function row(id: string, value: number): ChartRow {
  return { id, label: id, value, percent: 0, display: String(value), color: '' };
}

describe('confronto', () => {
  it('posizione e percentile', () => {
    expect(standing(10, [5, 20, 1])).toEqual({ rank: 2, total: 4, percentile: (2 / 3) * 100 });
    expect(standing(3, [])).toEqual({ rank: 1, total: 1, percentile: 100 });
  });

  it('mediana su numero pari e dispari', () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 3, 2])).toBe(2.5);
  });

  it("indice con media = 100 e misure senza media escluse", () => {
    const rows = indexRows([
      { id: 'a', label: 'A', value: 20, others: [10, 10], format: String },
      { id: 'b', label: 'B', value: 5, others: [0, 0], format: String }
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0].value).toBe(200);
  });

  it('la voce scelta resta in classifica anche fuori dalle prime', () => {
    const rows = [row('a', 9), row('b', 8), row('c', 7), row('d', 1)];
    const top = highlightRows(rows, 'd', 3);
    expect(top.map((item) => item.id)).toEqual(['a', 'b', 'd']);
    expect(top[2].label).toBe('#4 d');
    expect(top[2].color).toBe(FOCUS_COLOR);
    expect(top[0].color).toBe(NEUTRAL);
  });

  it('confronto di una issue con le altre', () => {
    const issue = (key: string, seconds: number) =>
      ({
        key,
        fields: { summary: key, worklog_authors: [{ displayName: 'Anna', timeSpentSeconds: seconds }] }
      }) satisfies JiraHistoryIssue;
    const issues = [issue('A-1', 7200), issue('A-2', 3600), issue('A-3', 3600)];
    const entries = [
      { issueKey: 'A-1', date: '2026-03-02', author: 'Anna', seconds: 3600, projectKey: 'A' },
      { issueKey: 'A-1', date: '2026-03-04', author: 'Anna', seconds: 3600, projectKey: 'A' },
      { issueKey: 'A-2', date: '2026-03-02', author: 'Anna', seconds: 3600, projectKey: 'A' },
      { issueKey: 'A-3', date: '2026-03-03', author: 'Anna', seconds: 3600, projectKey: 'A' }
    ];
    const result = compareIssue(issues, entries, 'A-1', { topCount: 10, bucket: 'day' });
    expect(result?.standing.rank).toBe(1);
    expect(result?.share).toBe(0.5);
    expect(result?.index.find((item) => item.id === 'seconds')?.value).toBe(200);
    expect(result?.index.find((item) => item.id === 'span')?.value).toBe(300);
    expect(compareIssue(issues, entries, 'Z-9', { topCount: 10, bucket: 'day' })).toBeNull();
  });
});
