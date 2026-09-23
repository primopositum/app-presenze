<script lang="ts">
  /**
   * Ciambella + legenda. Misura lo spazio che ha e applica gli standard della
   * modalita' di rendering: sotto la soglia mette la legenda sotto al grafico
   * invece di stringerla, e la ciambella non scende mai sotto la sua misura.
   *
   * Grafico e legenda condividono l'evidenziazione: puntare una voce accende
   * anche l'altra, cosi' l'identita' non si gioca sul solo colore.
   */
  import type { ChartRow } from '../chartData';
  import { DONUT_SIZING, resolveRenderMode, type ChartRenderMode } from '../chartSizing';
  import ChartLegend from './ChartLegend.svelte';
  import DonutChart from './DonutChart.svelte';
  import { tooltipAt, type ChartTooltipState } from './tooltip';

  type Props = {
    rows: ChartRow[];
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
    mode = 'auto',
    showValue = true,
    centerValue,
    centerLabel,
    title,
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeId = $state<string | null>(null);

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(DONUT_SIZING[renderMode]);
  const stacked = $derived(availableWidth > 0 && availableWidth < sizing.stackBelow);

  function show(event: MouseEvent, row: ChartRow) {
    activeId = row.id;
    ontooltip?.(tooltipAt(event, row));
  }

  function hide() {
    activeId = null;
    ontooltip?.(null);
  }
</script>

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
</style>
