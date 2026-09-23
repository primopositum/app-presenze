/**
 * Confronto di un contratto con gli altri della schermata "Contratti".
 *
 * Il contratto scelto si cerca fra tutti, anche se i filtri lo escludono: il
 * suo valore non dipende dal periodo. Il termine di confronto sono invece i
 * contratti che passano i filtri, lui escluso.
 */
import type { ContrattoCliente } from '$lib/services/clienti';
import { fmtDays, fmtEuro, fmtInt } from '../../format';
import {
  clientName,
  contractCurrentValue,
  contractInitialValue,
  contractValueRows,
  forecastPoints,
  monthlyRate,
  parseDay
} from '../../contractsSelectors';
import { highlightRows, indexRows, mean, standing, type CompareMetric } from '../core/compare';
import { contractStatus } from './apply';

const DAY_MS = 86_400_000;

function durationDays(contract: ContrattoCliente) {
  const start = parseDay(contract.start_date);
  const end = parseDay(contract.end_date);
  return start && end ? Math.max(0, Math.round((end.getTime() - start.getTime()) / DAY_MS)) : 0;
}

function forecastTotal(contract: ContrattoCliente, from: Date, months: number) {
  return forecastPoints([contract], from, months).reduce((sum, point) => sum + point.value, 0);
}

const STATUS_LABEL = { active: 'Attivo', upcoming: 'Futuro', expired: 'Scaduto' } as const;

export type ContractComparison = NonNullable<ReturnType<typeof compareContract>>;

export function compareContract(
  allContracts: ContrattoCliente[],
  scope: ContrattoCliente[],
  focusId: string,
  options: { referenceDate: Date; forecastMonths: number; topCount: number }
) {
  const focus = allContracts.find((contract) => String(contract.id) === focusId);
  if (!focus) return null;

  const others = scope.filter((contract) => contract.id !== focus.id);
  const { referenceDate, forecastMonths } = options;
  const measure = (read: (contract: ContrattoCliente) => number) => ({
    value: read(focus),
    others: others.map(read)
  });
  const forecastOf = (contract: ContrattoCliente) => forecastTotal(contract, referenceDate, forecastMonths);

  const metrics: CompareMetric[] = [
    { id: 'current', label: 'Valore maturato', ...measure(contractCurrentValue), format: fmtEuro },
    { id: 'initial', label: 'Valore firmato', ...measure(contractInitialValue), format: fmtEuro },
    { id: 'monthly', label: 'Canone mensile', ...measure(monthlyRate), format: fmtEuro },
    { id: 'forecast', label: `Incassi previsti ${forecastMonths} mesi`, ...measure(forecastOf), format: fmtEuro },
    { id: 'duration', label: 'Durata', ...measure(durationDays), format: fmtDays },
    { id: 'pool', label: 'Task nel pool', ...measure((c) => (c.pool_task || []).length), format: fmtInt }
  ];

  const current = measure(contractCurrentValue);
  const scopeTotal = current.others.reduce((sum, value) => sum + value, current.value);
  const end = parseDay(focus.end_date);
  // Il contratto scelto entra sempre in classifica, anche se i filtri lo escludono.
  const rankingScope = [focus, ...others];

  return {
    id: String(focus.id),
    label: focus.contract_id,
    client: clientName(focus),
    status: STATUS_LABEL[contractStatus(focus, referenceDate)],
    inScope: scope.some((contract) => contract.id === focus.id),
    others: others.length,
    standing: standing(current.value, current.others),
    share: scopeTotal > 0 ? current.value / scopeTotal : 0,
    value: current.value,
    averageValue: mean(current.others),
    daysLeft: end ? Math.round((end.getTime() - referenceDate.getTime()) / DAY_MS) : null,
    index: indexRows(metrics),
    ranking: highlightRows(contractValueRows(rankingScope), String(focus.id), options.topCount),
    forecast: forecastPoints([focus], referenceDate, forecastMonths)
  };
}
