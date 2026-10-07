<script lang="ts">
  /**
   * Ciambella + legenda. Misura lo spazio che ha e applica gli standard della
   * modalita' di rendering: sotto la soglia mette la legenda sotto al grafico
   * invece di stringerla, e la ciambella non scende mai sotto la sua misura.
   *
   * Grafico e legenda condividono l'evidenziazione: puntare una voce accende
   * anche l'altra, cosi' l'identita' non si gioca sul solo colore.
   *
   * Con `allRows`, a schermo intero la ciambella lascia il posto all'elenco
   * completo delle quote: la coda ripiegata in "Altri" torna voce per voce.
   */
  import type { ChartRow } from '../chartData';
  import { DONUT_SIZING, resolveRenderMode, type ChartRenderMode } from '../chartSizing';
  import { fmtPercent } from '../format';
  import ChartLegend from './ChartLegend.svelte';
  import DonutChart from './DonutChart.svelte';
  import { useCardExpansion } from './cardExpansion';
  import { tooltipAt, type ChartTooltipState } from './tooltip';

  type Props = {
    rows: ChartRow[];
    /** Tutte le voci, senza "Altri": si mostrano a schermo intero. */
    allRows?: ChartRow[];
    /** 'auto' sceglie in base alla larghezza disponibile. */
    mode?: ChartRenderMode | 'auto';
    showValue?: boolean;
    centerValue?: string;
    centerLabel?: string;
    title: string;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    rows,
    allRows,
    mode = 'auto',
    showValue = true,
    centerValue,
    centerLabel,
    title,
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeId = $state<string | null>(null);

  const card = useCardExpansion();
  const fullRows = $derived(card?.expanded && allRows ? allRows.slice(0, card.limit) : null);
  const maxPercent = $derived(Math.max(0, ...(fullRows ?? []).map((row) => row.percent)));

  $effect(() => {
    if (allRows) card?.reportTotal(allRows.length);
  });

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(DONUT_SIZING[renderMode]);
  const stacked = $derived(availableWidth > 0 && availableWidth < sizing.stackBelow);

  /** Le quote piccole tengono due decimali: con uno solo diventerebbero 0,0%. */
  function share(percent: number) {
    return fmtPercent(percent, percent < 1 ? 2 : 1);
  }

  function show(event: MouseEvent, row: ChartRow) {
    activeId = row.id;
    ontooltip?.(tooltipAt(event, row));
  }

  function hide() {
    activeId = null;
    ontooltip?.(null);
  }
</script>

{#if fullRows}
  <ol class="share-list" aria-label={title}>
    {#each fullRows as row (row.id)}
      <li
        class:dimmed={activeId !== null && activeId !== row.id}
        data-history-hover-exclude
        onmouseenter={(event) => show(event, row)}
        onmousemove={(event) => show(event, row)}
        onmouseleave={hide}
      >
        <span class="dot" style:--dot={row.color}></span>
        <span class="name" title={row.label}>{row.label}</span>
        <span class="track">
          <span
            class="fill"
            style:--dot={row.color}
            style:width={`${maxPercent > 0 ? (row.percent / maxPercent) * 100 : 0}%`}
          ></span>
        </span>
        {#if showValue}<span class="value">{row.display}</span>{/if}
        <span class="share">{share(row.percent)}</span>
      </li>
    {/each}
  </ol>
{:else}
  <div class="donut-panel" class:stacked bind:clientWidth={availableWidth}>
    <DonutChart
      {rows}
      {title}
      {centerValue}
      {centerLabel}
      {activeId}
      size={sizing.size}
      innerRadius={sizing.innerRadius}
      outerRadius={sizing.outerRadius}
      onhover={show}
      onleave={hide}
    />
    <ChartLegend
      {rows}
      {showValue}
      {activeId}
      maxHeight={`${sizing.legendHeight}px`}
      onhover={show}
      onleave={hide}
    />
  </div>
{/if}

<style>
  .donut-panel {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.75rem;
    align-items: center;
  }

  .donut-panel.stacked {
    grid-template-columns: minmax(0, 1fr);
    justify-items: stretch;
  }

  .donut-panel.stacked :global(.donut-svg) {
    justify-self: center;
  }

  /* Stessa grammatica della legenda, piu' grande e con la quota in barra. */
  .share-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }

  .share-list li {
    display: grid;
    grid-template-columns: 10px minmax(120px, 2fr) minmax(80px, 3fr) auto 4.5rem;
    align-items: center;
    gap: 10px;
    padding: 3px 0;
    font-size: 0.78rem;
    color: #475569;
    font-family: var(--font-mono);
    transition: opacity 140ms ease;
  }

  .share-list li.dimmed {
    opacity: 0.4;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dot {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    background: var(--dot);
  }

  .track {
    height: 10px;
    border-radius: 3px;
    background: #f1f5f9;
    overflow: hidden;
  }

  .fill {
    display: block;
    height: 100%;
    border-radius: 0 3px 3px 0;
    background: var(--dot);
  }

  .value {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .share {
    color: #0f172a;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  @media (max-width: 560px) {
    .share-list li {
      grid-template-columns: 10px minmax(0, 1fr) auto;
    }

    .track,
    .value {
      display: none;
    }
  }
</style>
