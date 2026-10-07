<script lang="ts">
  /**
   * Cornice comune alle schermate del cubo: titolo, riga delle cifre e griglia
   * dei grafici.
   *
   * Durante un aggiornamento i grafici restano a schermo, un po' piu' tenui:
   * sostituirli con uno scheletro farebbe lampeggiare la faccia a ogni ricarica.
   */
  import type { Snippet } from 'svelte';

  type Props = {
    title: string;
    subtitle?: string;
    /** Prima carica: non c'e' ancora niente da mostrare. */
    loading?: boolean;
    /** Ricarica con i dati gia' a schermo. */
    refreshing?: boolean;
    error?: string;
    empty?: boolean;
    emptyMessage?: string;
    metrics?: Snippet;
    children?: Snippet;
  };

  let {
    title,
    subtitle,
    loading = false,
    refreshing = false,
    error = '',
    empty = false,
    emptyMessage = 'Nessun dato disponibile per il periodo selezionato.',
    metrics,
    children
  }: Props = $props();
</script>

<section class="chart-screen">
  <header class="screen-head">
    <div>
      <h3>{title}</h3>
      {#if subtitle}<p>{subtitle}</p>{/if}
    </div>
    {#if refreshing}<span class="badge">Aggiornamento…</span>{/if}
  </header>

  {#if metrics && !loading && !error}
    <div class="metric-grid">{@render metrics()}</div>
  {/if}

  {#if error}
    <p class="state error" data-history-hover>{error}</p>
  {:else if loading}
    <p class="state" data-history-hover>Caricamento dati…</p>
  {:else if empty}
    <p class="state" data-history-hover>{emptyMessage}</p>
  {:else}
    <div class="charts-grid" class:stale={refreshing}>{@render children?.()}</div>
  {/if}
</section>

<style>
  .chart-screen {
    display: grid;
    align-content: start;
    gap: 0.75rem;
    padding: 0.95rem;
    min-width: 0;
  }

  .screen-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .screen-head h3 {
    margin: 0;
    color: #0f172a;
    font-size: 0.92rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-family: var(--font-mono);
  }

  .screen-head p {
    margin: 0.25rem 0 0;
    color: #64748b;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }

  .badge {
    flex: 0 0 auto;
    border-radius: 999px;
    padding: 0.15rem 0.5rem;
    background: #f1f5f9;
    color: #64748b;
    font-size: 0.64rem;
    font-family: var(--font-mono);
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(146px, 1fr));
    gap: 8px;
  }

  /*
   * Le card hanno una larghezza minima: finche' ci stanno si affiancano, poi
   * vanno su una colonna sola e, se anche quella non basta, la faccia scorre.
   * Cosi' i grafici non vengono compressi fino a diventare illeggibili.
   * Le card affiancate prendono l'altezza della piu' alta della riga: il
   * contenuto resta in testa, la cornice si allunga.
   */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(var(--chart-card-min, 360px), 1fr));
    align-items: stretch;
    gap: 0.7rem;
    transition: opacity 160ms ease;
  }

  .charts-grid.stale {
    opacity: 0.6;
  }

  .state {
    margin: 0;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 0.9rem;
    color: #64748b;
    font-size: 0.78rem;
    font-family: var(--font-mono);
  }

  .state.error {
    border-style: solid;
    border-color: #fecaca;
    background: #fef2f2;
    color: #b91c1c;
  }
</style>
