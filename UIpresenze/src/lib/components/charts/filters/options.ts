/** Opzioni dei filtri calcolate sui dati gia' caricati nei grafici. */
import type { ChartsDataState } from '$lib/remo/chartsData';
import {
  isCmIssue,
  issueLoggedSeconds,
  issueProjectKey,
  issueProjectLabel,
  issueStatusLabel,
  issueTitle,
  issueTypeLabel
} from '../jiraSelectors';
import { clientName, parseDay } from '../contractsSelectors';
import { fmtHours, fmtInt } from '../format';
import type { JiraHistoryIssue } from '$lib/services/jira';
import type { FilterDef, FilterOption, FilterOptionSource } from './core/types';

/** Conta le occorrenze e ordina per frequenza: le voci piu' usate stanno in cima. */
function counted(items: { value: string; label: string }[], unit: string): FilterOption[] {
  const groups = new Map<string, { label: string; count: number }>();
  items.forEach((item) => {
    const current = groups.get(item.value);
    if (current) current.count += 1;
    else groups.set(item.value, { label: item.label, count: 1 });
  });
  return [...groups]
    .sort((first, second) => second[1].count - first[1].count || first[1].label.localeCompare(second[1].label))
    .map(([value, group]) => ({ value, label: group.label, hint: `${fmtInt(group.count)} ${unit}` }));
}

/** Issue con ore, dalla piu' pesante: e' l'ordine in cui di solito si cerca. */
function issueOptions(issues: JiraHistoryIssue[]): FilterOption[] {
  return issues
    .map((issue) => ({ issue, seconds: issueLoggedSeconds(issue) }))
    .filter((item) => item.seconds > 0)
    .sort((first, second) => second.seconds - first.seconds)
    .map(({ issue, seconds }) => ({
      value: issue.key,
      label: `${issue.key} · ${issueTitle(issue)}`,
      hint: fmtHours(seconds)
    }));
}

/** Anni in cui partono i contratti, dal piu' recente. */
function contractYears(data: ChartsDataState): FilterOption[] {
  const counts = new Map<number, number>();
  data.contratti.forEach((contract) => {
    const year = parseDay(contract.start_date)?.getFullYear();
    if (year !== undefined) counts.set(year, (counts.get(year) ?? 0) + 1);
  });
  return [...counts]
    .sort((first, second) => second[0] - first[0])
    .map(([year, count]) => ({ value: String(year), label: String(year), hint: `${fmtInt(count)} contratti` }));
}

export function sourceOptions(source: FilterOptionSource, data: ChartsDataState): FilterOption[] {
  switch (source) {
    case 'projects':
      return counted(
        data.issues.map((issue) => ({
          value: issueProjectKey(issue),
          label: `${issueProjectKey(issue)} · ${issueProjectLabel(issue)}`
        })),
        'issue'
      );
    case 'authors':
      return counted(
        data.worklogEntries.map((entry) => ({ value: entry.author, label: entry.author })),
        'worklog'
      );
    case 'issueTypes':
      return counted(
        data.issues.map((issue) => ({ value: issueTypeLabel(issue), label: issueTypeLabel(issue) })),
        'issue'
      );
    case 'statuses':
      return counted(
        data.issues.map((issue) => ({ value: issueStatusLabel(issue), label: issueStatusLabel(issue) })),
        'issue'
      );
    case 'clients':
      return counted(
        data.contratti.map((contract) => ({
          value: String(contract.client_id),
          label: clientName(contract)
        })),
        'contratti'
      );
    case 'issues':
      return issueOptions(data.issues);
    case 'cmIssues':
      return issueOptions(data.issues.filter((issue) => isCmIssue(issue)));
    case 'contracts':
      return data.contratti.map((contract) => ({
        value: String(contract.id),
        label: contract.contract_id,
        hint: clientName(contract)
      }));
    case 'contractYears':
      return contractYears(data);
  }
}

export function filterOptions(def: FilterDef, data: ChartsDataState): FilterOption[] {
  if (def.type === 'segmented') return def.options;
  if (def.type !== 'multiselect' && def.type !== 'select') return [];
  return def.source ? sourceOptions(def.source, data) : (def.options ?? []);
}
