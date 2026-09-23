<script lang="ts">
  /**
   * Ciambella: parte-sul-tutto a colpo d'occhio, mai per confrontare valori vicini.
   * Chi la usa tiene gli spicchi entro sei (vedi `withOther`).
   * Gli spicchi si separano con un vuoto nel colore della superficie, non con un bordo.
   */
  import { arc, pie, type PieArcDatum } from 'd3';
  import type { ChartRow } from '../chartData';

  type Props = {
    rows: ChartRow[];
    size?: number;
    innerRadius?: number;
    outerRadius?: number;
    /** Testo grande al centro: il totale che gli spicchi compongono. */
    centerValue?: string;
    centerLabel?: string;
    title: string;
    activeId?: string | null;
    onhover?: (event: MouseEvent, row: ChartRow) => void;
    onleave?: () => void;
  };

  let {
    rows,
    size = 232,
    innerRadius = 68,
    outerRadius = 108,
    centerValue,
    centerLabel,
    title,
    activeId = null,
    onhover,
    onleave
  }: Props = $props();

  const layout = $derived(
    pie<ChartRow>()
      .sort(null)
      .padAngle(2 / Math.max(1, outerRadius))
      .value((row: ChartRow) => row.value)(rows)
  );
  const arcPath = $derived(
    arc<PieArcDatum<ChartRow>>().innerRadius(innerRadius).outerRadius(outerRadius).cornerRadius(2)
  );
</script>

<svg
  class="donut-svg"
  width={size}
  height={size}
  viewBox={`0 0 ${size} ${size}`}
  role="img"
  aria-label={title}
>
  <g transform={`translate(${size / 2},${size / 2})`}>
    {#each layout as slice (slice.data.id)}
      <!-- Il grafico ha gia' un ruolo img con la sua aria-label: gli spicchi sono decorativi. -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <path
        class="segment"
        class:dimmed={activeId !== null && activeId !== slice.data.id}
        data-history-hover-exclude
        d={arcPath(slice) || ''}
        fill={slice.data.color}
        onmouseenter={(event) => onhover?.(event, slice.data)}
        onmousemove={(event) => onhover?.(event, slice.data)}
        onmouseleave={() => onleave?.()}
      ></path>
    {/each}

    {#if centerValue}
      <text class="center-value" text-anchor="middle" dy={centerLabel ? '-0.05em' : '0.35em'}>
        {centerValue}
      </text>
      {#if centerLabel}
        <text class="center-label" text-anchor="middle" dy="1.35em">{centerLabel}</text>
      {/if}
    {/if}
  </g>
</svg>

<style>
  .donut-svg {
    max-width: 100%;
    height: auto;
  }

  .segment {
    cursor: pointer;
    transition: opacity 140ms ease;
  }

  .dimmed {
    opacity: 0.35;
  }

  .center-value {
    fill: #0f172a;
    font-family: var(--font-mono);
    font-size: 0.92rem;
    font-weight: 700;
  }

  .center-label {
    fill: #64748b;
    font-family: var(--font-mono);
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
</style>
