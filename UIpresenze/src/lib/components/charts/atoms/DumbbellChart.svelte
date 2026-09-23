<script module lang="ts">
  export type DumbbellRow = {
    id: string;
    label: string;
    from: number;
    to: number;
    hint?: string;
  };
</script>

<script lang="ts">
  /**
   * Confronto prima/dopo per voce: due punte unite da un segmento.
   * E' la forma giusta per "stimato contro consuntivo": due barre affiancate
   * raddoppierebbero l'inchiostro per dire la stessa cosa, e la distanza fra i
   * due valori - che qui e' il punto - si leggerebbe peggio.
   */
  import { dumbbellLayout } from '../chartData';
  import {
    BAR_SIZING,
    estimateTextWidth,
    resolveRenderMode,
    truncateToWidth,
    type ChartRenderMode
  } from '../chartSizing';
  import { tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    rows: DumbbellRow[];
    title: string;
    format: (value: number) => string;
    axisFormat?: (value: number) => string;
    fromLabel: string;
    toLabel: string;
    fromColor: string;
    toColor: string;
    mode?: ChartRenderMode | 'auto';
    /** Limita l'altezza visibile: di default il grafico cresce e scorre la schermata. */
    maxHeight?: string;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    rows,
    title,
    format,
    axisFormat,
    fromLabel,
    toLabel,
    fromColor,
    toColor,
    mode = 'auto',
    maxHeight,
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeId = $state<string | null>(null);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(BAR_SIZING[renderMode]);
  const fontSize = $derived(sizing.fontSize);
  const tickFormat = $derived(axisFormat ?? format);

  const labelWidth = $derived(
    Math.min(
      sizing.maxLabelWidth,
      Math.max(
        sizing.minLabelWidth,
        Math.ceil(Math.max(0, ...rows.map((row) => estimateTextWidth(row.label, fontSize)))) + 12
      )
    )
  );
  const axisTop = $derived(Math.ceil(fontSize * 1.9));
  const padRight = $derived(Math.ceil(fontSize * 1.4));
  const layout = $derived(dumbbellLayout(rows, availableWidth, labelWidth, sizing, padRight));
  const ticks = $derived(layout.ticks);
  const plotWidth = $derived(layout.plotWidth);
  const plotHeight = $derived(layout.plotHeight);
  const height = $derived(axisTop + plotHeight + Math.ceil(fontSize * 0.6));
  const y = $derived(layout.y);
  const x = $derived(layout.x);

  function show(event: MouseEvent, row: DumbbellRow) {
    activeId = row.id;
    ontooltip?.(
      tooltipFor(
        event,
        row.label,
        [
          { label: fromLabel, value: format(row.from), color: fromColor },
          { label: toLabel, value: format(row.to), color: toColor }
        ],
        row.hint
      )
    );
  }

  function hide() {
    activeId = null;
    ontooltip?.(null);
  }
</script>

<div class="dumbbell" style:--chart-font={`${fontSize}px`} bind:clientWidth={availableWidth}>
  <ul class="legend">
    <li><span class="key" style:background={fromColor}></span>{fromLabel}</li>
    <li><span class="key" style:background={toColor}></span>{toLabel}</li>
  </ul>

  <div class="plot" style:max-height={maxHeight}>
    {#if availableWidth > 0}
      <svg
        width={labelWidth + plotWidth + padRight}
        {height}
        viewBox={`0 0 ${labelWidth + plotWidth + padRight} ${height}`}
        role="img"
        aria-label={title}
      >
        <g transform={`translate(${labelWidth},0)`}>
          {#each ticks as tick (tick)}
            <line class="grid" x1={x(tick)} x2={x(tick)} y1={axisTop - 6} y2={axisTop + plotHeight}></line>
            <text class="tick" x={x(tick)} y={axisTop - 12} text-anchor="middle">{tickFormat(tick)}</text>
          {/each}
        </g>

        <g transform={`translate(${labelWidth},${axisTop})`}>
          {#each rows as row (row.id)}
            {@const centerY = (y(row.id) || 0) + y.bandwidth() / 2}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <g
              class="row"
              class:active={activeId === row.id}
              data-history-hover-exclude
              onmouseenter={(event) => show(event, row)}
              onmousemove={(event) => show(event, row)}
              onmouseleave={hide}
            >
              <rect class="hit" x={-labelWidth} y={y(row.id) || 0} width={labelWidth + plotWidth} height={y.bandwidth()}></rect>
              <line class="link" x1={x(row.from)} x2={x(row.to)} y1={centerY} y2={centerY}></line>
              <circle class="dot" cx={x(row.from)} cy={centerY} r="5" fill={fromColor}></circle>
              <circle class="dot" cx={x(row.to)} cy={centerY} r="5" fill={toColor}></circle>
              <text class="label" x={-10} y={centerY} text-anchor="end" dominant-baseline="middle">
                {truncateToWidth(row.label, fontSize, labelWidth - 12)}
                <title>{row.label}</title>
              </text>
            </g>
          {/each}
        </g>
      </svg>
    {/if}
  </div>
</div>

<style>
  .dumbbell {
    min-width: 0;
  }

  .plot {
    overflow: auto;
  }

  svg {
    display: block;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 0.9rem;
    margin: 0 0 0.45rem;
    padding: 0;
    list-style: none;
    color: #475569;
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .key {
    width: 9px;
    height: 9px;
    border-radius: 999px;
  }

  .grid {
    stroke: #e7ecf2;
    stroke-width: 1;
    shape-rendering: crispEdges;
  }

  .tick,
  .label {
    fill: #94a3b8;
    font-family: var(--font-mono);
    font-size: var(--chart-font);
  }

  .label {
    fill: #475569;
  }

  .link {
    stroke: #cbd5e1;
    stroke-width: 2;
    stroke-linecap: round;
  }

  .dot {
    stroke: #ffffff;
    stroke-width: 2;
  }

  .hit {
    fill: transparent;
  }

  .row {
    cursor: pointer;
  }

  .row.active .hit {
    fill: rgba(15, 23, 42, 0.04);
  }
</style>
