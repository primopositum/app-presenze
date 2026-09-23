/**
 * Filtri della schermata "Task CM". Gli id letti qui sono quelli di
 * `filters.json` nella stessa cartella: non dipendono da quelli di "Ore Jira".
 */
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import {
  isCmIssue,
  issueLoggedSeconds,
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
import { sliceJira } from '../core/jiraSlice';
import type { FilterScreen, FilterValues } from '../core/types';
import definition from './filters.json';

export const cmTasksFilters = definition as FilterScreen;

/** Marcatore scelto nel pannello; quello di default quando il campo e' vuoto. */
export function cmMarker(values: FilterValues, fallback: string) {
  return readText(values, 'marker').trim().toUpperCase() || fallback;
}

/** Il marcatore puo' essere cercato solo nella chiave della issue o solo nel progetto. */
function matchesMarker(issue: JiraHistoryIssue, marker: string, scope: string) {
  if (scope === 'issue') return String(issue.key || '').split('-')[0].toUpperCase().includes(marker);
  if (scope === 'project') return issueProjectKey(issue).toUpperCase().includes(marker);
  return isCmIssue(issue, marker);
}

function issueMatches(issue: JiraHistoryIssue, values: FilterValues) {
  const resolution = readText(values, 'resolution');
  const pattern = compileRegex(readText(values, 'keyPattern'));
  const resolved = Boolean(issue.fields?.resolutiondate);

  if (!inList(readList(values, 'projects'), issueProjectKey(issue))) return false;
  if (!inList(readList(values, 'issueTypes'), issueTypeLabel(issue))) return false;
  if (!inList(readList(values, 'statuses'), issueStatusLabel(issue))) return false;
  if (resolution === 'open' && resolved) return false;
  if (resolution === 'resolved' && !resolved) return false;
  if (!textMatches(readText(values, 'search'), issue.key, issueTitle(issue))) return false;
  if (pattern && !pattern.test(issue.key)) return false;
  if (keyList(readText(values, 'excludeKeys')).has(String(issue.key).toUpperCase())) return false;
  if (!inDates(readDates(values, 'createdRange'), issue.fields?.created)) return false;
  if (!inDates(readDates(values, 'updatedRange'), issue.fields?.updated)) return false;
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

/**
 * Task CM filtrate e ore del periodo su cui calcolare la quota.
 * La quota puo' stare su tutte le ore caricate o solo su quelle che passano
 * i filtri di periodo e persona: lo sceglie `shareBase`.
 */
export function applyCmFilters(
  issues: JiraHistoryIssue[],
  entries: ChartWorklogEntry[],
  values: FilterValues,
  defaultMarker: string
) {
  const marker = cmMarker(values, defaultMarker);
  const scope = readText(values, 'markerScope');
  const worklog = worklogRule(values);
  const scoped = sliceJira(issues, entries, {
    issue: (issue) => issueMatches(issue, values),
    worklog
  });
  const hours = readRange(values, 'issueHours');
  const cmIssues = scoped.issues.filter(
    (issue) =>
      matchesMarker(issue, marker, scope) && inRange(hours, issueLoggedSeconds(issue), 3600)
  );
  const cmKeys = new Set(cmIssues.map((issue) => issue.key));
  const shareIssues = readText(values, 'shareBase') === 'filtered' ? scoped.issues : issues;

  return {
    marker,
    issues: cmIssues,
    entries: scoped.entries.filter((entry) => cmKeys.has(entry.issueKey)),
    periodSeconds: shareIssues.reduce((total, issue) => total + issueLoggedSeconds(issue), 0)
  };
}

export function cmTasksDisplay(values: FilterValues, defaults: { topCount: number }) {
  return {
    topCount: readNumber(values, 'topCount') ?? defaults.topCount,
    bucket: (readText(values, 'bucket') || 'auto') as TimelineBucket | 'auto',
    /** Chiave della task da confrontare; vuota = nessun confronto. */
    compareKey: readText(values, 'compareIssue')
  };
}
