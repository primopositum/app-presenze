<script module lang="ts">
  export type GroupedColumnSeries = {
    id: string;
    label: string;
    color: string;
  };

  export type GroupedColumnPoint = {
    key: string;
    label: string;
    /** Un valore per serie, indicizzato per `id`. */
    values: Record<string, number>;
  };
</script>

<script lang="ts">
  /**
   * Colonne affiancate: poche serie (2-3) confrontate categoria per categoria.
   * Stesso disegno di ColumnChart; le colonne di un gruppo sono separate da un
   * vuoto di 2px nel colore della superficie.
   *
   * La legenda in testa porta identita' e totale di ogni serie, cosi' il colore
   * non e' mai l'unico canale. Il passaggio del mouse evidenzia l'intero giorno
   * e il tooltip elenca tutte le serie.
   */
  import { columnPath, niceTicks } from '../chartData';
  import { estimateTextWidth, resolveRenderMode, SERIES_SIZING, type ChartRenderMode } from '../chartSizing';
  import { tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    points: GroupedColumnPoint[];
    series: GroupedColumnSeries[];
    title: string;
    format: (value: number) => string;
    axisFormat?: (value: number) => string;
    mode?: ChartRenderMode | 'auto';
    /** Valori interi (conteggi): l'asse non mostra tacche frazionarie. */
    integer?: boolean;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    points,
    series,
    title,
    format,
    axisFormat,
    mode = 'auto',
    integer = false,
    ontooltip
  }: Props = $props();

  /** Vuoto fra le colonne di uno stesso gruppo. */
  const GAP = 2;

  let availableWidth = $state(0);
  let activeKey = $state<string | null>(null);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(SERIES_SIZING[renderMode]);
  const tickFormat = $derived(axisFormat ?? format);
  const fontSize = $derived(sizing.fontSize);

  const valueOf = (point: GroupedColumnPoint, id: string) => Math.max(0, point.values[id] ?? 0);
  const totals = $derived(
    series.map((item) => ({ ...item, total: points.reduce((sum, point) => sum + valueOf(point, item.id), 0) }))
  );
  const maxValue = $derived(
    Math.max(0, ...points.flatMap((point) => series.map((item) => valueOf(point, item.id))))
  );
  const ticks = $derived(
    integer
      ? niceTicks(Math.max(1, maxValue), sizing.tickCount).filter(Number.isInteger)
      : niceTicks(maxValue, sizing.tickCount)
  );
  const yMax = $derived(ticks[ticks.length - 1] || 1);

  const axisWidth = $derived(
    Math.ceil(Math.max(...ticks.map((tick) => estimateTextWidth(tickFormat(tick), fontSize)))) + 12
  );
  const labelBand = $derived(Math.ceil(fontSize * 2.2));
  const capBand = $derived(Math.ceil(fontSize * 0.8));
  const minGroupWidth = $derived(series.length * (sizing.minSlotWidth / 2 + GAP) + 10);
  const slotWidth = $derived(
    Math.max(
      minGroupWidth,
      Math.ceil(Math.max(0, ...points.map((point) => estimateTextWidth(point.label, fontSize)))) + 10
    )
  );
  const plotWidth = $derived(Math.max(slotWidth * points.length, availableWidth - axisWidth - 8));
  const width = $derived(axisWidth + plotWidth + 8);
  const height = $derived(capBand + sizing.plotHeight + labelBand);
  const band = $derived(points.length > 0 ? plotWidth / points.length : plotWidth);
  const columnWidth = $derived(
    Math.min(
      sizing.maxColumnThickness,
      Math.max(4, (band - 12 - GAP * (series.length - 1)) / Math.max(1, series.length))
    )
  );
  const groupWidth = $derived(columnWidth * series.length + GAP * (series.length - 1));

  const y = (value: number) => capBand + sizing.plotHeight - (value / yMax) * sizing.plotHeight;

  function show(event: MouseEvent, point: GroupedColumnPoint) {
    activeKey = point.key;
    ontooltip?.(
      tooltipFor(
        event,
        point.label,
        series.map((item) => ({ label: item.label, value: format(valueOf(point, item.id)), color: item.color }))
      )
    );
  }

  function hide() {
    activeKey = null;
    ontooltip?.(null);
  }
</script>

<div class="grouped">
  <ul class="legend">
    {#each totals as item (item.id)}
      <li>
        <span class="dot" style:--dot={item.color}></span>
        <span class="name">{item.label}</span>
        <span class="total">{format(item.total)}</span>
      </li>
    {/each}
  </ul>

  <div class="column-wrap" style:--chart-font={`${fontSize}px`} bind:clientWidth={availableWidth}>
    {#if availableWidth > 0}
      <svg {width} {height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {#each ticks as tick (tick)}
          <line class="grid" x1={axisWidth} x2={width - 8} y1={y(tick)} y2={y(tick)}></line>
          <text class="tick" x={axisWidth - 8} y={y(tick)} text-anchor="end" dominant-baseline="middle">
            {tickFormat(tick)}
          </text>
        {/each}

        <g transform={`translate(${axisWidth},0)`}>
          {#each points as point, index (point.key)}
            {@const groupX = index * band + (band - groupWidth) / 2}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <g
              class="group"
              class:active={activeKey === point.key}
              data-history-hover-exclude
              onmouseenter={(event) => show(event, point)}
              onmousemove={(event) => show(event, point)}
              onmouseleave={hide}
            >
              <rect class="hit" x={index * band} y={capBand} width={band} height={sizing.plotHeight}></rect>
              {#each series as item, seriesIndex (item.id)}
                {@const value = valueOf(point, item.id)}
                {#if value > 0}
                  <path
                    class="mark"
                    transform={`translate(${groupX + seriesIndex * (columnWidth + GAP)},${y(value)})`}
                    d={columnPath(columnWidth, Math.max(0, capBand + sizing.plotHeight - y(value)))}
                    fill={item.color}
                  ></path>
                {/if}
              {/each}
              <text
                class="label"
                x={index * band + band / 2}
                y={capBand + sizing.plotHeight + fontSize * 1.5}
                text-anchor="middle"
              >
                {point.label}
              </text>
            </g>
          {/each}
        </g>
      </svg>
    {/if}
  </div>
</div>

<style>
  .grouped {
    display: grid;
    gap: 0.5rem;
    min-width: 0;
  }

  .legend {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 1.1rem;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: #475569;
  }

  .dot {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    background: var(--dot);
  }

  .total {
    color: #0f172a;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
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
  .label {
    font-family: var(--font-mono);
    font-size: var(--chart-font);
    fill: #94a3b8;
  }

  .hit {
    fill: transparent;
  }

  .group {
    cursor: pointer;
  }

  .group .mark {
    transition: opacity 140ms ease;
  }

  .group.active .hit {
    fill: rgba(15, 23, 42, 0.04);
  }

  .group.active .mark {
    opacity: 0.82;
  }

  .group.active .label {
    fill: #0f172a;
  }
</style>
