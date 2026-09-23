import type { ChartRow } from '../chartData';

export type ChartTooltipState = {
  title: string;
  /** Righe valore: ognuna con la sua pastiglia di colore. */
  values: { label?: string; value: string; color?: string }[];
  /** Riga di contesto in coda, in inchiostro attenuato. */
  hint?: string;
  x: number;
  y: number;
};

const TOOLTIP_WIDTH = 240;
const TOOLTIP_HEIGHT = 92;
const GAP = 14;

/** Posizione accanto al puntatore, rientrando sempre dentro la finestra. */
function place(event: { clientX: number; clientY: number }) {
  const x = Math.min(event.clientX + GAP, window.innerWidth - TOOLTIP_WIDTH - GAP);
  const y =
    event.clientY + TOOLTIP_HEIGHT + GAP > window.innerHeight
      ? event.clientY - TOOLTIP_HEIGHT - GAP
      : event.clientY + GAP;

  return { x: Math.max(GAP, x), y: Math.max(GAP, y) };
}

/** Tooltip di una riga: valore, quota sul totale e contesto. */
export function tooltipAt(
  event: MouseEvent,
  row: ChartRow,
  options: { percent?: boolean } = {}
): ChartTooltipState {
  const { percent = true } = options;
  return {
    title: row.label,
    values: [
      { value: row.display, color: row.color },
      ...(percent
        ? [
            {
              label: 'quota',
              value: `${row.percent.toLocaleString('it-IT', {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1
              })}%`
            }
          ]
        : [])
    ],
    hint: row.hint,
    ...place(event)
  };
}

/** Tooltip generico per i grafici che non ragionano per righe. */
export function tooltipFor(
  event: { clientX: number; clientY: number },
  title: string,
  values: ChartTooltipState['values'],
  hint?: string
): ChartTooltipState {
  return { title, values, hint, ...place(event) };
}
