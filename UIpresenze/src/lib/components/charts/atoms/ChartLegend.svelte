<script lang="ts">
  /**
   * Legenda: il canale di identita' affidabile. C'e' sempre quando le serie sono
   * due o piu', perche' nessuna lettura deve dipendere dal solo colore.
   */
  import { fmtPercent } from '../format';
  import type { ChartRow } from '../chartData';

  type Props = {
    rows: ChartRow[];
    /** Mostra anche il valore formattato accanto alla quota. */
    showValue?: boolean;
    maxHeight?: string;
    activeId?: string | null;
    onhover?: (event: MouseEvent, row: ChartRow) => void;
    onleave?: () => void;
  };

  let { rows, showValue = true, maxHeight, activeId = null, onhover, onleave }: Props = $props();
</script>

<ul class="legend" class:with-value={showValue} style:max-height={maxHeight}>
  {#each rows as row (row.id)}
    <li
      class:dimmed={activeId !== null && activeId !== row.id}
      data-history-hover-exclude
      onmouseenter={(event) => onhover?.(event, row)}
      onmousemove={(event) => onhover?.(event, row)}
      onmouseleave={() => onleave?.()}
    >
      <span class="dot" style:--dot={row.color}></span>
      <span class="name" title={row.label}>{row.label}</span>
      {#if showValue}<span class="value">{row.display}</span>{/if}
      <span class="share">{fmtPercent(row.percent)}</span>
    </li>
  {/each}
</ul>

<style>
  .legend {
    min-width: 150px;
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    align-content: start;
    gap: 5px;
    overflow: auto;
  }

  .legend li {
    display: grid;
    grid-template-columns: 10px minmax(0, 1fr) auto;
    align-items: center;
    gap: 7px;
    font-size: 0.7rem;
    color: #475569;
    font-family: var(--font-mono);
    transition: opacity 140ms ease;
  }

  .legend.with-value li {
    grid-template-columns: 10px minmax(0, 1fr) auto auto;
  }

  .legend li.dimmed {
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

  .value {
    color: #475569;
    font-variant-numeric: tabular-nums;
  }

  .share {
    color: #0f172a;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
</style>
