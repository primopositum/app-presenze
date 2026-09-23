<script module lang="ts">
  export type ScatterPoint = {
    id: string;
    label: string;
    x: number;
    y: number;
    hint?: string;
  };
</script>

<script lang="ts">
  /**
   * Dispersione a serie singola: due misure per voce, una per asse.
   *
   * Serve a leggere un rapporto - ore contro valore - che due grafici separati
   * non mostrerebbero. La retta di riferimento e' il rapporto medio: sopra sta
   * chi rende piu' della media, sotto chi rende meno.
   */
  import { niceTicks } from '../chartData';
  import {
    estimateTextWidth,
    resolveRenderMode,
    SERIES_SIZING,
    truncateToWidth,
    type ChartRenderMode
  } from '../chartSizing';
  import { ACCENT } from '../palette';
  import { tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    points: ScatterPoint[];
    title: string;
    xLabel: string;
    yLabel: string;
    formatX: (value: number) => string;
    formatY: (value: number) => string;
    axisFormatX?: (value: number) => string;
    axisFormatY?: (value: number) => string;
    color?: string;
    /** Pendenza della retta di riferimento (y per unita' di x) e sua didascalia. */
    reference?: { slope: number; label: string } | null;
    mode?: ChartRenderMode | 'auto';
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    points,
    title,
    xLabel,
    yLabel,
    formatX,
    formatY,
    axisFormatX,
    axisFormatY,
    color = ACCENT,
    reference = null,
    mode = 'auto',
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeId = $state<string | null>(null);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(SERIES_SIZING[renderMode]);
  const fontSize = $derived(sizing.fontSize);
  const tickX = $derived(axisFormatX ?? formatX);
  const tickY = $derived(axisFormatY ?? formatY);

  const xTicks = $derived(niceTicks(Math.max(0, ...points.map((point) => point.x)), sizing.tickCount));
  const yTicks = $derived(niceTicks(Math.max(0, ...points.map((point) => point.y)), sizing.tickCount));
  const xMax = $derived(xTicks[xTicks.length - 1] || 1);
  const yMax = $derived(yTicks[yTicks.length - 1] || 1);

  const axisWidth = $derived(
    Math.ceil(Math.max(...yTicks.map((tick) => estimateTextWidth(tickY(tick), fontSize)))) + 12
  );
  const labelBand = $derived(Math.ceil(fontSize * 3.4));
  const capBand = $derived(Math.ceil(fontSize * 2.2));
  const padRight = $derived(Math.ceil(fontSize * 2.6));
  const plotHeight = $derived(sizing.plotHeight);
  // Sotto la misura minima il disegno non si comprime: sborda e il contenitore scorre.
  const plotWidth = $derived(Math.max(sizing.minPlotWidth, availableWidth - axisWidth - padRight));
  const width = $derived(axisWidth + plotWidth + padRight);
  const height = $derived(capBand + plotHeight + labelBand);

  const x = (value: number) => (value / xMax) * plotWidth;
  const y = (value: number) => capBand + plotHeight - (value / yMax) * plotHeight;

  /** La retta si ferma al bordo che incontra per primo. */
  const referenceEnd = $derived.by(() => {
    if (!reference || !(reference.slope > 0)) return null;
    const atXMax = reference.slope * xMax;
    return atXMax <= yMax ? { x: xMax, y: atXMax } : { x: yMax / reference.slope, y: yMax };
  });

  function show(event: MouseEvent, point: ScatterPoint) {
    activeId = point.id;
    ontooltip?.(
      tooltipFor(
        event,
        point.label,
        [
          { label: xLabel, value: formatX(point.x), color },
          { label: yLabel, value: formatY(point.y) }
        ],
        point.hint
      )
    );
  }

  function hide() {
    activeId = null;
    ontooltip?.(null);
  }
</script>

<div class="scatter" style:--chart-font={`${fontSize}px`} bind:clientWidth={availableWidth}>
  {#if availableWidth > 0}
    <svg {width} {height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
      {#each yTicks as tick (tick)}
        <line class="grid" x1={axisWidth} x2={axisWidth + plotWidth} y1={y(tick)} y2={y(tick)}></line>
        <text class="tick" x={axisWidth - 8} y={y(tick)} text-anchor="end" dominant-baseline="middle">
          {tickY(tick)}
        </text>
      {/each}

      <g transform={`translate(${axisWidth},0)`}>
        {#each xTicks as tick (tick)}
          <text class="tick" x={x(tick)} y={capBand + plotHeight + fontSize * 1.5} text-anchor="middle">
            {tickX(tick)}
          </text>
        {/each}

        {#if referenceEnd}
          <line class="reference" x1={0} y1={y(0)} x2={x(referenceEnd.x)} y2={y(referenceEnd.y)}></line>
          <text
            class="reference-label"
            x={x(referenceEnd.x)}
            y={y(referenceEnd.y) - 6}
            text-anchor="end"
          >
            {reference?.label}
          </text>
        {/if}

        {#each points as point (point.id)}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <g
            class="point"
            class:active={activeId === point.id}
            data-history-hover-exclude
            onmouseenter={(event) => show(event, point)}
            onmousemove={(event) => show(event, point)}
            onmouseleave={hide}
          >
            <!-- Bersaglio generoso: il pallino da 10px sarebbe troppo piccolo da centrare. -->
            <circle class="hit" cx={x(point.x)} cy={y(point.y)} r="13"></circle>
            <circle class="dot" cx={x(point.x)} cy={y(point.y)} r={activeId === point.id ? 7 : 5} fill={color}></circle>
            {#if activeId === point.id}
              <text class="point-label" x={x(point.x)} y={y(point.y) - 12} text-anchor="middle">
                {truncateToWidth(point.label, fontSize, 140)}
              </text>
            {/if}
          </g>
        {/each}

        <text class="axis-name" x={plotWidth / 2} y={capBand + plotHeight + fontSize * 3} text-anchor="middle">
          {xLabel}
        </text>
      </g>

      <text class="axis-name" x="0" y={capBand - 7} text-anchor="start">{yLabel}</text>
    </svg>
  {/if}
</div>

<style>
  .scatter {
    min-width: 0;
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
  .axis-name,
  .reference-label,
  .point-label {
    font-family: var(--font-mono);
    font-size: var(--chart-font);
  }

  .tick {
    fill: #94a3b8;
  }

  .axis-name,
  .reference-label {
    fill: #64748b;
    font-size: calc(var(--chart-font) * 0.92);
  }

  .point-label {
    fill: #0f172a;
    font-weight: 700;
  }

  .reference {
    stroke: #94a3b8;
    stroke-width: 1.5;
  }

  .hit {
    fill: transparent;
    cursor: pointer;
  }

  .dot {
    stroke: #ffffff;
    stroke-width: 2;
  }
</style>
