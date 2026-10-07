<script lang="ts">
  /** Grafici di confronto di un contratto con gli altri, in fondo a "Contratti". */
  import BarChart from '../../atoms/BarChart.svelte';
  import ChartCard from '../../atoms/ChartCard.svelte';
  import ChartEmpty from '../../atoms/ChartEmpty.svelte';
  import ColumnChart from '../../atoms/ColumnChart.svelte';
  import type { ChartTooltipState } from '../../atoms/tooltip';
  import { fmtDays, fmtEuro, fmtEuroAxis, fmtInt, fmtPercent } from '../../format';
  import CompareSummary from '../CompareSummary.svelte';
  import { FOCUS_COLOR } from '../core/compare';
  import type { ContractComparison } from './compare';

  type Props = {
    comparison: ContractComparison | null;
    forecastMonths: number;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let { comparison, forecastMonths, ontooltip }: Props = $props();

  const forecastTotal = $derived(
    comparison ? comparison.forecast.reduce((sum, point) => sum + point.value, 0) : 0
  );
</script>

{#if comparison}
  <CompareSummary
    title={`Confronto · ${comparison.label}`}
    subtitle={`${comparison.client} · contro ${fmtInt(comparison.others)} altri contratti`}
    note={comparison.inScope
      ? 'Il termine di confronto sono i contratti che passano i filtri, questo escluso.'
      : 'Il contratto scelto e\' escluso dai filtri attivi: resta confrontato con i contratti filtrati.'}
    items={[
      { label: 'Valore da compensi periodici', value: fmtEuro(comparison.value), hint: `media altri ${fmtEuro(comparison.averageValue)}` },
      { label: 'Posizione per valore', value: `#${fmtInt(comparison.standing.rank)}`, hint: `su ${fmtInt(comparison.standing.total)}` },
      {
        label: 'Percentile',
        value: fmtPercent(comparison.standing.percentile, 0),
        meter: { ratio: comparison.standing.percentile / 100, color: FOCUS_COLOR }
      },
      {
        label: 'Quota sul valore totale',
        value: fmtPercent(comparison.share * 100),
        meter: { ratio: comparison.share, color: FOCUS_COLOR }
      },
      {
        label: 'Stato',
        value: comparison.status,
        hint:
          comparison.daysLeft === null
            ? 'senza data di fine'
            : comparison.daysLeft >= 0
              ? `scade fra ${fmtDays(comparison.daysLeft)}`
              : `scaduto da ${fmtDays(-comparison.daysLeft)}`
      }
    ]}
  />

  <ChartCard
    title="Indice rispetto alla media degli altri"
    subtitle="media = 100"
    accent={FOCUS_COLOR}
    wide
    note="Ogni barra divide il valore del contratto per la media degli altri: 200 vuol dire il doppio, 50 la meta'. Le misure che gli altri non hanno (es. nessun canone) restano fuori."
  >
    {#if comparison.index.length > 0}
      <BarChart
        rows={comparison.index}
        title="Indice rispetto alla media"
        axisFormat={(value) => fmtInt(value)}
        reference={{ value: 100, label: 'media' }}
        includeReference
        {ontooltip}
      />
    {:else}
      <ChartEmpty message="Non ci sono altri contratti con cui confrontarlo." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Posizione in classifica per valore da compensi periodici"
    subtitle={`#${fmtInt(comparison.standing.rank)} su ${fmtInt(comparison.standing.total)}`}
    accent={FOCUS_COLOR}
    note="In arancio il contratto scelto; se e' fuori dalle prime posizioni compare in fondo con il suo numero."
  >
    <BarChart rows={comparison.ranking} title="Classifica per valore da compensi periodici" axisFormat={fmtEuroAxis} {ontooltip} />
  </ChartCard>

  <ChartCard
    title={`Incassi previsti del contratto, ${forecastMonths} mesi`}
    subtitle={fmtEuro(forecastTotal)}
    accent={FOCUS_COLOR}
  >
    {#if forecastTotal > 0}
      <ColumnChart
        points={comparison.forecast}
        title="Incassi previsti del contratto per mese"
        format={fmtEuro}
        axisFormat={fmtEuroAxis}
        color={FOCUS_COLOR}
        valueLabel="previsto"
        {ontooltip}
      />
    {:else}
      <ChartEmpty message="Il contratto non ha una periodicita' con incassi nel periodo di previsione." />
    {/if}
  </ChartCard>
{:else}
  <ChartCard title="Confronto" accent={FOCUS_COLOR} wide>
    <ChartEmpty message="Il contratto scelto non e' piu' tra quelli caricati." />
  </ChartCard>
{/if}
