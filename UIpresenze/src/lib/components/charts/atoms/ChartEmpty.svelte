<script lang="ts">
  /** Messaggio al posto di un grafico senza dati: la card resta, il posto non salta. */
  type Props = { message: string };

  let { message }: Props = $props();
</script>

<p class="chart-empty">{message}</p>

<style>
  .chart-empty {
    display: grid;
    place-items: center;
    min-height: 90px;
    margin: 0;
    border: 1px dashed #e2e8f0;
    border-radius: 8px;
    padding: 0.8rem;
    color: #64748b;
    font-size: 0.72rem;
    font-family: var(--font-mono);
    text-align: center;
  }
</style>
