<script module lang="ts">
  export type ColumnPoint = {
    key: string;
    label: string;
    value: number;
    /** Riga di contesto nel tooltip. */
    hint?: string;
    /** Tinta propria, per i punti che portano uno stato. */
    color?: string;
  };
</script>

<script lang="ts">
  /**
   * Colonne a serie singola, per categorie brevi e ordinate: mesi, giorni della
   * settimana, fasce. Le etichette restano orizzontali; quando non ci stanno,
   * il grafico scorre invece di ruotarle o troncarle.
   *
   * Direttamente etichettata e' solo la colonna piu' alta: un numero su ogni
   * colonna non viene letto da nessuno, il resto lo portano asse e tooltip.
   */
  import { columnPath, niceTicks } from '../chartData';
  import { estimateTextWidth, resolveRenderMode, SERIES_SIZING, type ChartRenderMode } from '../chartSizing';
  import { ACCENT } from '../palette';
  import { tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    points: ColumnPoint[];
    title: string;
    format: (value: number) => string;
    axisFormat?: (value: number) => string;
    color?: string;
    mode?: ChartRenderMode | 'auto';
    /** Nome della misura, mostrato nel tooltip accanto al valore. */
    valueLabel?: string;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    points,
    title,
    format,
    axisFormat,
    color = ACCENT,
    mode = 'auto',
    valueLabel,
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeKey = $state<string | null>(null);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(SERIES_SIZING[renderMode]);
  const tickFormat = $derived(axisFormat ?? format);
  const fontSize = $derived(sizing.fontSize);

  const maxValue = $derived(Math.max(0, ...points.map((point) => point.value)));
  const ticks = $derived(niceTicks(maxValue, sizing.tickCount));
  const yMax = $derived(ticks[ticks.length - 1] || 1);

  const axisWidth = $derived(
    Math.ceil(Math.max(...ticks.map((tick) => estimateTextWidth(tickFormat(tick), fontSize)))) + 12
  );
  const labelBand = $derived(Math.ceil(fontSize * 2.2));
  const capBand = $derived(Math.ceil(fontSize * 1.6));
  // La larghezza minima di una colonna e' quella che serve alla sua etichetta.
  const slotWidth = $derived(
    Math.max(
      sizing.minSlotWidth,
      Math.ceil(Math.max(0, ...points.map((point) => estimateTextWidth(point.label, fontSize)))) + 10
    )
  );
  const plotWidth = $derived(Math.max(slotWidth * points.length, availableWidth - axisWidth - 8));
  const width = $derived(axisWidth + plotWidth + 8);
  const height = $derived(capBand + sizing.plotHeight + labelBand);
  const band = $derived(points.length > 0 ? plotWidth / points.length : plotWidth);
  const columnWidth = $derived(Math.min(sizing.maxColumnThickness, Math.max(4, band - 8)));
  const topValue = $derived(
    points.reduce<ColumnPoint | null>(
      (best, point) => (best === null || point.value > best.value ? point : best),
      null
    )
  );

  const y = (value: number) => capBand + sizing.plotHeight - (value / yMax) * sizing.plotHeight;

  function show(event: MouseEvent, point: ColumnPoint) {
    activeKey = point.key;
    ontooltip?.(
      tooltipFor(
        event,
        point.label,
        [{ label: valueLabel, value: format(point.value), color: point.color ?? color }],
        point.hint
      )
    );
  }

  function hide() {
    activeKey = null;
    ontooltip?.(null);
  }
</script>

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
          {@const columnHeight = Math.max(0, capBand + sizing.plotHeight - y(point.value))}
          {@const columnX = index * band + (band - columnWidth) / 2}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <g
            class="column"
            class:active={activeKey === point.key}
            data-history-hover-exclude
            onmouseenter={(event) => show(event, point)}
            onmousemove={(event) => show(event, point)}
            onmouseleave={hide}
          >
            <rect class="hit" x={index * band} y={capBand} width={band} height={sizing.plotHeight}></rect>
            <path
              class="mark"
              transform={`translate(${columnX},${y(point.value)})`}
              d={columnPath(columnWidth, columnHeight)}
              fill={point.color ?? color}
            ></path>
            {#if topValue && point.key === topValue.key && point.value > 0}
              <!-- Sui bordi l'etichetta rientra verso il grafico, altrimenti esce dalla card. -->
              <text
                class="cap"
                x={index * band + band / 2}
                y={y(point.value) - 6}
                text-anchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
              >
                {format(point.value)}
              </text>
            {/if}
            <text class="label" x={index * band + band / 2} y={capBand + sizing.plotHeight + fontSize * 1.5} text-anchor="middle">
              {point.label}
            </text>
          </g>
        {/each}
      </g>
    </svg>
  {/if}
</div>

<style>
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

  .column {
    cursor: pointer;
  }

  .column .mark {
    transition: opacity 140ms ease;
  }

  .column.active .hit {
    fill: rgba(15, 23, 42, 0.04);
  }

  .column.active .mark {
    opacity: 0.82;
  }

  .column.active .label {
    fill: #0f172a;
  }
</style>
