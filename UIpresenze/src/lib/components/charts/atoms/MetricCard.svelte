<script lang="ts">
  /**
   * Riquadro di una singola cifra: etichetta, valore e, quando serve, un
   * contesto. Una cifra sola non merita un grafico a una barra.
   *
   * `meter` disegna un rapporto rispetto a un limite: la parte piena e il
   * fondo sono due gradini della stessa scala, cosi' lo stato si legge su
   * tutta la barra.
   */
  import { ACCENT } from '../palette';

  type Props = {
    label: string;
    value: string | number;
    hint?: string;
    /** Cifra di testa della schermata: una sola per faccia. */
    lead?: boolean;
    meter?: { ratio: number; color?: string } | null;
  };

  let { label, value, hint, lead = false, meter = null }: Props = $props();

  const ratio = $derived(Math.min(1, Math.max(0, meter?.ratio ?? 0)));
</script>

<article class="metric-card" class:lead data-history-hover>
  <span class="label">{label}</span>
  <strong>{value}</strong>
  {#if meter}
    <div
      class="meter"
      role="meter"
      aria-valuenow={Math.round(ratio * 100)}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-label={label}
    >
      <span style:width={`${ratio * 100}%`} style:background={meter.color ?? ACCENT}></span>
    </div>
  {/if}
  {#if hint}<small>{hint}</small>{/if}
</article>

<style>
  .metric-card {
    display: grid;
    align-content: start;
    gap: 0.2rem;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.55rem 0.7rem;
    background: #ffffff;
  }

  .label {
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  strong {
    color: #0f172a;
    font-size: 1.15rem;
    line-height: 1.15;
  }

  /* La cifra di testa: proporzionale, non tabellare, perche' sta da sola. */
  .lead strong {
    font-size: 1.7rem;
  }

  .lead {
    background: #f1f5f9;
    border-color: #cbd5e1;
  }

  .meter {
    height: 5px;
    margin-top: 0.15rem;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .meter span {
    display: block;
    height: 100%;
    border-radius: 999px;
  }

  small {
    color: #64748b;
    font-size: 0.64rem;
    font-family: var(--font-mono);
    line-height: 1.3;
  }
</style>
