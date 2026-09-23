/**
 * Confronto della redditivita' di un contratto con quella degli altri.
 *
 * Il contratto scelto deve avere ore sul pool nel periodo: senza, la tariffa
 * oraria non esiste e non c'e' niente da confrontare.
 */
import { buildChartRows, type ChartGroups } from '../../chartData';
import { fmtEuro, fmtHours, fmtInt, fmtPercent, fmtRate } from '../../format';
import { hourlyRateRows, type ContractProfitability } from '../../contractsSelectors';
import { SERIES } from '../../palette';
import { highlightRows, indexRows, standing, type CompareMetric } from '../core/compare';

const coverage = (row: ContractProfitability) =>
  row.poolSize > 0 ? ((row.poolSize - row.missingTasks) / row.poolSize) * 100 : 0;
const valuePerTask = (row: ContractProfitability) => (row.poolSize > 0 ? row.value / row.poolSize : 0);

export type ProfitabilityComparison = NonNullable<ReturnType<typeof compareProfitability>>;

export function compareProfitability(
  fullList: ContractProfitability[],
  scope: ContractProfitability[],
  focusId: string,
  options: { averageRate: number; topCount: number }
) {
  const focus = fullList.find((row) => String(row.id) === focusId);
  if (!focus) return null;

  const others = scope.filter((row) => row.id !== focus.id);
  const measure = (read: (row: ContractProfitability) => number) => ({
    value: read(focus),
    others: others.map(read)
  });

  const metrics: CompareMetric[] = [
    { id: 'rate', label: 'Tariffa oraria', ...measure((row) => row.hourlyRate), format: fmtRate },
    { id: 'hours', label: 'Ore sul pool', ...measure((row) => row.seconds), format: fmtHours },
    { id: 'value', label: 'Valore maturato', ...measure((row) => row.value), format: fmtEuro },
    { id: 'pool', label: 'Task nel pool', ...measure((row) => row.poolSize), format: fmtInt },
    { id: 'coverage', label: 'Copertura del pool', ...measure(coverage), format: (v) => fmtPercent(v, 0) },
    { id: 'perTask', label: 'Valore per task', ...measure(valuePerTask), format: fmtEuro }
  ];

  const tasks: ChartGroups = {};
  focus.tasks.forEach((task) => {
    tasks[task.key] = { label: `${task.key} · ${task.summary}`, value: task.seconds };
  });

  const rate = measure((row) => row.hourlyRate);

  return {
    id: String(focus.id),
    label: focus.contractId,
    client: focus.clientName,
    inScope: scope.some((row) => row.id === focus.id),
    others: others.length,
    standing: standing(rate.value, rate.others),
    hourlyRate: focus.hourlyRate,
    /** Scarto dalla media di confronto, in €/h e in percentuale. */
    gap: focus.hourlyRate - options.averageRate,
    gapPercent: options.averageRate > 0 ? ((focus.hourlyRate - options.averageRate) / options.averageRate) * 100 : 0,
    missingTasks: focus.missingTasks,
    index: indexRows(metrics),
    ranking: highlightRows(hourlyRateRows([focus, ...others].sort((a, b) => b.hourlyRate - a.hourlyRate)), String(focus.id), options.topCount),
    tasks: buildChartRows(tasks, { format: fmtHours, color: SERIES[2] })
  };
}
