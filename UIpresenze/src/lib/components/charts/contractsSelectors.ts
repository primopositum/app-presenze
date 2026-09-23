/** Trasformazioni pure dei contratti commerciali nei dati per i grafici. */
import type { ContrattoCliente } from '$lib/services/clienti';
import type { ChartPoolTask } from '$lib/remo/chartsData';
import { addGrouped, buildChartRows, type ChartGroups, type ChartRow } from './chartData';
import { fmtEuro, fmtDays, fmtHours, fmtMonth, fmtRate } from './format';
import { ACCENT, STATUS } from './palette';

export type ContractsSummary = {
  active: ContrattoCliente[];
  expiring: ContrattoCliente[];
  initialValue: number;
  currentValue: number;
  accruedValue: number;
  monthlyRecurring: number;
};

const DAY_MS = 24 * 60 * 60 * 1000;

export function toNumber(value: unknown) {
  const text = String(value ?? '').trim();
  const result = Number(text);
  return text && Number.isFinite(result) ? result : 0;
}

/** Le date del backend sono YYYY-MM-DD: le interpretiamo sempre nel fuso locale. */
export function parseDay(value: string | null | undefined) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayStart(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function daysBetween(start: Date, end: Date) {
  return Math.round((dayStart(end).getTime() - dayStart(start).getTime()) / DAY_MS);
}

/** Valore maturato: `current_value` quando c'e', altrimenti il valore firmato. */
export function contractCurrentValue(contract: ContrattoCliente) {
  const currentText = String(contract.current_value ?? '').trim();
  return currentText ? toNumber(currentText) : toNumber(contract.value);
}

export function contractInitialValue(contract: ContrattoCliente) {
  return toNumber(contract.value);
}

export function clientName(contract: ContrattoCliente) {
  return contract.client?.nome || 'Cliente non disponibile';
}

export function isActive(contract: ContrattoCliente, referenceDate: Date) {
  const today = dayStart(referenceDate);
  const start = parseDay(contract.start_date);
  const end = parseDay(contract.end_date);
  return (!start || start <= today) && (!end || end >= today);
}

/** Canone mensile normalizzato a 30 giorni; i contratti una tantum valgono zero. */
export function monthlyRate(contract: ContrattoCliente) {
  const periodicity = contract.periodicity;
  if (!periodicity || periodicity.period_days <= 0) return 0;
  return (toNumber(periodicity.periodic_value) * 30) / periodicity.period_days;
}

export function contractsSummary(
  contracts: ContrattoCliente[],
  referenceDate: Date,
  expiringDays = 90
): ContractsSummary {
  const active = contracts.filter((contract) => isActive(contract, referenceDate));
  const initialValue = contracts.reduce(
    (total, contract) => total + contractInitialValue(contract),
    0
  );
  const currentValue = contracts.reduce(
    (total, contract) => total + contractCurrentValue(contract),
    0
  );
  return {
    active,
    expiring: active.filter((contract) => {
      const end = parseDay(contract.end_date);
      if (end === null) return false;
      const remaining = daysBetween(referenceDate, end);
      return remaining >= 0 && remaining <= expiringDays;
    }),
    initialValue,
    currentValue,
    accruedValue: currentValue - initialValue,
    monthlyRecurring: active.reduce((total, contract) => total + monthlyRate(contract), 0)
  };
}

/**
 * Valore maturato per contratto: una sola serie, quindi una sola tinta.
 * Il valore iniziale non sta sullo stesso grafico: e' una misura diversa e
 * affiancarla raddoppia le barre senza aggiungere una lettura.
 */
export function contractValueRows(contracts: ContrattoCliente[]): ChartRow[] {
  const groups: ChartGroups = {};
  const hints: Record<string, string> = {};

  contracts.forEach((contract) => {
    const id = String(contract.id);
    addGrouped(groups, id, contract.contract_id, contractCurrentValue(contract));
    hints[id] = clientName(contract);
  });

  return buildChartRows(groups, { format: fmtEuro, hintOf: (id) => hints[id] });
}

export function clientValueRows(contracts: ContrattoCliente[]): ChartRow[] {
  const groups: ChartGroups = {};
  contracts.forEach((contract) =>
    addGrouped(groups, String(contract.client_id), clientName(contract), contractCurrentValue(contract))
  );
  return buildChartRows(groups, { format: fmtEuro, palette: 'identity' });
}

export function clientMonthlyRows(contracts: ContrattoCliente[]): ChartRow[] {
  const groups: ChartGroups = {};
  contracts.forEach((contract) =>
    addGrouped(groups, String(contract.client_id), clientName(contract), monthlyRate(contract))
  );
  return buildChartRows(groups, { format: fmtEuro });
}

export type ForecastPoint = { key: string; label: string; value: number };

/** Incassi ricorrenti stimati per ciascuno dei prossimi mesi. */
export function forecastPoints(
  contracts: ContrattoCliente[],
  from: Date,
  months = 12
): ForecastPoint[] {
  const start = dayStart(from);
  const buckets = Array.from({ length: Math.max(1, months) }, (_, offset) => {
    const monthStart = new Date(start.getFullYear(), start.getMonth() + offset, 1);
    return {
      key: `${monthStart.getFullYear()}-${String(monthStart.getMonth() + 1).padStart(2, '0')}`,
      label: fmtMonth(monthStart),
      start: monthStart,
      end: new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0),
      value: 0
    };
  });

  contracts.forEach((contract) => {
    const periodicity = contract.periodicity;
    const firstMeeting = parseDay(periodicity?.first_meeting_date);
    const contractStart = parseDay(contract.start_date);
    const contractEnd = parseDay(contract.end_date);
    const periodDays = Number(periodicity?.period_days || 0);
    const periodicValue = toNumber(periodicity?.periodic_value);
    if (!firstMeeting || periodDays <= 0 || periodicValue <= 0) return;

    buckets.forEach((bucket) => {
      const windowStart = bucket.start < start ? start : bucket.start;
      const windowEnd = contractEnd && contractEnd < bucket.end ? contractEnd : bucket.end;
      if (contractStart && windowEnd < contractStart) return;
      if (windowEnd < windowStart) return;

      const firstValidDay = contractStart && contractStart > windowStart ? contractStart : windowStart;
      const offset = Math.max(0, Math.ceil(daysBetween(firstMeeting, firstValidDay) / periodDays));
      const occurrence = new Date(
        firstMeeting.getFullYear(),
        firstMeeting.getMonth(),
        firstMeeting.getDate() + offset * periodDays
      );
      for (
        let due = occurrence;
        due <= windowEnd;
        due = new Date(due.getFullYear(), due.getMonth(), due.getDate() + periodDays)
      ) {
        if (due >= firstValidDay) bucket.value += periodicValue;
      }
    });
  });

  return buckets.map(({ key, label, value }) => ({ key, label, value }));
}

/**
 * Giorni che mancano alla scadenza, dal piu' urgente.
 * Il colore qui significa uno stato (sotto i 30 giorni, sotto i 90): resta
 * appaiato al numero di giorni, non e' mai l'unico segnale.
 */
export function expiryRows(
  contracts: ContrattoCliente[],
  referenceDate: Date,
  horizonDays = 365
): ChartRow[] {
  const rows = contracts
    .map((contract) => {
      const end = parseDay(contract.end_date);
      return end ? { contract, remaining: daysBetween(referenceDate, end), end } : null;
    })
    .filter((row): row is { contract: ContrattoCliente; remaining: number; end: Date } => row !== null)
    .filter((row) => row.remaining >= 0 && row.remaining <= horizonDays)
    .sort((first, second) => first.remaining - second.remaining);

  const total = rows.reduce((sum, row) => sum + row.remaining, 0);

  return rows.map((row) => ({
    id: String(row.contract.id),
    label: row.contract.contract_id,
    value: row.remaining,
    percent: total > 0 ? (row.remaining / total) * 100 : 0,
    display: fmtDays(row.remaining),
    color: row.remaining <= 30 ? STATUS.critical : row.remaining <= 90 ? STATUS.warning : ACCENT,
    hint: `${clientName(row.contract)} · scade il ${row.contract.end_date}`
  }));
}

/* -------------------------------------------------------------------------- */
/* Redditivita': incrocio fra contratti e ore Jira delle task del pool         */
/* -------------------------------------------------------------------------- */

export type PoolTaskRow = {
  key: string;
  summary: string;
  seconds: number;
  /** false quando la task del pool non ha worklog nel periodo selezionato. */
  found: boolean;
  /** Tariffa oraria del contratto: e' la stessa per tutte le sue task. */
  hourlyRate: number;
  /** Quota del valore del contratto attribuita alla task. */
  share: number;
};

export type ContractProfitability = {
  id: number;
  contractId: string;
  clientName: string;
  /** Valore maturato del contratto. */
  value: number;
  seconds: number;
  hours: number;
  /** Valore maturato diviso le ore loggate sulle task del pool. */
  hourlyRate: number;
  poolSize: number;
  /** Task del pool senza ore nel periodo: la tariffa le ignora. */
  missingTasks: number;
  tasks: PoolTaskRow[];
};

export function tasksByKey(tasks: ChartPoolTask[]) {
  return new Map(tasks.map((task) => [task.key.trim().toUpperCase(), task]));
}

/**
 * Ore e quote di valore delle task del pool di un contratto.
 * E' il calcolo che alimenta sia il dettaglio contratto sia i grafici di
 * redditivita': sta qui una volta sola.
 */
export function contractProfitability(
  contract: ContrattoCliente,
  pool: Map<string, ChartPoolTask>
): ContractProfitability {
  const value = contractCurrentValue(contract);
  const entries = (contract.pool_task || []).map((taskKey) => {
    const task = pool.get(taskKey.trim().toUpperCase());
    return {
      key: taskKey,
      summary: task?.summary || 'Task non presente nei worklog del periodo',
      seconds: Math.max(0, Number(task?.seconds || 0)),
      found: Boolean(task)
    };
  });

  const seconds = entries.reduce((total, entry) => total + entry.seconds, 0);
  const hours = seconds / 3600;
  const hourlyRate = hours > 0 ? value / hours : 0;

  return {
    id: contract.id,
    contractId: contract.contract_id,
    clientName: clientName(contract),
    value,
    seconds,
    hours,
    hourlyRate,
    poolSize: entries.length,
    missingTasks: entries.filter((entry) => !entry.found).length,
    tasks: entries.map((entry) => ({
      ...entry,
      hourlyRate,
      share: seconds > 0 ? (value / seconds) * entry.seconds : 0
    }))
  };
}

/** Solo i contratti su cui e' stata loggata almeno un'ora nel periodo. */
export function profitabilityList(
  contracts: ContrattoCliente[],
  pool: Map<string, ChartPoolTask>
): ContractProfitability[] {
  return contracts
    .map((contract) => contractProfitability(contract, pool))
    .filter((row) => row.seconds > 0)
    .sort((first, second) => second.hourlyRate - first.hourlyRate);
}

/** Tariffa oraria effettiva per contratto. */
export function hourlyRateRows(list: ContractProfitability[]): ChartRow[] {
  const total = list.reduce((sum, row) => sum + row.hourlyRate, 0);
  return list.map((row) => ({
    id: String(row.id),
    label: row.contractId,
    value: row.hourlyRate,
    percent: total > 0 ? (row.hourlyRate / total) * 100 : 0,
    display: fmtRate(row.hourlyRate),
    color: ACCENT,
    hint: `${row.clientName} · ${fmtEuro(row.value)} su ${fmtHours(row.seconds)}`
  }));
}

/** Ore loggate sulle task del pool, per contratto. */
export function contractHoursRows(list: ContractProfitability[]): ChartRow[] {
  const groups: ChartGroups = {};
  const hints: Record<string, string> = {};

  list.forEach((row) => {
    const id = String(row.id);
    addGrouped(groups, id, row.contractId, row.seconds);
    hints[id] = `${row.clientName} · ${row.poolSize} task nel pool`;
  });

  return buildChartRows(groups, { format: fmtHours, hintOf: (id) => hints[id] });
}

/** Valore generato dalle singole task del pool, su tutti i contratti. */
export function taskValueRows(list: ContractProfitability[]): ChartRow[] {
  const groups: ChartGroups = {};
  const hints: Record<string, string> = {};

  list.forEach((contract) =>
    contract.tasks.forEach((task) => {
      addGrouped(groups, task.key, task.key, task.share);
      hints[task.key] = `${contract.contractId} · ${fmtHours(task.seconds)} · ${task.summary}`;
    })
  );

  return buildChartRows(groups, { format: fmtEuro, hintOf: (id) => hints[id] });
}

/** Media ponderata: il valore totale diviso le ore totali, non la media delle tariffe. */
export function blendedHourlyRate(list: ContractProfitability[]) {
  const hours = list.reduce((total, row) => total + row.hours, 0);
  const value = list.reduce((total, row) => total + row.value, 0);
  return hours > 0 ? value / hours : 0;
}
