<script lang="ts">
  /**
   * Testata del confronto: apre il blocco di grafici in fondo alla schermata
   * con le cifre che dicono dove sta la voce scelta rispetto alle altre.
   * Il filo arancio e' lo stesso della barra evidenziata nelle classifiche.
   */
  import ChartCard from '../atoms/ChartCard.svelte';
  import MetricCard from '../atoms/MetricCard.svelte';
  import { FOCUS_COLOR } from './core/compare';

  type Item = {
    label: string;
    value: string;
    hint?: string;
    lead?: boolean;
    meter?: { ratio: number; color?: string } | null;
  };

  type Props = {
    title: string;
    subtitle?: string;
    items: Item[];
    note?: string;
  };

  let { title, subtitle, items, note }: Props = $props();
</script>

<ChartCard {title} {subtitle} accent={FOCUS_COLOR} wide {note}>
  <div class="compare-grid">
    {#each items as item (item.label)}
      <MetricCard label={item.label} value={item.value} hint={item.hint} lead={item.lead} meter={item.meter} />
    {/each}
  </div>
</ChartCard>

<style>
  .compare-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(146px, 1fr));
    gap: 8px;
  }
</style>
