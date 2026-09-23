/**
 * Elenco delle schermate con filtri. Ogni schermata ha la sua cartella con
 * `filters.json` (cosa mostra il pannello) e `apply.ts` (come si applica):
 * per aggiungere un filtro si toccano solo quei due file.
 */
import { cmTasksFilters } from './cmTasks/apply';
import { contrattiFilters } from './contratti/apply';
import { jiraHistoryFilters } from './jiraHistory/apply';
import { redditivitaFilters } from './redditivita/apply';
import type { FilterScreen } from './core/types';

export const FILTER_SCREENS = {
  jiraHistory: jiraHistoryFilters,
  contratti: contrattiFilters,
  redditivita: redditivitaFilters,
  cmTasks: cmTasksFilters
} as const;

const byId = new Map(Object.values(FILTER_SCREENS).map((screen) => [screen.id, screen]));

export function getFilterScreen(id: string | undefined): FilterScreen | undefined {
  return id ? byId.get(id) : undefined;
}
