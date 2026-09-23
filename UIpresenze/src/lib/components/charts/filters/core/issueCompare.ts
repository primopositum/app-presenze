/**
 * Confronto di una issue Jira con le altre dello stesso perimetro.
 *
 * Lo usano "Ore Jira" e "Task CM": il perimetro (le issue gia' filtrate) lo
 * decide la schermata, qui si calcolano solo le misure.
 */
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import { addGrouped, buildChartRows, type ChartGroups } from '../../chartData';
import { fmtDays, fmtHours, fmtInt, fmtPercent } from '../../format';
import {
  addIssueUserSeconds,
  issueEstimateSeconds,
  issueLoggedSeconds,
  issueTitle,
  worklogTimeline,
  type TimelineBucket
} from '../../jiraSelectors';
import { SERIES } from '../../palette';
import { highlightRows, indexRows, mean, standing, type CompareMetric } from './compare';

type IssueStats = {
  seconds: number;
  people: number;
  worklogs: number;
  activeDays: number;
  /** Giorni fra il primo e l'ultimo worklog, estremi inclusi. */
  spanDays: number;
};

const DAY_MS = 86_400_000;

function statsByIssue(issues: JiraHistoryIssue[], entries: ChartWorklogEntry[]) {
  const perIssue = new Map<string, { days: Set<string>; count: number; first: string; last: string }>();
  entries.forEach((entry) => {
    const day = entry.date.slice(0, 10);
    const current = perIssue.get(entry.issueKey) ?? { days: new Set<string>(), count: 0, first: day, last: day };
    current.days.add(day);
    current.count += 1;
    if (day < current.first) current.first = day;
    if (day > current.last) current.last = day;
    perIssue.set(entry.issueKey, current);
  });

  return new Map<string, IssueStats>(
    issues.map((issue) => {
      const logs = perIssue.get(issue.key);
      const span = logs
        ? Math.round((Date.parse(logs.last) - Date.parse(logs.first)) / DAY_MS) + 1
        : 0;
      return [
        issue.key,
        {
          seconds: issueLoggedSeconds(issue),
          people: (issue.fields?.worklog_authors || []).filter(
            (author) => Number(author?.timeSpentSeconds || 0) > 0
          ).length,
          worklogs: logs?.count ?? 0,
          activeDays: logs?.days.size ?? 0,
          spanDays: Number.isFinite(span) ? span : 0
        }
      ];
    })
  );
}

export type IssueComparison = ReturnType<typeof compareIssue>;

/**
 * null se la issue scelta non e' nel perimetro: e' stata esclusa dai filtri o
 * non ha ore nel periodo.
 */
export function compareIssue(
  issues: JiraHistoryIssue[],
  entries: ChartWorklogEntry[],
  focusKey: string,
  options: { topCount: number; bucket: TimelineBucket | 'auto' }
) {
  const focus = issues.find((issue) => issue.key === focusKey);
  if (!focus) return null;

  const stats = statsByIssue(issues, entries);
  const mine = stats.get(focus.key)!;
  const others = issues.filter((issue) => issue.key !== focus.key).map((issue) => stats.get(issue.key)!);
  const pick = (read: (item: IssueStats) => number) => others.map(read);
  const perLog = (item: IssueStats) => (item.worklogs > 0 ? item.seconds / item.worklogs : 0);

  const metrics: CompareMetric[] = [
    { id: 'seconds', label: 'Ore loggate', value: mine.seconds, others: pick((i) => i.seconds), format: fmtHours },
    { id: 'people', label: 'Persone coinvolte', value: mine.people, others: pick((i) => i.people), format: fmtInt },
    { id: 'worklogs', label: 'Numero di worklog', value: mine.worklogs, others: pick((i) => i.worklogs), format: fmtInt },
    { id: 'activeDays', label: 'Giorni con worklog', value: mine.activeDays, others: pick((i) => i.activeDays), format: fmtInt },
    { id: 'perLog', label: 'Ore medie per worklog', value: perLog(mine), others: pick(perLog), format: fmtHours },
    { id: 'span', label: 'Durata (primo-ultimo log)', value: mine.spanDays, others: pick((i) => i.spanDays), format: fmtDays }
  ];

  const allSeconds = pick((i) => i.seconds);
  const totalSeconds = allSeconds.reduce((sum, value) => sum + value, mine.seconds);
  const estimate = issueEstimateSeconds(focus);

  const ranking: ChartGroups = {};
  issues.forEach((issue) =>
    addGrouped(ranking, issue.key, `${issue.key} · ${issueTitle(issue)}`, stats.get(issue.key)!.seconds)
  );

  const people: ChartGroups = {};
  addIssueUserSeconds(people, focus);

  const timeline = worklogTimeline(
    entries.filter((entry) => entry.issueKey === focus.key),
    options.bucket
  );

  return {
    key: focus.key,
    label: `${focus.key} · ${issueTitle(focus)}`,
    others: others.length,
    standing: standing(mine.seconds, allSeconds),
    share: totalSeconds > 0 ? mine.seconds / totalSeconds : 0,
    seconds: mine.seconds,
    averageSeconds: mean(allSeconds),
    estimate: estimate > 0 ? { seconds: estimate, deviation: ((mine.seconds - estimate) / estimate) * 100 } : null,
    index: indexRows(metrics),
    ranking: highlightRows(buildChartRows(ranking, { format: fmtHours }), focus.key, options.topCount),
    people: buildChartRows(people, { format: fmtHours, color: SERIES[2] }),
    timeline: timeline.points.map((point) => ({ key: point.key, label: point.label, value: point.seconds })),
    bucketName: timeline.bucket === 'month' ? 'mese' : 'giorno'
  };
}

export function deviationLabel(deviation: number) {
  return deviation >= 0
    ? `${fmtPercent(deviation, 0)} sopra la stima`
    : `${fmtPercent(Math.abs(deviation), 0)} sotto la stima`;
}
