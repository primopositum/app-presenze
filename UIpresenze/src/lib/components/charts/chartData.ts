/**
 * Righe dei grafici e geometria delle barre.
 *
 * Funzioni pure: non conoscono ne' Svelte ne' il dominio, prendono numeri e
 * restituiscono righe pronte per BarChart / DonutPanel.
 */
import { area, curveMonotoneX, descending, line, scaleBand, scaleLinear } from 'd3';
import { ACCENT, NEUTRAL, seriesColor } from './palette';
import { BAR_SIZING, estimateTextWidth, truncateToWidth, type BarSizing } from './chartSizing';

export type ChartRow = {
  id: string;
  label: string;
  /** Valore grezzo: secondi, euro, euro/ora... lo decide chi costruisce le righe. */
  value: number;
  percent: number;
  /** Valore gia' formattato per tooltip, legenda ed etichette. */
  display: string;
  color: string;
  /** Seconda riga del tooltip: contesto, non un altro asse. */
  hint?: string;
};

export type ChartGroups = Record<string, { label: string; value: number }>;

/**
 * Come si assegna il colore alle righe.
 * - `single`   una sola serie, un solo colore: e' il default dei grafici di magnitudine;
 * - `identity` scala categorica: solo quando le voci *sono* il soggetto (ciambelle, legende);
 * - `fixed`    il colore arriva gia' deciso da chi costruisce le righe (stato, evidenza).
 */
export type RowPalette = 'single' | 'identity' | 'fixed';

export type BuildRowsOptions = {
  format?: (value: number) => string;
  palette?: RowPalette;
  /** Tinta dei grafici a serie singola. */
  color?: string;
  /** Tiene anche le voci a zero (utile per gli assi temporali). */
  keepZero?: boolean;
  /** Colore per riga, quando `palette` e' `fixed`. */
  colorOf?: (id: string, index: number) => string;
  hintOf?: (id: string) => string | undefined;
};

/** Somma un valore nel gruppo `id`, creandolo se manca. */
export function addGrouped(groups: ChartGroups, id: string, label: string, value: number) {
  if (!groups[id]) groups[id] = { label, value: 0 };
  groups[id].value += Math.max(0, Number(value || 0));
}

export function buildChartRows(groups: ChartGroups, options: BuildRowsOptions = {}): ChartRow[] {
  const {
    format = (value: number) => String(Math.round(value)),
    palette = 'single',
    color = ACCENT,
    keepZero = false,
    colorOf,
    hintOf
  } = options;

  const total = Object.values(groups).reduce((sum, group) => sum + group.value, 0);

  return Object.entries(groups)
    .map(([id, group]) => ({ id, ...group }))
    .filter((group) => keepZero || group.value > 0)
    .sort((first, second) => descending(first.value, second.value))
    .map((group, index) => ({
      id: group.id,
      label: group.label,
      value: group.value,
      percent: total > 0 ? (group.value / total) * 100 : 0,
      display: format(group.value),
      color:
        palette === 'identity'
          ? seriesColor(index)
          : palette === 'fixed'
            ? (colorOf?.(group.id, index) ?? color)
            : color,
      hint: hintOf?.(group.id)
    }));
}

export function totalOf(rows: ChartRow[]) {
  return rows.reduce((sum, row) => sum + row.value, 0);
}

/**
 * Tiene le prime `max` righe e ripiega la coda su una voce "Altri".
 * Serve alle ciambelle: oltre i sei spicchi due tinte adiacenti non si distinguono piu'.
 */
export function withOther(
  rows: ChartRow[],
  max = 6,
  format: (value: number) => string = (value) => String(Math.round(value)),
  label = 'Altri'
): ChartRow[] {
  if (rows.length <= max) return rows;

  const head = rows.slice(0, max - 1);
  const tail = rows.slice(max - 1);
  const value = totalOf(tail);

  return [
    ...head,
    {
      id: '__other__',
      label: `${label} (${tail.length})`,
      value,
      percent: tail.reduce((sum, row) => sum + row.percent, 0),
      display: format(value),
      color: NEUTRAL,
      hint: tail
        .slice(0, 4)
        .map((row) => row.label)
        .join(', ')
    }
  ];
}

/** Prime `max` righe di una classifica: il resto resta leggibile nel dettaglio. */
export function topRows(rows: ChartRow[], max: number) {
  return rows.length > max ? rows.slice(0, max) : rows;
}

/** Tacche "tonde" su cui appoggiare la griglia. */
export function niceTicks(maxValue: number, count = 4): number[] {
  if (!(maxValue > 0)) return [0, 1];
  const raw = maxValue / Math.max(1, count);
  const power = 10 ** Math.floor(Math.log10(raw));
  const normalized = raw / power;
  const step =
    (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10) *
    power;
  const top = Math.ceil(maxValue / step) * step;
  return Array.from({ length: Math.round(top / step) + 1 }, (_, index) => index * step);
}

export type BarLayout = ReturnType<typeof barLayout>;

/**
 * Geometria di un grafico a barre orizzontali.
 *
 * Le misure arrivano dagli standard della modalita' di rendering: le barre non
 * si assottigliano per stare dentro, se non ci stanno il contenitore scorre.
 */
export function barLayout(
  rows: ChartRow[],
  availableWidth: number,
  sizing: BarSizing = BAR_SIZING.standard,
  axisFormat: (value: number) => string = (value) => String(Math.round(value)),
  /** La scala arriva almeno fin qui, anche se tutte le barre restano sotto. */
  domainFloor = 0
) {
  const fontSize = sizing.fontSize;
  const longestLabel = rows.reduce((longest, row) => Math.max(longest, row.label.length), 0);
  const labelWidth = Math.min(
    sizing.maxLabelWidth,
    Math.max(sizing.minLabelWidth, Math.ceil(estimateTextWidth('x'.repeat(longestLabel), fontSize)) + 12)
  );
  const maxValue = Math.max(0, domainFloor, ...rows.map((row) => row.value));
  const ticks = niceTicks(maxValue, sizing.tickCount);
  const axisTop = Math.ceil(fontSize * 1.9);
  const longestValue = rows.reduce((longest, row) => Math.max(longest, row.display.length), 0);
  const valueWidth = Math.max(
    sizing.minValueWidth,
    Math.ceil(estimateTextWidth('0'.repeat(longestValue), fontSize)) + 14
  );
  // -2px: evita lo scroll orizzontale nato da arrotondamenti subpixel.
  const plotWidth = Math.max(sizing.minPlotWidth, availableWidth - labelWidth - valueWidth - 2);
  const plotHeight = Math.max(sizing.rowHeight, rows.length * sizing.rowHeight);

  const y = scaleBand<string>()
    .domain(rows.map((row) => row.id))
    .range([0, plotHeight])
    .paddingInner(sizing.rowHeight > 30 ? 0.34 : 0.28);

  return {
    fontSize,
    labelWidth,
    valueWidth,
    plotWidth,
    plotHeight,
    axisTop,
    ticks,
    tickLabel: axisFormat,
    width: labelWidth + plotWidth + valueWidth,
    height: axisTop + plotHeight + Math.ceil(fontSize * 0.6),
    /** Spessore reale della barra: mai oltre il tetto dello standard. */
    barHeight: Math.min(sizing.maxBarThickness, y.bandwidth()),
    y,
    x: scaleLinear()
      .domain([0, ticks[ticks.length - 1] || 1])
      .range([0, plotWidth]),
    /** Etichetta accorciata alla colonna disponibile, con i puntini finali. */
    labelText: (label: string) => truncateToWidth(label, fontSize, labelWidth - 12)
  };
}

/**
 * Barra con l'estremita' del dato arrotondata e la base squadrata.
 * Con un `rx` sul rect si arrotonderebbe anche l'attacco alla linea di base.
 */
export function barPath(width: number, height: number, radius = 4) {
  const w = Math.max(0, width);
  const h = Math.max(0, height);
  const r = Math.min(radius, w, h / 2);
  if (r <= 0) return `M0,0 H${w} V${h} H0 Z`;
  return `M0,0 H${w - r} A${r},${r} 0 0 1 ${w},${r} V${h - r} A${r},${r} 0 0 1 ${w - r},${h} H0 Z`;
}

/** Colonna con la testa arrotondata e la base squadrata. */
export function columnPath(width: number, height: number, radius = 4) {
  const w = Math.max(0, width);
  const h = Math.max(0, height);
  const r = Math.min(radius, h, w / 2);
  if (r <= 0) return `M0,${h} V0 H${w} V${h} Z`;
  return `M0,${h} V${r} A${r},${r} 0 0 1 ${r},0 H${w - r} A${r},${r} 0 0 1 ${w},${r} V${h} Z`;
}

export type SeriesPoint = { key: string; label: string; value: number };

/**
 * Percorsi della linea e del velo sottostante, per punti equispaziati.
 *
 * Sta qui e non nel componente perche' `d3` in questo progetto non porta i
 * propri tipi: tenendo un solo punto d'ingresso le annotazioni esplicite
 * servono una volta sola.
 */
export function seriesPaths(
  points: SeriesPoint[],
  x: (index: number) => number,
  y: (value: number) => number,
  baseline: number
) {
  const toLine = line()
    .x((_: SeriesPoint, index: number) => x(index))
    .y((point: SeriesPoint) => y(point.value))
    .curve(curveMonotoneX);
  const toArea = area()
    .x((_: SeriesPoint, index: number) => x(index))
    .y0(baseline)
    .y1((point: SeriesPoint) => y(point.value))
    .curve(curveMonotoneX);

  return { line: String(toLine(points) || ''), area: String(toArea(points) || '') };
}

export type DumbbellDatum = { id: string; from: number; to: number };

/** Geometria del confronto a due punte: stesse regole delle barre orizzontali. */
export function dumbbellLayout(
  rows: DumbbellDatum[],
  availableWidth: number,
  labelWidth: number,
  sizing: BarSizing,
  padRight: number
) {
  const ticks = niceTicks(Math.max(0, ...rows.flatMap((row) => [row.from, row.to])), sizing.tickCount);
  const plotWidth = Math.max(sizing.minPlotWidth, availableWidth - labelWidth - padRight - 2);
  const plotHeight = Math.max(sizing.rowHeight, rows.length * sizing.rowHeight);

  return {
    ticks,
    plotWidth,
    plotHeight,
    y: scaleBand<string>()
      .domain(rows.map((row) => row.id))
      .range([0, plotHeight])
      .paddingInner(0.3),
    x: scaleLinear()
      .domain([0, ticks[ticks.length - 1] || 1])
      .range([0, plotWidth])
  };
}
