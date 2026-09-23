/**
 * Meccanica comune alle schermate che leggono issue e worklog Jira.
 *
 * Non decide *quali* filtri applicare: riceve i predicati dalla schermata e si
 * occupa solo di tenere coerenti issue e worklog fra loro.
 */
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { ChartWorklogEntry } from '$lib/remo/chartsData';
import { issueLoggedSeconds } from '../../jiraSelectors';
import { inRange } from './primitives';
import type { NumberRange } from './types';

export type JiraSlice = { issues: JiraHistoryIssue[]; entries: ChartWorklogEntry[] };

export type JiraSliceRules = {
  issue: (issue: JiraHistoryIssue) => boolean;
  /** Assente = nessun filtro sul singolo worklog. */
  worklog?: (entry: ChartWorklogEntry) => boolean;
  /** Ore per issue, in ore, calcolate dopo gli altri filtri. */
  issueHours?: NumberRange;
};

/**
 * Le ore per persona delle issue non hanno una data: quando un filtro agisce sul
 * singolo worklog (periodo, giorno, autore) le si ricalcola dai worklog rimasti,
 * altrimenti le classifiche direbbero una cosa e l'andamento un'altra.
 */
export function sliceJira(
  issues: JiraHistoryIssue[],
  entries: ChartWorklogEntry[],
  rules: JiraSliceRules
): JiraSlice {
  const byIssue = issues.filter(rules.issue);
  let scoped = byIssue;

  if (rules.worklog) {
    const keep = rules.worklog;
    const keys = new Set(byIssue.map((issue) => issue.key));
    const authorsByIssue = new Map<string, Map<string, number>>();
    entries.forEach((entry) => {
      if (!keys.has(entry.issueKey) || !keep(entry)) return;
      const authors = authorsByIssue.get(entry.issueKey) ?? new Map<string, number>();
      authors.set(entry.author, (authors.get(entry.author) ?? 0) + Math.max(0, entry.seconds));
      authorsByIssue.set(entry.issueKey, authors);
    });

    scoped = byIssue
      .filter((issue) => authorsByIssue.has(issue.key))
      .map((issue) => ({
        ...issue,
        fields: {
          ...issue.fields,
          worklog_authors: [...(authorsByIssue.get(issue.key) ?? new Map())].map(
            ([displayName, timeSpentSeconds]) => ({ displayName, timeSpentSeconds })
          )
        }
      }));
  }

  const hours = rules.issueHours ?? { min: null, max: null };
  const kept = scoped.filter((issue) => inRange(hours, issueLoggedSeconds(issue), 3600));
  const keptKeys = new Set(kept.map((issue) => issue.key));

  return {
    issues: kept,
    entries: entries.filter(
      (entry) => keptKeys.has(entry.issueKey) && (!rules.worklog || rules.worklog(entry))
    )
  };
}
