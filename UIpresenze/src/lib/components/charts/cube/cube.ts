/**
 * Geometria e stato del CubeSwitcher.
 *
 * Le facce sono le pareti laterali di un prisma regolare: con 4 schermate e'
 * esattamente un cubo, con 3 un prisma triangolare, con N una rotazione di
 * 360/N gradi per passo. `step` cresce/decresce all'infinito e non viene mai
 * riportato a 0: la faccia attiva si ricava con il modulo, altrimenti tornando
 * dall'ultima alla prima schermata il cubo girerebbe all'indietro.
 */

export const CUBE_CONTEXT_KEY = Symbol('cube-switcher');

export type CubeFaceDescriptor = {
  id?: string;
  /** Etichetta mostrata nei pulsanti/tab di navigazione. */
  label?: string;
  /** Colore di sfondo della faccia. */
  tint?: string;
  /** Id della schermata di filtri (`filters/<schermata>/filters.json`): senza, il pulsante filtro non compare. */
  filters?: string;
  /** Componente Svelte da montare nella faccia: le prop le decide chi lo passa. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component?: any;
  props?: Record<string, unknown>;
};

export type CubeContext = {
  /** Label, tint e filtri arrivano come getter: se la prop cambia, i tab si aggiornano. */
  register(
    id: symbol,
    label?: () => string | undefined,
    tint?: () => string | undefined,
    filters?: () => string | undefined
  ): void;
  unregister(id: symbol): void;
  indexOf(id: symbol): number;
  /** true quando la faccia va montata: con `mount="active"` solo quella attiva e quella in arrivo. */
  isMounted(index: number): boolean;
  isActive(index: number): boolean;
  readonly count: number;
  readonly activeIndex: number;
  readonly angle: number;
  readonly depth: number;
  readonly reducedMotion: boolean;
  /**
   * true quando la rotazione e' finita e il cubo e' tornato piatto.
   *
   * A riposo le facce escono dallo spazio 3D: Chrome esclude dall'hit test una
   * faccia la cui matrice locale contiene una rotazione di 90 o 270 gradi, anche
   * quando la composizione con il cubo la riporta frontale. Restando in 3D,
   * meta' delle schermate non riceverebbe ne' la rotella ne' il passaggio del
   * mouse, pur essendo disegnata correttamente.
   */
  readonly settled: boolean;
};

/** Gradi di rotazione fra una faccia e la successiva. */
export function faceAngle(count: number): number {
  return 360 / Math.max(1, count);
}

/**
 * Distanza della faccia dal centro del prisma (apotema).
 * Con 4 facce vale meta' larghezza, come nel cubo classico.
 */
export function faceDepth(width: number, count: number): number {
  const half = Math.max(0, width) / 2;
  if (count < 3) return half;
  return half / Math.tan(Math.PI / count);
}

/** Faccia visibile per uno `step` che cresce all'infinito, anche negativo. */
export function activeFace(step: number, count: number): number {
  const total = Math.max(1, count);
  return ((step % total) + total) % total;
}

/** Rotazione del cubo in gradi: segue `step`, non la faccia attiva. */
export function cubeRotation(step: number, count: number): number {
  return -faceAngle(count) * step;
}

/**
 * Step da raggiungere per mostrare `targetIndex` prendendo la strada piu' corta.
 * Senza loop la rotazione resta dentro l'intervallo delle facce esistenti.
 */
export function stepForIndex(step: number, count: number, targetIndex: number, loop = true): number {
  const total = Math.max(1, count);
  const target = Math.min(total - 1, Math.max(0, targetIndex));
  const current = activeFace(step, total);
  if (!loop) return step + (target - current);

  let delta = ((target - current) % total + total) % total;
  if (delta * 2 > total) delta -= total;
  return step + delta;
}

/** Con loop disattivato i pulsanti si spengono sul primo e sull'ultimo grafico. */
export function canStep(step: number, count: number, direction: 1 | -1, loop = true): boolean {
  if (count <= 1) return false;
  if (loop) return true;
  const current = activeFace(step, count);
  return direction === 1 ? current < count - 1 : current > 0;
}
