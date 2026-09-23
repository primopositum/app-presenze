/**
 * Regole di dimensionamento dei grafici.
 *
 * Ogni tipo di grafico ha i suoi standard per tre modalita' di rendering,
 * scelte in base allo spazio disponibile:
 * - `compact`  card affiancate in griglia, o cubo stretto;
 * - `standard` card a tutta riga;
 * - `large`    cubo ingrandito a schermo intero.
 *
 * I grafici non "scalano" per stare dentro: prendono la misura minima dello
 * standard e, se non ci stanno, si scorre.
 */

export type ChartRenderMode = 'compact' | 'standard' | 'large';

/** Larghezza disponibile a partire dalla quale si passa alla modalita'. */
export const RENDER_MODE_WIDTH = {
  standard: 520,
  large: 900
} as const;

export function resolveRenderMode(availableWidth: number): ChartRenderMode {
  if (availableWidth >= RENDER_MODE_WIDTH.large) return 'large';
  if (availableWidth >= RENDER_MODE_WIDTH.standard) return 'standard';
  return 'compact';
}

/** Larghezza indicativa di un testo: serve per decidere se ci sta, non per disegnarlo. */
export function estimateTextWidth(text: string, fontSize: number) {
  return text.length * fontSize * 0.62;
}

/**
 * Accorcia un'etichetta alla larghezza disponibile aggiungendo i puntini.
 * In SVG il testo non va mai tagliato dal contenitore: si misura prima.
 */
export function truncateToWidth(text: string, fontSize: number, maxWidth: number) {
  if (maxWidth <= 0) return '';
  if (estimateTextWidth(text, fontSize) <= maxWidth) return text;
  const maxChars = Math.floor(maxWidth / (fontSize * 0.62)) - 1;
  return maxChars <= 1 ? '…' : `${text.slice(0, maxChars)}…`;
}

export type DonutSizing = {
  size: number;
  innerRadius: number;
  outerRadius: number;
  /** Altezza massima della legenda accanto alla ciambella. */
  legendHeight: number;
  /** Sotto questa larghezza del pannello la legenda va sotto al grafico. */
  stackBelow: number;
};

export const DONUT_SIZING: Record<ChartRenderMode, DonutSizing> = {
  compact: { size: 188, innerRadius: 54, outerRadius: 86, legendHeight: 190, stackBelow: 430 },
  standard: { size: 232, innerRadius: 68, outerRadius: 108, legendHeight: 236, stackBelow: 470 },
  large: { size: 280, innerRadius: 84, outerRadius: 132, legendHeight: 300, stackBelow: 540 }
};

export type BarSizing = {
  /** Passo verticale di una riga: lo spessore della barra e' sempre minore. */
  rowHeight: number;
  /** Tetto dello spessore della barra: mai un blocco spesso quanto la banda. */
  maxBarThickness: number;
  fontSize: number;
  minLabelWidth: number;
  /** Larghezza massima della colonna etichette. */
  maxLabelWidth: number;
  /** Larghezza minima dell'area barre: sotto, si scorre. */
  minPlotWidth: number;
  minValueWidth: number;
  tickCount: number;
};

export const BAR_SIZING: Record<ChartRenderMode, BarSizing> = {
  compact: {
    rowHeight: 26,
    maxBarThickness: 14,
    fontSize: 10,
    minLabelWidth: 96,
    maxLabelWidth: 170,
    minPlotWidth: 150,
    minValueWidth: 60,
    tickCount: 3
  },
  standard: {
    rowHeight: 32,
    maxBarThickness: 18,
    fontSize: 11,
    minLabelWidth: 120,
    maxLabelWidth: 260,
    minPlotWidth: 200,
    minValueWidth: 70,
    tickCount: 4
  },
  large: {
    rowHeight: 38,
    maxBarThickness: 24,
    fontSize: 12,
    minLabelWidth: 150,
    maxLabelWidth: 360,
    minPlotWidth: 260,
    minValueWidth: 86,
    tickCount: 5
  }
};

export type SeriesSizing = {
  fontSize: number;
  /** Altezza dell'area di disegno, assi esclusi. */
  plotHeight: number;
  /** Larghezza minima di una colonna/punto: sotto, il grafico scorre. */
  minSlotWidth: number;
  /** Larghezza minima dell'area di disegno: sotto, il grafico scorre. */
  minPlotWidth: number;
  /** Tetto dello spessore di una colonna. */
  maxColumnThickness: number;
  tickCount: number;
};

/** Standard dei grafici con asse orizzontale: colonne, linee, aree, dispersione. */
export const SERIES_SIZING: Record<ChartRenderMode, SeriesSizing> = {
  compact: { fontSize: 10, plotHeight: 150, minSlotWidth: 30, minPlotWidth: 190, maxColumnThickness: 18, tickCount: 3 },
  standard: { fontSize: 11, plotHeight: 200, minSlotWidth: 38, minPlotWidth: 240, maxColumnThickness: 22, tickCount: 4 },
  large: { fontSize: 12, plotHeight: 260, minSlotWidth: 46, minPlotWidth: 300, maxColumnThickness: 24, tickCount: 5 }
};
