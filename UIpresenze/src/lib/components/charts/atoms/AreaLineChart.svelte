<script lang="ts">
  /**
   * Andamento nel tempo: linea da 2px con un velo dello stesso colore sotto.
   * Una sola serie, quindi nessuna legenda: il titolo della card dice gia' cosa
   * e' disegnato.
   *
   * I bucket vuoti restano sull'asse: saltarli racconterebbe una continuita'
   * che nei dati non c'e'.
   */
  import { niceTicks, seriesPaths, type SeriesPoint } from '../chartData';
  import { estimateTextWidth, resolveRenderMode, SERIES_SIZING, type ChartRenderMode } from '../chartSizing';
  import { ACCENT } from '../palette';
  import { tooltipFor, type ChartTooltipState } from './tooltip';

  type Props = {
    points: SeriesPoint[];
    title: string;
    format: (value: number) => string;
    axisFormat?: (value: number) => string;
    color?: string;
    mode?: ChartRenderMode | 'auto';
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
  let activeIndex = $state<number | null>(null);
  let plotElement: SVGRectElement | undefined = $state();

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(SERIES_SIZING[renderMode]);
  const fontSize = $derived(sizing.fontSize);
  const tickFormat = $derived(axisFormat ?? format);

  const maxValue = $derived(Math.max(0, ...points.map((point) => point.value)));
  const ticks = $derived(niceTicks(maxValue, sizing.tickCount));
  const yMax = $derived(ticks[ticks.length - 1] || 1);

  const axisWidth = $derived(
    Math.ceil(Math.max(...ticks.map((tick) => estimateTextWidth(tickFormat(tick), fontSize)))) + 12
  );
  const labelBand = $derived(Math.ceil(fontSize * 2.2));
  const capBand = $derived(Math.ceil(fontSize * 1.8));
  const padRight = $derived(Math.ceil(fontSize * 1.2));
  // Sotto la misura minima il disegno non si comprime: sborda e il contenitore scorre.
  const plotWidth = $derived(Math.max(sizing.minPlotWidth, availableWidth - axisWidth - padRight));
  const width = $derived(axisWidth + plotWidth + padRight);
  const height = $derived(capBand + sizing.plotHeight + labelBand);

  const stepX = $derived(points.length > 1 ? plotWidth / (points.length - 1) : 0);
  const x = (index: number) => (points.length > 1 ? index * stepX : plotWidth / 2);
  const y = (value: number) => capBand + sizing.plotHeight - (value / yMax) * sizing.plotHeight;

  const paths = $derived(seriesPaths(points, x, y, capBand + sizing.plotHeight));

  /** Mostra una data ogni N, quanto basta perche' due etichette non si tocchino. */
  const labelEvery = $derived.by(() => {
    const widest = Math.max(0, ...points.map((point) => estimateTextWidth(point.label, fontSize)));
    return Math.max(1, Math.ceil((widest + 12) / Math.max(1, stepX)));
  });
  const peakIndex = $derived(
    points.reduce((best, point, index) => (point.value > points[best].value ? index : best), 0)
  );

  function track(event: MouseEvent) {
    if (!plotElement || points.length === 0) return;
    const bounds = plotElement.getBoundingClientRect();
    const ratio = (event.clientX - bounds.left) / Math.max(1, bounds.width);
    const index = Math.min(points.length - 1, Math.max(0, Math.round(ratio * (points.length - 1))));
    activeIndex = index;
    ontooltip?.(
      tooltipFor(event, points[index].label, [
        { label: valueLabel, value: format(points[index].value), color }
      ])
    );
  }

  function hide() {
    activeIndex = null;
    ontooltip?.(null);
  }
</script>

<div class="area-wrap" style:--chart-font={`${fontSize}px`} bind:clientWidth={availableWidth}>
  {#if availableWidth > 0 && points.length > 0}
    <svg {width} {height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
      {#each ticks as tick (tick)}
        <line class="grid" x1={axisWidth} x2={axisWidth + plotWidth} y1={y(tick)} y2={y(tick)}></line>
        <text class="tick" x={axisWidth - 8} y={y(tick)} text-anchor="end" dominant-baseline="middle">
          {tickFormat(tick)}
        </text>
      {/each}

      <g transform={`translate(${axisWidth},0)`}>
        <path class="wash" d={paths.area} fill={color}></path>
        <path class="line" d={paths.line} stroke={color}></path>

        {#if activeIndex !== null}
          <line
            class="crosshair"
            x1={x(activeIndex)}
            x2={x(activeIndex)}
            y1={capBand}
            y2={capBand + sizing.plotHeight}
          ></line>
          <circle class="marker" cx={x(activeIndex)} cy={y(points[activeIndex].value)} r="5" fill={color}></circle>
        {/if}

        <!-- Etichetta diretta sul solo picco: l'asse porta il resto. -->
        {#if maxValue > 0}
          <circle class="marker" cx={x(peakIndex)} cy={y(points[peakIndex].value)} r="4" fill={color}></circle>
          <text
            class="peak"
            x={x(peakIndex)}
            y={y(points[peakIndex].value) - 10}
            text-anchor={peakIndex === 0 ? 'start' : peakIndex === points.length - 1 ? 'end' : 'middle'}
          >
            {format(points[peakIndex].value)}
          </text>
        {/if}

        {#each points as point, index (point.key)}
          {#if index % labelEvery === 0}
            <text
              class="label"
              x={x(index)}
              y={capBand + sizing.plotHeight + fontSize * 1.5}
              text-anchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
            >
              {point.label}
            </text>
          {/if}
        {/each}

        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <rect
          class="hit"
          bind:this={plotElement}
          data-history-hover-exclude
          x="0"
          y={capBand}
          width={plotWidth}
          height={sizing.plotHeight}
          onmousemove={track}
          onmouseleave={hide}
        ></rect>
      </g>
    </svg>
  {/if}
</div>

<style>
  .area-wrap {
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
  .label,
  .peak {
    font-family: var(--font-mono);
    font-size: var(--chart-font);
  }

  .tick,
  .label {
    fill: #94a3b8;
  }

  .peak {
    fill: #0f172a;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .wash {
    opacity: 0.12;
  }

  .line {
    fill: none;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .marker {
    stroke: #ffffff;
    stroke-width: 2;
  }

  .crosshair {
    stroke: #94a3b8;
    stroke-width: 1;
  }

  .hit {
    fill: transparent;
    cursor: crosshair;
  }
</style>
