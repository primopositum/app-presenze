import { describe, expect, it } from 'vitest';
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import {
  estimateComparisons,
  isCmIssue,
  weekOpenedClosed,
  weekdayTotals,
  worklogTimeline
} from './jiraSelectors';

function entry(date: string, seconds: number): ChartWorklogEntry {
  return { date, seconds, author: 'Tizio', projectKey: 'ABC', issueKey: 'ABC-1' };
}

function issue(key: string, overrides: Partial<NonNullable<JiraHistoryIssue['fields']>> = {}): JiraHistoryIssue {
  return {
    key,
    fields: {
      summary: `Sommario ${key}`,
      worklog_authors: [{ displayName: 'Tizio', timeSpentSeconds: 7200 }],
      ...overrides
    }
  };
}

describe('serie temporale dei worklog', () => {
  it('tiene i giorni senza worklog invece di saltarli', () => {
    const { points, bucket } = worklogTimeline([entry('2026-09-01', 3600), entry('2026-09-04', 1800)]);

    expect(bucket).toBe('day');
    expect(points).toHaveLength(4);
    expect(points.map((point) => point.seconds)).toEqual([3600, 0, 0, 1800]);
  });

  it('passa ai mesi quando il periodo e piu lungo di due mesi', () => {
    const { points, bucket } = worklogTimeline([entry('2026-01-10', 3600), entry('2026-06-02', 3600)]);

    expect(bucket).toBe('month');
    expect(points).toHaveLength(6);
  });

  it('somma piu worklog nello stesso bucket', () => {
    const { points } = worklogTimeline([entry('2026-09-01', 3600), entry('2026-09-01', 1800)]);

    expect(points[0].seconds).toBe(5400);
  });

  it('ignora le date che il backend non ha valorizzato', () => {
    expect(worklogTimeline([entry('', 3600)]).points).toHaveLength(0);
  });
});

describe('ore per giorno della settimana', () => {
  it('parte dal lunedi e tiene i giorni vuoti', () => {
    // 2026-09-21 e' un lunedi, 2026-09-27 la domenica successiva.
    const totals = weekdayTotals([entry('2026-09-21', 3600), entry('2026-09-27', 1800)]);

    expect(totals).toHaveLength(7);
    expect(totals[0].seconds).toBe(3600);
    expect(totals[6].seconds).toBe(1800);
    expect(totals[3].seconds).toBe(0);
  });
});

describe('stima contro consuntivo', () => {
  it('confronta solo le issue che hanno davvero una stima', () => {
    const rows = estimateComparisons([
      issue('ABC-1', { timeoriginalestimate: 3600 }),
      issue('ABC-2')
    ]);

    expect(rows.map((row) => row.key)).toEqual(['ABC-1']);
    expect(rows[0].deviationPercent).toBe(100);
  });

  it('mette in cima lo scostamento piu grande, in entrambe le direzioni', () => {
    const rows = estimateComparisons([
      issue('ABC-1', { timeoriginalestimate: 7200 }),
      issue('ABC-2', { timeoriginalestimate: 36000 })
    ]);

    expect(rows[0].key).toBe('ABC-2');
    expect(rows[0].deviationPercent).toBeLessThan(0);
  });
});

describe('marcatore CM', () => {
  it('riconosce il marcatore nella chiave della issue e del progetto', () => {
    expect(isCmIssue(issue('CM-12'))).toBe(true);
    expect(isCmIssue({ key: 'ABC-1', fields: { project: { key: 'CMX' } } })).toBe(true);
    expect(isCmIssue(issue('ABC-1'))).toBe(false);
  });

  it('con un marcatore vuoto non seleziona niente', () => {
    expect(isCmIssue(issue('CM-12'), '  ')).toBe(false);
  });
});

describe('task aperte e chiuse nella settimana', () => {
  // 2026-10-02 e' un venerdi: la settimana va da lunedi 28/09 a domenica 04/10.
  const friday = new Date(2026, 9, 2, 11, 0);
  const done = { name: 'Completata', statusCategory: { key: 'done' } };
  const open = { name: 'In corso', statusCategory: { key: 'indeterminate' } };

  it('parte dal lunedi e conta aperte e chiuse per giorno', () => {
    const days = weekOpenedClosed(
      [
        issue('ABC-1', { created: '2026-09-28T09:00:00.000+0200', status: open }),
        issue('ABC-2', {
          created: '2026-09-29T10:00:00.000+0200',
          status: done,
          statuscategorychangedate: '2026-10-01T16:00:00.000+0200'
        }),
        issue('ABC-3', {
          created: '2026-08-01T10:00:00.000+0200',
          status: done,
          statuscategorychangedate: '2026-10-01T09:00:00.000+0200'
        })
      ],
      friday
    );

    expect(days).toHaveLength(7);
    expect(days[0].label).toBe('Lun 28');
    expect(days.map((day) => day.opened)).toEqual([1, 1, 0, 0, 0, 0, 0]);
    expect(days.map((day) => day.closed)).toEqual([0, 0, 0, 2, 0, 0, 0]);
  });

  it('non conta come chiusa una task riaperta, ne le date fuori settimana', () => {
    const days = weekOpenedClosed(
      [
        issue('ABC-1', { status: open, statuscategorychangedate: '2026-09-30T09:00:00.000+0200' }),
        issue('ABC-2', { created: '2026-10-05T09:00:00.000+0200', status: done, resolutiondate: '2026-09-27T09:00:00.000+0200' })
      ],
      friday
    );

    expect(days.every((day) => day.opened === 0 && day.closed === 0)).toBe(true);
  });
});
