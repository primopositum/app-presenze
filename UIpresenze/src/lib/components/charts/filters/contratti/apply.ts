/**
 * Filtri della schermata "Contratti". Gli id letti qui sono quelli di
 * `filters.json` nella stessa cartella.
 */
import type { ContrattoCliente } from '$lib/services/clienti';
import {
  clientName,
  contractCurrentValue,
  contractInitialValue,
  monthlyRate,
  parseDay
} from '../../contractsSelectors';
import { readDates, readList, readNumber, readRange, readText } from '../core/filterState';
import { compileRegex, inDates, inList, inRange, textMatches } from '../core/primitives';
import type { FilterScreen, FilterValues } from '../core/types';
import definition from './filters.json';

export const contrattiFilters = definition as FilterScreen;

export type ContractStatus = 'active' | 'upcoming' | 'expired';

export function contractStatus(contract: ContrattoCliente, referenceDate: Date): ContractStatus {
  const today = new Date(referenceDate.getFullYear(), referenceDate.getMonth(), referenceDate.getDate());
  const start = parseDay(contract.start_date);
  const end = parseDay(contract.end_date);
  if (start && start > today) return 'upcoming';
  if (end && end < today) return 'expired';
  return 'active';
}

function contractMatches(contract: ContrattoCliente, values: FilterValues, referenceDate: Date) {
  const billing = readText(values, 'billing');
  const pool = readText(values, 'pool');
  const endMode = readText(values, 'endMode');
  const pattern = compileRegex(readText(values, 'idPattern'));
  const recurring = monthlyRate(contract) > 0;
  const poolSize = (contract.pool_task || []).length;

  if (!inList(readList(values, 'clients'), String(contract.client_id))) return false;
  if (!inList(readList(values, 'status'), contractStatus(contract, referenceDate))) return false;
  if (billing === 'recurring' && !recurring) return false;
  if (billing === 'oneoff' && recurring) return false;
  if (pool === 'with' && poolSize === 0) return false;
  if (pool === 'without' && poolSize > 0) return false;
  if (endMode === 'fixed' && !contract.end_date) return false;
  if (endMode === 'open' && contract.end_date) return false;
  if (!textMatches(readText(values, 'search'), contract.contract_id, clientName(contract))) return false;
  if (pattern && !pattern.test(contract.contract_id)) return false;
  if (!inRange(readRange(values, 'currentValue'), contractCurrentValue(contract))) return false;
  if (!inRange(readRange(values, 'initialValue'), contractInitialValue(contract))) return false;
  if (!inRange(readRange(values, 'monthlyRate'), monthlyRate(contract))) return false;
  if (!inDates(readDates(values, 'startRange'), contract.start_date)) return false;
  if (!inDates(readDates(values, 'endRange'), contract.end_date)) return false;
  return true;
}

export function applyContrattiFilters(
  contracts: ContrattoCliente[],
  values: FilterValues,
  referenceDate: Date
) {
  return contracts.filter((contract) => contractMatches(contract, values, referenceDate));
}

export type ContrattiDisplayDefaults = {
  referenceDate: Date;
  expiringDays: number;
  forecastMonths: number;
  topCount: number;
};

/** Impostazioni di visualizzazione: i campi vuoti ricadono sulle prop della schermata. */
export function contrattiDisplay(values: FilterValues, defaults: ContrattiDisplayDefaults) {
  return {
    referenceDate: parseDay(readText(values, 'referenceDate')) ?? defaults.referenceDate,
    expiringDays: readNumber(values, 'expiringDays') ?? defaults.expiringDays,
    forecastMonths: Math.min(36, Math.max(1, readNumber(values, 'forecastMonths') ?? defaults.forecastMonths)),
    topCount: readNumber(values, 'topCount') ?? defaults.topCount,
    expiryHorizon: readNumber(values, 'expiryHorizon') ?? 365,
    // Oltre gli otto spicchi la palette non distingue piu' le tinte adiacenti.
    donutSlices: Math.min(8, Math.max(2, readNumber(values, 'donutSlices') ?? 6)),
    /** Id del contratto da confrontare; vuoto = nessun confronto. */
    compareId: readText(values, 'compareContract')
  };
}
