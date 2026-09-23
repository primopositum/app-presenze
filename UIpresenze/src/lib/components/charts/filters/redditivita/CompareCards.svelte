<script lang="ts">
  /** Grafici di confronto della redditivita' di un contratto, in fondo a "Redditivita'". */
  import BarChart from '../../atoms/BarChart.svelte';
  import ChartCard from '../../atoms/ChartCard.svelte';
  import ChartEmpty from '../../atoms/ChartEmpty.svelte';
  import type { ChartTooltipState } from '../../atoms/tooltip';
  import { fmtHoursAxis, fmtInt, fmtPercent, fmtRate } from '../../format';
  import { CARD_ACCENT } from '../../palette';
  import CompareSummary from '../CompareSummary.svelte';
  import { FOCUS_COLOR } from '../core/compare';
  import type { ProfitabilityComparison } from './compare';

  type Props = {
    comparison: ProfitabilityComparison | null;
    averageRate: number;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let { comparison, averageRate, ontooltip }: Props = $props();
</script>

{#if comparison}
  <CompareSummary
    title={`Confronto · ${comparison.label}`}
    subtitle={`${comparison.client} · contro ${fmtInt(comparison.others)} altri contratti`}
    note={comparison.inScope
      ? 'Il termine di confronto sono i contratti che passano i filtri, questo escluso.'
      : 'Il contratto scelto e\' escluso dai filtri attivi: resta confrontato con i contratti filtrati.'}
    items={[
      { label: 'Tariffa oraria', value: fmtRate(comparison.hourlyRate), hint: `media ${fmtRate(averageRate)}` },
      {
        label: 'Scarto dalla media',
        value: `${comparison.gap >= 0 ? '+' : '−'}${fmtRate(Math.abs(comparison.gap))}`,
        hint: `${comparison.gapPercent >= 0 ? '+' : '−'}${fmtPercent(Math.abs(comparison.gapPercent), 0)}`
      },
      { label: 'Posizione per tariffa', value: `#${fmtInt(comparison.standing.rank)}`, hint: `su ${fmtInt(comparison.standing.total)}` },
      {
        label: 'Percentile',
        value: fmtPercent(comparison.standing.percentile, 0),
        meter: { ratio: comparison.standing.percentile / 100, color: FOCUS_COLOR }
      },
      {
        label: 'Task del pool senza ore',
        value: fmtInt(comparison.missingTasks),
        hint: 'nel periodo selezionato'
      }
    ]}
  />

  <ChartCard
    title="Indice rispetto alla media degli altri"
    subtitle="media = 100"
    accent={FOCUS_COLOR}
    wide
    note="Ogni barra divide il valore del contratto per la media degli altri: 200 vuol dire il doppio, 50 la meta'."
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
    title="Posizione in classifica per tariffa"
    subtitle={`#${fmtInt(comparison.standing.rank)} su ${fmtInt(comparison.standing.total)}`}
    accent={FOCUS_COLOR}
    note="In arancio il contratto scelto; la linea verticale e' la tariffa media."
  >
    <BarChart
      rows={comparison.ranking}
      title="Classifica per tariffa oraria"
      axisFormat={(value) => `${Math.round(value)} €`}
      reference={averageRate > 0 ? { value: averageRate, label: 'media' } : null}
      {ontooltip}
    />
  </ChartCard>

  <ChartCard title="Ore per task del pool" subtitle={`${fmtInt(comparison.tasks.length)} task con ore`} accent={CARD_ACCENT.people}>
    {#if comparison.tasks.length > 0}
      <BarChart rows={comparison.tasks} title="Ore per task del pool" axisFormat={fmtHoursAxis} {ontooltip} />
    {:else}
      <ChartEmpty message="Nessuna task del pool ha ore nel periodo." />
    {/if}
  </ChartCard>
{:else}
  <ChartCard title="Confronto" accent={FOCUS_COLOR} wide>
    <ChartEmpty message="Il contratto scelto non ha ore sulle task del pool nel periodo: la tariffa oraria non si puo' calcolare." />
  </ChartCard>
{/if}
