/**
 * Collegamento fra una ChartCard e i grafici che contiene.
 *
 * A card ingrandita i grafici con una classifica tagliata (`limit`) mostrano
 * molte piu' voci: la card decide quante, il grafico dice quante ne ha.
 */
import { getContext, setContext } from 'svelte';

const KEY = Symbol('chart-card-expansion');

/** Voci mostrate subito a schermo intero, e quante se ne aggiungono scorrendo. */
export const EXPANDED_STEP = 30;

export type CardExpansion = {
  readonly expanded: boolean;
  /** Voci da mostrare a schermo intero: cresce scorrendo. */
  readonly limit: number;
  /** Il grafico comunica quante voci ha in tutto. */
  reportTotal(total: number): void;
};

export function provideCardExpansion(expansion: CardExpansion) {
  setContext(KEY, expansion);
}

/** undefined fuori da una ChartCard: il grafico si comporta come sempre. */
export function useCardExpansion(): CardExpansion | undefined {
  return getContext<CardExpansion | undefined>(KEY);
}

/**
 * Sposta il nodo in fondo al body: esce da ogni contesto di impilamento del cubo.
 *
 * Va messo su un elemento *figlio* di un contenitore che resta al suo posto
 * (vedi `.portal-anchor`), mai sul primo o sull'ultimo nodo di un blocco
 * `{#if}`: Svelte smonta un blocco scorrendo i fratelli dal primo all'ultimo
 * nodo e, se l'ultimo e' stato spostato, rimuoverebbe anche tutti i fratelli
 * successivi (gli altri grafici della griglia).
 */
export function portal(node: HTMLElement) {
  if (typeof document === 'undefined') return;
  document.body.appendChild(node);
  return {
    destroy() {
      node.remove();
    }
  };
}
