/**
 * Token di colore dei grafici.
 *
 * La scala categorica e' un set validato: ogni coppia adiacente resta
 * distinguibile anche con deficit di visione dei colori (Delta E >= 8 su OKLab)
 * e nessuno slot esce dalla banda di luminosita' utile su fondo bianco.
 * L'ordine degli slot fa parte della validazione: si assegnano in sequenza,
 * non si ricicla e non si generano tinte nuove oltre l'ottava.
 */

/** Superfici su cui i grafici vengono disegnati. */
export const SURFACE = {
  /** Fondo delle card dei grafici: i marchi si staccano solo su un fondo neutro. */
  card: '#ffffff',
  /** Fondo di una faccia del cubo. */
  face: '#f8fafc'
} as const;

/** Inchiostri: testi, griglie e assi. Il testo non indossa mai il colore della serie. */
export const INK = {
  primary: '#0f172a',
  secondary: '#475569',
  muted: '#64748b',
  /** Griglia a filo, un gradino sopra la superficie. */
  grid: '#e7ecf2',
  axis: '#cbd5e1'
} as const;

/** Scala categorica: si usa quando le serie *sono* il soggetto (identita'). */
export const SERIES = [
  '#2a78d6',
  '#eb6834',
  '#1baf7a',
  '#eda100',
  '#e87ba4',
  '#008300',
  '#4a3aa7',
  '#e34948'
] as const;

/** Tinta unica per i grafici di magnitudine: una sola serie, un solo colore. */
export const ACCENT = SERIES[0];

/** Grigio delle voci di contesto: la coda "Altri" e le barre non evidenziate. */
export const NEUTRAL = '#aab6c4';

/** Scala sequenziale blu, chiaro -> scuro: solo per magnitudini continue. */
export const SEQUENTIAL = [
  '#b7d3f6',
  '#86b6ef',
  '#5598e7',
  '#3987e5',
  '#2a78d6',
  '#256abf',
  '#1c5cab',
  '#184f95'
] as const;

/**
 * Colori di stato: significano buono/attenzione/critico, mai "serie numero 4".
 * Vanno sempre accompagnati da un'etichetta, mai lasciati soli a colore.
 */
export const STATUS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b'
} as const;

/** Tinte d'accento delle card: una riga sottile, non un fondo pieno. */
export const CARD_ACCENT = {
  jira: SERIES[0],
  people: SERIES[2],
  time: SERIES[6],
  money: SERIES[3],
  forecast: SERIES[1],
  risk: STATUS.critical
} as const;

/** Colore categorico dello slot `index`, senza mai riciclare oltre l'ottavo. */
export function seriesColor(index: number) {
  return SERIES[Math.min(Math.max(0, index), SERIES.length - 1)];
}

/** Gradino della scala sequenziale per un valore normalizzato 0..1. */
export function sequentialColor(ratio: number) {
  const clamped = Math.min(1, Math.max(0, Number.isFinite(ratio) ? ratio : 0));
  return SEQUENTIAL[Math.round(clamped * (SEQUENTIAL.length - 1))];
}
