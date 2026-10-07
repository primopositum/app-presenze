/**
 * Filtri della schermata "Ore Jira". Gli id letti qui sono quelli di
 * `filters.json` nella stessa cartella.
 */
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import {
  issueProjectKey,
  issueStatusLabel,
  issueTitle,
  issueTypeLabel,
  type TimelineBucket
} from '../../jiraSelectors';
import {
  readBool,
  readDates,
  readList,
  readNumber,
  readRange,
  readText
} from '../core/filterState';
import {
  compileRegex,
  inDates,
  inList,
  inRange,
  keyList,
  textMatches,
  weekdayOf
} from '../core/primitives';
import { sliceJira, type JiraSlice } from '../core/jiraSlice';
import type { FilterScreen, FilterValues } from '../core/types';
import definition from './filters.json';

export const jiraHistoryFilters = definition as FilterScreen;

function issueMatches(issue: JiraHistoryIssue, values: FilterValues) {
  const hierarchy = readText(values, 'hierarchy');
  const resolution = readText(values, 'resolution');
  const pattern = compileRegex(readText(values, 'keyPattern'));
  const fields = issue.fields;
  const isSubtask = Boolean(fields?.issuetype?.subtask);
  const resolved = Boolean(fields?.resolutiondate);

  if (!inList(readList(values, 'projects'), issueProjectKey(issue))) return false;
  if (!inList(readList(values, 'issueTypes'), issueTypeLabel(issue))) return false;
  if (!inList(readList(values, 'statuses'), issueStatusLabel(issue))) return false;
  if (hierarchy === 'task' && isSubtask) return false;
  if (hierarchy === 'subtask' && !isSubtask) return false;
  if (resolution === 'open' && resolved) return false;
  if (resolution === 'resolved' && !resolved) return false;
  if (!textMatches(readText(values, 'search'), issue.key, issueTitle(issue))) return false;
  if (pattern && !pattern.test(issue.key)) return false;
  if (keyList(readText(values, 'excludeKeys')).has(String(issue.key).toUpperCase())) return false;
  if (!inDates(readDates(values, 'createdRange'), fields?.created)) return false;
  if (!inDates(readDates(values, 'updatedRange'), fields?.updated)) return false;
  return true;
}

function worklogRule(values: FilterValues) {
  const period = readDates(values, 'period');
  const weekdays = readList(values, 'weekdays');
  const authors = readList(values, 'authors');
  const hideUnassigned = readBool(values, 'hideUnassigned');
  const minutes = readRange(values, 'worklogMinutes');
  const active =
    period.from ||
    period.to ||
    weekdays.length > 0 ||
    authors.length > 0 ||
    hideUnassigned ||
    minutes.min !== null ||
    minutes.max !== null;
  if (!active) return undefined;

  return (entry: ChartWorklogEntry) =>
    inDates(period, entry.date) &&
    inList(weekdays, String(weekdayOf(entry.date))) &&
    inList(authors, entry.author) &&
    !(hideUnassigned && entry.author === 'Non assegnato') &&
    inRange(minutes, entry.seconds, 60);
}

/** Issue e worklog della schermata, dopo la selezione di sinistra e il pannello. */
export function applyJiraHistoryFilters(
  issues: JiraHistoryIssue[],
  entries: ChartWorklogEntry[],
  values: FilterValues
): JiraSlice {
  return sliceJira(issues, entries, {
    issue: (issue) => issueMatches(issue, values),
    worklog: worklogRule(values),
    issueHours: readRange(values, 'issueHours')
  });
}


export function jiraHistoryDisplay(values: FilterValues, defaults: { topCount: number }) {
  return {
    topCount: readNumber(values, 'topCount') ?? defaults.topCount,
    bucket: (readText(values, 'bucket') || 'auto') as TimelineBucket | 'auto',
    /** Chiave della task da confrontare; vuota = nessun confronto. */
    compareKey: readText(values, 'compareIssue')
  };
}
