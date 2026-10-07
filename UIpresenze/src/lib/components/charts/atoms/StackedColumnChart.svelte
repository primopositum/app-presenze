<script module lang="ts">
  export type StackedSeries = {
    id: string;
    label: string;
    color: string;
    /** Un valore per categoria, allineato a `categories`. */
    values: number[];
  };
</script>

<script lang="ts">
  /**
   * Colonne impilate: il totale di ogni categoria e come si divide fra poche
   * serie (al massimo otto tinte, la coda va gia' piegata in "Altri").
   *
   * Le serie si impilano nell'ordine ricevuto, la prima alla base. Fra un pezzo
   * e l'altro resta un vuoto di 2px nel colore della superficie; solo la testa
   * della colonna e' arrotondata. Etichettato direttamente e' solo il totale
   * piu' alto, il resto lo portano asse, tooltip e legenda.
   *
   * La legenda sta sotto: nella card mostra le voci di `legend`, a schermo
   * intero quelle di `fullLegend` (tutte), se c'e'.
   */
  import { columnPath, niceTicks, type ChartRow } from '../chartData';
  import { estimateTextWidth, resolveRenderMode, SERIES_SIZING, type ChartRenderMode } from '../chartSizing';
  import { fmtPercent } from '../format';
  import ChartLegend from './ChartLegend.svelte';
  import { useCardExpansion } from './cardExpansion';
  import { tooltipAt, tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    categories: { key: string; label: string }[];
    series: StackedSeries[];
    legend: ChartRow[];
    fullLegend?: ChartRow[];
    /** Serie che raccoglie le voci di `fullLegend` senza un pezzo proprio. */
    otherId?: string;
    title: string;
    format: (value: number) => string;
    axisFormat?: (value: number) => string;
    mode?: ChartRenderMode | 'auto';
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    categories,
    series,
    legend,
    fullLegend,
    otherId = '__other__',
    title,
    format,
    axisFormat,
    mode = 'auto',
    ontooltip
  }: Props = $props();

  /** Vuoto fra due pezzi della stessa colonna. */
  const GAP = 2;

  let availableWidth = $state(0);
  let activeKey = $state<string | null>(null);
  let activeSeries = $state<string | null>(null);

  const card = useCardExpansion();
  const legendRows = $derived(card?.expanded && fullLegend ? fullLegend : legend);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(SERIES_SIZING[renderMode]);
  const tickFormat = $derived(axisFormat ?? format);
  const fontSize = $derived(sizing.fontSize);

  const totals = $derived(
    categories.map((_, index) => series.reduce((sum, item) => sum + Math.max(0, item.values[index] ?? 0), 0))
  );
  const maxValue = $derived(Math.max(0, ...totals));
  const ticks = $derived(niceTicks(maxValue, sizing.tickCount));
  const yMax = $derived(ticks[ticks.length - 1] || 1);
  const topIndex = $derived(totals.indexOf(maxValue));

  const axisWidth = $derived(
    Math.ceil(Math.max(...ticks.map((tick) => estimateTextWidth(tickFormat(tick), fontSize)))) + 12
  );
  const labelBand = $derived(Math.ceil(fontSize * 2.2));
  const capBand = $derived(Math.ceil(fontSize * 1.6));
  const slotWidth = $derived(
    Math.max(
      sizing.minSlotWidth,
      Math.ceil(Math.max(0, ...categories.map((category) => estimateTextWidth(category.label, fontSize)))) + 10
    )
  );
  const plotWidth = $derived(Math.max(slotWidth * categories.length, availableWidth - axisWidth - 8));
  const width = $derived(axisWidth + plotWidth + 8);
  const height = $derived(capBand + sizing.plotHeight + labelBand);
  const band = $derived(categories.length > 0 ? plotWidth / categories.length : plotWidth);
  const columnWidth = $derived(Math.min(sizing.maxColumnThickness, Math.max(4, band - 8)));

  const scale = (value: number) => (value / yMax) * sizing.plotHeight;
  const baseline = $derived(capBand + sizing.plotHeight);

  /** Pezzi di una colonna dal basso, con la loro altezza gia' al netto del vuoto. */
  function stack(index: number) {
    const pieces = series
      .map((item) => ({ item, value: Math.max(0, item.values[index] ?? 0) }))
      .filter((piece) => piece.value > 0);
    let bottom = baseline;
    return pieces.map((piece, position) => {
      const full = scale(piece.value);
      const top = position === pieces.length - 1;
      const drawn = top ? full : Math.max(0, full - GAP);
      const result = { ...piece, y: bottom - full + (top ? 0 : GAP), height: drawn, top };
      bottom -= full;
      return result;
    });
  }

  function seriesOfLegend(id: string) {
    return series.some((item) => item.id === id) ? id : otherId;
  }

  function showPiece(event: MouseEvent, index: number, item: StackedSeries, value: number) {
    activeKey = categories[index].key;
    activeSeries = item.id;
    const total = totals[index];
    ontooltip?.(
      tooltipFor(
        event,
        `${item.label} · ${categories[index].label}`,
        [
          { value: format(value), color: item.color },
          { label: 'quota del mese', value: fmtPercent(total > 0 ? (value / total) * 100 : 0) }
        ],
        `totale del mese ${format(total)}`
      )
    );
  }

  function showLegend(event: MouseEvent, row: ChartRow) {
    activeSeries = seriesOfLegend(row.id);
    ontooltip?.(tooltipAt(event, row));
  }

  function hide() {
    activeKey = null;
    activeSeries = null;
    ontooltip?.(null);
  }
</script>

<div class="stacked">
  <div class="column-wrap" style:--chart-font={`${fontSize}px`} bind:clientWidth={availableWidth}>
    {#if availableWidth > 0}
      <svg {width} {height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {#each ticks as tick (tick)}
          <line class="grid" x1={axisWidth} x2={width - 8} y1={baseline - scale(tick)} y2={baseline - scale(tick)}></line>
          <text class="tick" x={axisWidth - 8} y={baseline - scale(tick)} text-anchor="end" dominant-baseline="middle">
            {tickFormat(tick)}
          </text>
        {/each}

        <g transform={`translate(${axisWidth},0)`}>
          {#each categories as category, index (category.key)}
            {@const columnX = index * band + (band - columnWidth) / 2}
            <g class="column" class:active={activeKey === category.key} data-history-hover-exclude>
              <rect class="hit" x={index * band} y={capBand} width={band} height={sizing.plotHeight}></rect>
              {#each stack(index) as piece (piece.item.id)}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <path
                  class="mark"
                  class:dimmed={activeSeries !== null && activeSeries !== piece.item.id}
                  transform={`translate(${columnX},${piece.y})`}
                  d={piece.top
                    ? columnPath(columnWidth, piece.height)
                    : `M0,0 H${columnWidth} V${piece.height} H0 Z`}
                  fill={piece.item.color}
                  onmouseenter={(event) => showPiece(event, index, piece.item, piece.value)}
                  onmousemove={(event) => showPiece(event, index, piece.item, piece.value)}
                  onmouseleave={hide}
                ></path>
              {/each}
              {#if index === topIndex && totals[index] > 0}
                <!-- Sui bordi l'etichetta rientra verso il grafico, altrimenti esce dalla card. -->
                <text
                  class="cap"
                  x={index * band + band / 2}
                  y={baseline - scale(totals[index]) - 6}
                  text-anchor={index === 0 ? 'start' : index === categories.length - 1 ? 'end' : 'middle'}
                >
                  {format(totals[index])}
                </text>
              {/if}
              <text class="label" x={index * band + band / 2} y={baseline + fontSize * 1.5} text-anchor="middle">
                {category.label}
              </text>
            </g>
          {/each}
        </g>
      </svg>
    {/if}
  </div>

  <ChartLegend
    rows={legendRows}
    activeId={null}
    onhover={showLegend}
    onleave={hide}
  />
</div>

<style>
  .stacked {
    display: grid;
    gap: 0.6rem;
    min-width: 0;
  }

  .column-wrap {
    overflow-x: auto;
  }

  svg {
    display: block;
  }

  .grid {
    stroke: #e7ecf2;
    stroke-width: 1;
    shape-rendering: crispEdges;
  }

  .tick,
  .label,
  .cap {
    font-family: var(--font-mono);
    font-size: var(--chart-font);
  }

  .tick,
  .label {
    fill: #94a3b8;
  }

  .cap {
    fill: #0f172a;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .hit {
    fill: transparent;
  }

  .mark {
    cursor: pointer;
    transition: opacity 140ms ease;
  }

  .mark.dimmed {
    opacity: 0.3;
  }

  .column.active .label {
    fill: #0f172a;
  }
</style>
