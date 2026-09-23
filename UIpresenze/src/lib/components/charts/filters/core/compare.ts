/**
 * Confronto di una voce scelta (una task, un contratto) con tutte le altre.
 *
 * Misure con unita' diverse (ore, euro, giorni) non stanno sullo stesso asse:
 * si confrontano come indice, con la media delle altre voci uguale a 100.
 * Tutto e' lineare nel numero di voci e si calcola solo quando c'e' una scelta.
 */
import type { ChartRow } from '../../chartData';
import { fmtInt } from '../../format';
import { ACCENT, NEUTRAL, SERIES } from '../../palette';

/** Colore della voce scelta: le altre restano in grigio di contesto. */
export const FOCUS_COLOR = SERIES[1];

export type CompareMetric = {
  id: string;
  label: string;
  value: number;
  /** Stessa misura sulle altre voci, la scelta esclusa. */
  others: number[];
  format: (value: number) => string;
};

export function mean(values: number[]) {
  return values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

export function median(values: number[]) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((first, second) => first - second);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

export type Standing = {
  /** 1 = la piu' alta. */
  rank: number;
  total: number;
  /** Quota delle altre voci che stanno sotto: 100 = sopra tutte. */
  percentile: number;
};

export function standing(value: number, others: number[]): Standing {
  const above = others.filter((other) => other > value).length;
  const below = others.filter((other) => other < value).length;
  return {
    rank: above + 1,
    total: others.length + 1,
    percentile: others.length > 0 ? (below / others.length) * 100 : 100
  };
}

/**
 * Righe dell'indice (media delle altre = 100). Le misure senza una media
 * positiva restano fuori: un indice su zero non dice niente.
 */
export function indexRows(metrics: CompareMetric[]): ChartRow[] {
  const rows = metrics
    .map((metric) => ({ metric, average: mean(metric.others) }))
    .filter(({ metric, average }) => average > 0 && Number.isFinite(metric.value));
  const total = rows.reduce((sum, { metric, average }) => sum + (metric.value / average) * 100, 0);

  return rows.map(({ metric, average }) => {
    const index = (Math.max(0, metric.value) / average) * 100;
    return {
      id: metric.id,
      label: metric.label,
      value: index,
      percent: total > 0 ? (index / total) * 100 : 0,
      display: fmtInt(index),
      color: ACCENT,
      hint: `${metric.format(metric.value)} contro media ${metric.format(average)} · mediana ${metric.format(median(metric.others))}`
    };
  });
}

/**
 * Classifica con la voce scelta evidenziata. Se la scelta e' fuori dalle prime
 * `max`, la si aggiunge in coda: deve vedersi sempre.
 */
export function highlightRows(rows: ChartRow[], focusId: string, max: number): ChartRow[] {
  const position = rows.findIndex((row) => row.id === focusId);
  const paint = (row: ChartRow, index: number): ChartRow => ({
    ...row,
    label: `#${index + 1} ${row.label}`,
    color: row.id === focusId ? FOCUS_COLOR : NEUTRAL
  });
  const head = rows.slice(0, max).map(paint);
  if (position < 0 || position < max) return head;
  return [...head.slice(0, Math.max(0, max - 1)), paint(rows[position], position)];
}
