/**
 * Filtri della schermata "Redditivita'". Gli id letti qui sono quelli di
 * `filters.json` nella stessa cartella.
 */
import type { ContrattoCliente } from '$lib/services/clienti';
import { blendedHourlyRate, type ContractProfitability } from '../../contractsSelectors';
import { readList, readNumber, readRange, readText } from '../core/filterState';
import { compileRegex, inList, inRange, textMatches } from '../core/primitives';
import type { FilterScreen, FilterValues } from '../core/types';
import definition from './filters.json';

export const redditivitaFilters = definition as FilterScreen;

function rowMatches(row: ContractProfitability, values: FilterValues, averageRate: number) {
  const position = readText(values, 'position');
  const coverage = readNumber(values, 'coverage');
  const minPool = readNumber(values, 'minPoolSize');
  const pattern = compileRegex(readText(values, 'idPattern'));
  const covered = row.poolSize > 0 ? ((row.poolSize - row.missingTasks) / row.poolSize) * 100 : 0;

  if (!textMatches(readText(values, 'search'), row.contractId, row.clientName)) return false;
  if (pattern && !pattern.test(row.contractId)) return false;
  if (!inRange(readRange(values, 'hourlyRate'), row.hourlyRate)) return false;
  if (!inRange(readRange(values, 'hours'), row.hours)) return false;
  if (!inRange(readRange(values, 'value'), row.value)) return false;
  if (coverage !== null && covered < coverage) return false;
  if (minPool !== null && row.poolSize < minPool) return false;
  if (position === 'above' && row.hourlyRate < averageRate) return false;
  if (position === 'below' && row.hourlyRate >= averageRate) return false;
  return true;
}

/**
 * Righe di redditivita' filtrate e tariffa media di confronto.
 *
 * Il cliente sta sul contratto, non sulla riga: si filtra prima. La media
 * decide "sopra / sotto" e la linea di riferimento; `averageScope` sceglie se
 * calcolarla su tutti i contratti o solo su quelli filtrati.
 */
export function applyRedditivitaFilters(
  contracts: ContrattoCliente[],
  list: ContractProfitability[],
  values: FilterValues
) {
  const clients = readList(values, 'clients');
  const allowed = new Set(
    contracts
      .filter((contract) => inList(clients, String(contract.client_id)))
      .map((contract) => contract.id)
  );
  const byClient = list.filter((row) => allowed.has(row.id));
  const onFiltered = readText(values, 'averageScope') === 'filtered';
  const referenceRate = blendedHourlyRate(onFiltered ? byClient : list);

  const taskHours = readRange(values, 'taskHours');
  const filterTasks = taskHours.min !== null || taskHours.max !== null;
  const rows = byClient
    .filter((row) => rowMatches(row, values, referenceRate))
    .map((row) =>
      filterTasks
        ? { ...row, tasks: row.tasks.filter((task) => inRange(taskHours, task.seconds, 3600)) }
        : row
    );

  return {
    list: rows,
    averageRate: onFiltered ? blendedHourlyRate(rows) : referenceRate
  };
}

export function redditivitaDisplay(values: FilterValues) {
  return {
    /** Id del contratto da confrontare; vuoto = nessun confronto. */
    compareId: readText(values, 'compareContract')
  };
}
