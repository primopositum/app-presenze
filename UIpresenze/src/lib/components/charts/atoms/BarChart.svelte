<script lang="ts">
  /**
   * Barre orizzontali: la forma piu' robusta dentro una faccia del cubo, perche'
   * cresce in verticale (dove si scorre) e tiene le etichette dritte e leggibili.
   *
   * Si misura da sola e applica gli standard della modalita' di rendering:
   * passo riga, corpo del testo e larghezza minima dell'area barre restano
   * fissi; quando non ci stanno, il contenitore scorre.
   */
  import { barLayout, barPath, type ChartRow } from '../chartData';
  import { BAR_SIZING, resolveRenderMode, type ChartRenderMode } from '../chartSizing';
  import { tooltipAt, type ChartTooltipState } from './tooltip';
  import { useCardExpansion } from './cardExpansion';

  type Props = {
    /** Tutte le righe: il taglio lo fa il grafico, cosi' a schermo intero ne mostra di piu'. */
    rows: ChartRow[];
    /** Voci mostrate nella card: a schermo intero diventano 30, poi di piu' scorrendo. */
    limit?: number;
    /** 'auto' sceglie in base alla larghezza disponibile. */
    mode?: ChartRenderMode | 'auto';
    /** Formattazione delle tacche dell'asse: di default quella dei valori. */
    axisFormat?: (value: number) => string;
    /** Riferimento verticale, es. la media: valore e etichetta. */
    reference?: { value: number; label: string } | null;
    /**
     * Allarga la scala fino al riferimento. Serve quando il riferimento e' il
     * punto di confronto (es. indice 100 = media) e deve vedersi sempre.
     */
    includeReference?: boolean;
    /** Limita l'altezza visibile: di default il grafico cresce e scorre la schermata. */
    maxHeight?: string;
    title: string;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let {
    rows,
    limit,
    mode = 'auto',
    axisFormat,
    reference = null,
    includeReference = false,
    maxHeight,
    title,
    ontooltip
  }: Props = $props();

  let availableWidth = $state(0);
  let activeId = $state<string | null>(null);

  const card = useCardExpansion();
  const shownRows = $derived(
    card?.expanded ? rows.slice(0, card.limit) : limit ? rows.slice(0, limit) : rows
  );

  $effect(() => {
    card?.reportTotal(rows.length);
  });

  const renderMode = $derived(mode === 'auto' ? resolveRenderMode(availableWidth) : mode);
  const sizing = $derived(BAR_SIZING[renderMode]);
  const tickFormat = $derived(axisFormat ?? ((value: number) => String(Math.round(value))));
  const layout = $derived(
    barLayout(
      shownRows,
      availableWidth,
      sizing,
      tickFormat,
      includeReference && reference ? reference.value : 0
    )
  );
  // Il riferimento entra nel disegno solo se cade dentro la scala gia' calcolata.
  const referenceX = $derived(
    reference && reference.value > 0 && reference.value <= layout.x.domain()[1]
      ? layout.x(reference.value)
      : null
  );
  // La sua didascalia sta sotto l'ultima riga: senza fascia dedicata verrebbe tagliata.
  const referenceBand = $derived(referenceX === null ? 0 : Math.ceil(layout.fontSize * 1.7));
  const svgHeight = $derived(layout.height + referenceBand);

  function show(event: MouseEvent, row: ChartRow) {
    activeId = row.id;
    ontooltip?.(tooltipAt(event, row));
  }

  function hide() {
    activeId = null;
    ontooltip?.(null);
  }
</script>

<div
  class="bar-wrap"
  style:--chart-font={`${layout.fontSize}px`}
  style:max-height={maxHeight}
  bind:clientWidth={availableWidth}
>
  {#if availableWidth > 0}
    <svg
      width={layout.width}
      height={svgHeight}
      viewBox={`0 0 ${layout.width} ${svgHeight}`}
      role="img"
      aria-label={title}
    >
      <g transform={`translate(${layout.labelWidth},0)`}>
        <!-- Griglia a filo: porta i valori che non sono etichettati sulle barre. -->
        {#each layout.ticks as tick (tick)}
          <line
            class="grid"
            x1={layout.x(tick)}
            x2={layout.x(tick)}
            y1={layout.axisTop - 6}
            y2={layout.axisTop + layout.plotHeight}
          ></line>
          <text class="tick" x={layout.x(tick)} y={layout.axisTop - 12} text-anchor="middle">
            {layout.tickLabel(tick)}
          </text>
        {/each}

        {#if referenceX !== null}
          <line
            class="reference"
            x1={referenceX}
            x2={referenceX}
            y1={layout.axisTop - 6}
            y2={layout.axisTop + layout.plotHeight}
          ></line>
          <text
            class="reference-label"
            x={referenceX}
            y={layout.axisTop + layout.plotHeight + layout.fontSize * 1.2}
            text-anchor="middle"
          >
            {reference?.label}
          </text>
        {/if}
      </g>

      <g transform={`translate(${layout.labelWidth},${layout.axisTop})`}>
        {#each shownRows as row (row.id)}
          {@const bandY = layout.y(row.id) || 0}
          {@const barY = bandY + (layout.y.bandwidth() - layout.barHeight) / 2}
          {@const barWidth = layout.x(row.value)}
          {@const centerY = bandY + layout.y.bandwidth() / 2}
          <!-- Una riga sola e' il bersaglio del puntatore: la barra sottile sarebbe troppo piccola. -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <g
            class="row"
            class:active={activeId === row.id}
            data-history-hover-exclude
            onmouseenter={(event) => show(event, row)}
            onmousemove={(event) => show(event, row)}
            onmouseleave={hide}
          >
            <rect
              class="hit"
              x={-layout.labelWidth}
              y={bandY}
              width={layout.width}
              height={layout.y.bandwidth()}
            ></rect>
            <path class="bar" transform={`translate(0,${barY})`} d={barPath(barWidth, layout.barHeight)} fill={row.color}></path>
            <text class="label" x={-10} y={centerY} text-anchor="end" dominant-baseline="middle">
              {layout.labelText(row.label)}
              <title>{row.label}</title>
            </text>
            <text class="value" x={barWidth + 8} y={centerY} dominant-baseline="middle">
              {row.display}
            </text>
          </g>
        {/each}
      </g>
    </svg>
  {/if}
</div>

<style>
  /*
   * Scorre in orizzontale quando le barre non ci stanno in larghezza; in altezza
   * cresce con le righe e lascia scorrere la schermata, invece di aprire un
   * secondo scorrimento dentro la card.
   */
  .bar-wrap {
    overflow: auto;
  }

  svg {
    display: block;
  }

  .grid {
    stroke: var(--chart-grid, #e7ecf2);
    stroke-width: 1;
    shape-rendering: crispEdges;
  }

  .reference {
    stroke: #94a3b8;
    stroke-width: 1.5;
  }

  .label,
  .value,
  .tick,
  .reference-label {
    font-size: var(--chart-font);
    font-family: var(--font-mono);
  }

  .label {
    fill: #475569;
  }

  .value {
    fill: #0f172a;
    font-variant-numeric: tabular-nums;
  }

  .tick,
  .reference-label {
    fill: #94a3b8;
    font-size: calc(var(--chart-font) * 0.92);
  }

  .hit {
    fill: transparent;
  }

  .row {
    cursor: pointer;
  }

  .row .bar {
    transition: opacity 140ms ease;
  }

  .row.active .hit {
    fill: rgba(15, 23, 42, 0.04);
  }

  .row.active .bar {
    opacity: 0.82;
  }
</style>
