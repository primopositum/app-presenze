<script lang="ts">
  /** Griglia di prova con tre card, la prima con una classifica lunga. Solo per i test. */
  import BarChart from '../BarChart.svelte';
  import ChartCard from '../ChartCard.svelte';
  import type { ChartRow } from '../../chartData';

  const rows: ChartRow[] = Array.from({ length: 120 }, (_, index) => ({
    id: `r${index}`,
    label: `Voce ${index + 1}`,
    value: 1000 - index,
    percent: 0,
    display: String(1000 - index),
    color: '#2a78d6'
  }));
</script>

<div class="grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 900px">
  <ChartCard title="Classifica">
    <BarChart {rows} limit={12} title="Classifica" />
  </ChartCard>
  <ChartCard title="Seconda">
    <p data-testid="second">Contenuto B</p>
  </ChartCard>
  <ChartCard title="Terza">
    <p data-testid="third">Contenuto C</p>
  </ChartCard>
</div>
