/** Trasformazioni pure delle issue Jira nei dati per i grafici. */
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import { addGrouped, type ChartGroups } from './chartData';
import { fmtDay, fmtMonth } from './format';

/** Marcatore usato per isolare le task "CM". */
export const CM_MARKER = 'CM';

/** Ore realmente loggate su una issue nel periodo, sommando i worklog per autore. */
export function issueLoggedSeconds(issue: JiraHistoryIssue) {
  return (issue.fields?.worklog_authors || []).reduce(
    (total, author) => total + Math.max(0, Number(author?.timeSpentSeconds || 0)),
    0
  );
}

/** Stima originale della issue, quando Jira la espone. */
export function issueEstimateSeconds(issue: JiraHistoryIssue) {
  const fields = issue.fields;
  const candidates = [
    fields?.timeoriginalestimate,
    fields?.timetracking?.originalEstimateSeconds,
    fields?.aggregatetimeoriginalestimate
  ];
  const estimate = candidates.find((value) => Number(value) > 0);
  return Math.max(0, Number(estimate || 0));
}

/** Ripartisce le ore di una issue fra gli autori dei worklog (fallback: assegnatario). */
export function addIssueUserSeconds(groups: ChartGroups, issue: JiraHistoryIssue) {
  const authors = (issue.fields?.worklog_authors || [])
    .map((author) => ({
      name: String(author?.displayName || '').trim() || 'Non assegnato',
      seconds: Math.max(0, Number(author?.timeSpentSeconds || 0))
    }))
    .filter((author) => author.seconds > 0);

  if (authors.length > 0) {
    authors.forEach((author) => addGrouped(groups, author.name, author.name, author.seconds));
    return;
  }

  const assignee = issue.fields?.assignee?.displayName || 'Non assegnato';
  addGrouped(groups, assignee, assignee, issueLoggedSeconds(issue));
}

export function issueProjectKey(issue: JiraHistoryIssue) {
  return issue.fields?.project?.key || 'N/D';
}

export function issueProjectLabel(issue: JiraHistoryIssue) {
  return issue.fields?.project?.name || issue.fields?.project?.key || 'Progetto non disponibile';
}

/** Issue arrivata in fondo al flusso: categoria Done o stato "Completata"/"Completed". */
export function isIssueDone(issue: JiraHistoryIssue) {
  const status = issue.fields?.status;
  const name = String(status?.name || '').trim().toLowerCase();
  return status?.statusCategory?.key === 'done' || name === 'completata' || name === 'completed';
}

export type WeekFlowDay = { key: string; label: string; opened: number; closed: number };

/**
 * Task aperte e chiuse giorno per giorno, da lunedi a domenica della settimana di `referenceDate`.
 * Aperta = creata quel giorno; chiusa = oggi Done e passata a Done quel giorno
 * (`statuscategorychangedate`, o `resolutiondate` se manca).
 */
export function weekOpenedClosed(issues: JiraHistoryIssue[], referenceDate: Date): WeekFlowDay[] {
  const monday = new Date(
    referenceDate.getFullYear(),
    referenceDate.getMonth(),
    referenceDate.getDate() - ((referenceDate.getDay() + 6) % 7)
  );
  const labels = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];
  const days = labels.map((label, index) => {
    const date = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + index);
    return { key: dayKey(date), label: `${label} ${date.getDate()}`, opened: 0, closed: 0 };
  });
  const byKey = new Map(days.map((day) => [day.key, day]));

  issues.forEach((issue) => {
    const opened = timestampDay(issue.fields?.created);
    if (opened) {
      const day = byKey.get(opened);
      if (day) day.opened += 1;
    }
    if (!isIssueDone(issue)) return;
    const closed = timestampDay(issue.fields?.statuscategorychangedate || issue.fields?.resolutiondate);
    if (closed) {
      const day = byKey.get(closed);
      if (day) day.closed += 1;
    }
  });

  return days;
}

function dayKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

/** Giorno locale di un timestamp Jira ("2026-09-29T10:15:00.000+0200"). */
function timestampDay(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(String(value).replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
  return Number.isNaN(date.getTime()) ? null : dayKey(date);
}

export function issueTitle(issue: JiraHistoryIssue) {
  return String(issue.fields?.summary || '').trim() || issue.key;
}

export function issueTypeLabel(issue: JiraHistoryIssue) {
  return String(issue.fields?.issuetype?.name || '').trim() || 'Senza tipo';
}

export function issueStatusLabel(issue: JiraHistoryIssue) {
  return String(issue.fields?.status?.name || '').trim() || 'Senza stato';
}

/** Task "CM": il marcatore compare nella chiave della issue o del progetto. */
export function isCmIssue(issue: JiraHistoryIssue, marker = CM_MARKER) {
  const needle = marker.trim().toUpperCase();
  if (!needle) return false;
  const key = String(issue.key || '').toUpperCase();
  const projectKey = String(issue.fields?.project?.key || '').toUpperCase();
  return projectKey.includes(needle) || key.split('-')[0].includes(needle);
}

export type EstimateComparison = {
  key: string;
  title: string;
  estimateSeconds: number;
  loggedSeconds: number;
  /** Scostamento dalla stima in percentuale: negativo = sotto stima. */
  deviationPercent: number;
};

/** Issue con stima e consuntivo entrambi presenti: le sole confrontabili. */
export function estimateComparisons(issues: JiraHistoryIssue[]): EstimateComparison[] {
  return issues
    .map((issue) => {
      const estimateSeconds = issueEstimateSeconds(issue);
      const loggedSeconds = issueLoggedSeconds(issue);
      return {
        key: issue.key,
        title: issueTitle(issue),
        estimateSeconds,
        loggedSeconds,
        deviationPercent:
          estimateSeconds > 0 ? ((loggedSeconds - estimateSeconds) / estimateSeconds) * 100 : 0
      };
    })
    .filter((row) => row.estimateSeconds > 0 && row.loggedSeconds > 0)
    .sort((first, second) => Math.abs(second.deviationPercent) - Math.abs(first.deviationPercent));
}

export type TimelinePoint = {
  key: string;
  label: string;
  /** Inizio del bucket: serve a ordinare, non viene disegnato. */
  date: Date;
  seconds: number;
};

export type TimelineBucket = 'day' | 'month';

function parseWorklogDay(value: string) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * Serie temporale delle ore loggate.
 *
 * I bucket vuoti restano nella serie: una linea che salta i giorni senza
 * worklog racconterebbe un andamento che non c'e'.
 */
export function worklogTimeline(
  entries: ChartWorklogEntry[],
  bucket: TimelineBucket | 'auto' = 'auto'
): { points: TimelinePoint[]; bucket: TimelineBucket } {
  const days = entries
    .map((entry) => ({ date: parseWorklogDay(entry.date), seconds: entry.seconds }))
    .filter((entry): entry is { date: Date; seconds: number } => entry.date !== null);

  if (days.length === 0) return { points: [], bucket: bucket === 'auto' ? 'day' : bucket };

  const times = days.map((entry) => entry.date.getTime());
  const first = new Date(Math.min(...times));
  const last = new Date(Math.max(...times));
  const spanDays = Math.round((last.getTime() - first.getTime()) / 86_400_000);
  const resolved: TimelineBucket = bucket === 'auto' ? (spanDays > 62 ? 'month' : 'day') : bucket;

  const start =
    resolved === 'month'
      ? new Date(first.getFullYear(), first.getMonth(), 1)
      : new Date(first.getFullYear(), first.getMonth(), first.getDate());

  const slots: TimelinePoint[] = [];
  const indexByKey = new Map<string, number>();
  const keyOf = (date: Date) =>
    resolved === 'month'
      ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

  for (let cursor = start; cursor <= last; ) {
    const key = keyOf(cursor);
    indexByKey.set(key, slots.length);
    slots.push({
      key,
      label: resolved === 'month' ? fmtMonth(cursor) : fmtDay(cursor),
      date: cursor,
      seconds: 0
    });
    cursor =
      resolved === 'month'
        ? new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)
        : new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() + 1);
  }

  days.forEach((entry) => {
    const index = indexByKey.get(keyOf(entry.date));
    if (index !== undefined) slots[index].seconds += Math.max(0, entry.seconds);
  });

  return { points: slots, bucket: resolved };
}

/** Ore per giorno della settimana: da lunedi' a domenica, bucket vuoti inclusi. */
export function weekdayTotals(entries: ChartWorklogEntry[]) {
  const labels = ['Lunedi', 'Martedi', 'Mercoledi', 'Giovedi', 'Venerdi', 'Sabato', 'Domenica'];
  const totals = new Array(7).fill(0) as number[];

  entries.forEach((entry) => {
    const date = parseWorklogDay(entry.date);
    if (!date) return;
    totals[(date.getDay() + 6) % 7] += Math.max(0, entry.seconds);
  });

  return labels.map((label, index) => ({ key: label, label, seconds: totals[index] }));
}
