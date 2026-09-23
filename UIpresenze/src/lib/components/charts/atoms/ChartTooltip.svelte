<script lang="ts">
  /**
   * Tooltip unico per tutti i grafici: il valore resta leggibile anche senza.
   * Vive in fondo al body: dentro il cubo la `perspective` sposterebbe il
   * `position: fixed`, e sopra un grafico a schermo intero resterebbe coperto.
   */
  import type { ChartTooltipState } from './tooltip';
  import { portal } from './cardExpansion';

  type Props = { tooltip: ChartTooltipState | null };

  let { tooltip }: Props = $props();
</script>

{#if tooltip}
  <!-- L'ancora resta qui, il tooltip va nel body: vedi `portal`. -->
  <div class="portal-anchor">
    <div class="chart-tooltip" use:portal style={`left:${tooltip.x}px; top:${tooltip.y}px;`} role="tooltip">
      <strong>{tooltip.title}</strong>
      {#each tooltip.values as entry, index (entry.label ?? index)}
        <span class="value">
          {#if entry.color}<i class="swatch" style:background={entry.color}></i>{/if}
          {#if entry.label}<em>{entry.label}</em>{/if}
          {entry.value}
        </span>
      {/each}
      {#if tooltip.hint}<small>{tooltip.hint}</small>{/if}
    </div>
  </div>
{/if}

<style>
  .portal-anchor {
    display: contents;
  }

  .chart-tooltip {
    position: fixed;
    z-index: 1300;
    display: grid;
    gap: 3px;
    width: max-content;
    max-width: 240px;
    padding: 8px 10px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.16);
    color: #0f172a;
    font-family: var(--font-mono);
    pointer-events: none;
  }

  .chart-tooltip strong {
    overflow: hidden;
    font-size: 0.72rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .value {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 0.74rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .value em {
    color: #64748b;
    font-style: normal;
    font-weight: 400;
  }

  .swatch {
    flex: none;
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }

  .chart-tooltip small {
    max-width: 220px;
    color: #64748b;
    font-size: 0.66rem;
    line-height: 1.35;
  }
</style>
