<script lang="ts">
  /**
   * Grafici di confronto di una task con le altre, in fondo alla schermata.
   * Nessun contenitore proprio: le card entrano nella griglia della schermata.
   */
  import AreaLineChart from '../../atoms/AreaLineChart.svelte';
  import BarChart from '../../atoms/BarChart.svelte';
  import ChartCard from '../../atoms/ChartCard.svelte';
  import ChartEmpty from '../../atoms/ChartEmpty.svelte';
  import type { ChartTooltipState } from '../../atoms/tooltip';
  import { fmtHours, fmtHoursAxis, fmtInt, fmtPercent } from '../../format';
  import { CARD_ACCENT, SERIES } from '../../palette';
  import CompareSummary from '../CompareSummary.svelte';
  import { FOCUS_COLOR } from './compare';
  import { deviationLabel, type IssueComparison } from './issueCompare';

  type Props = {
    comparison: IssueComparison;
    focusKey: string;
    /** "issue" o "task CM": come chiamare le altre voci nei testi. */
    noun?: string;
    ontooltip?: (tooltip: ChartTooltipState | null) => void;
  };

  let { comparison, focusKey, noun = 'issue', ontooltip }: Props = $props();
</script>

{#if comparison}
  <CompareSummary
    title={`Confronto · ${comparison.label}`}
    subtitle={`contro ${fmtInt(comparison.others)} altre ${noun}`}
    note="Il confronto usa lo stesso perimetro dei grafici sopra: stessi filtri, stesso periodo."
    items={[
      { label: 'Ore loggate', value: fmtHours(comparison.seconds), hint: `media altre ${fmtHours(comparison.averageSeconds)}` },
      {
        label: 'Posizione per ore',
        value: `#${fmtInt(comparison.standing.rank)}`,
        hint: `su ${fmtInt(comparison.standing.total)}`
      },
      {
        label: 'Percentile',
        value: fmtPercent(comparison.standing.percentile, 0),
        hint: `sopra al ${fmtPercent(comparison.standing.percentile, 0)} delle altre`,
        meter: { ratio: comparison.standing.percentile / 100, color: FOCUS_COLOR }
      },
      {
        label: 'Quota sulle ore totali',
        value: fmtPercent(comparison.share * 100),
        meter: { ratio: comparison.share, color: FOCUS_COLOR }
      },
      comparison.estimate
        ? {
            label: 'Stima originale',
            value: fmtHours(comparison.estimate.seconds),
            hint: deviationLabel(comparison.estimate.deviation)
          }
        : { label: 'Stima originale', value: '—', hint: 'non impostata in Jira' }
    ]}
  />

  <ChartCard
    title="Indice rispetto alla media delle altre"
    subtitle="media = 100"
    accent={FOCUS_COLOR}
    wide
    note="Ogni barra divide il valore della task per la media delle altre: 200 vuol dire il doppio, 50 la meta'. Misure diverse, stessa scala."
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
      <ChartEmpty message={`Non ci sono altre ${noun} con cui confrontarla.`} />
    {/if}
  </ChartCard>

  <ChartCard
    title={`Andamento della task per ${comparison.bucketName}`}
    subtitle={fmtHours(comparison.seconds)}
    accent={CARD_ACCENT.time}
  >
    {#if comparison.timeline.length > 1}
      <AreaLineChart
        points={comparison.timeline}
        title={`Ore su ${focusKey} per ${comparison.bucketName}`}
        format={fmtHours}
        axisFormat={fmtHoursAxis}
        color={FOCUS_COLOR}
        valueLabel="ore"
        {ontooltip}
      />
    {:else}
      <ChartEmpty message="Serve piu' di un periodo con worklog per disegnare un andamento." />
    {/if}
  </ChartCard>

  <ChartCard title="Ore per persona sulla task" subtitle={`${fmtInt(comparison.people.length)} persone`} accent={CARD_ACCENT.people}>
    {#if comparison.people.length > 0}
      <BarChart rows={comparison.people} title={`Ore per persona su ${focusKey}`} axisFormat={fmtHoursAxis} {ontooltip} />
    {:else}
      <ChartEmpty message="Nessun worklog con autore sulla task." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Posizione in classifica per ore"
    subtitle={`#${fmtInt(comparison.standing.rank)} su ${fmtInt(comparison.standing.total)}`}
    accent={SERIES[1]}
    wide
    note="In arancio la task scelta; se e' fuori dalle prime posizioni compare in fondo con il suo numero."
  >
    <BarChart rows={comparison.ranking} title="Classifica per ore" axisFormat={fmtHoursAxis} {ontooltip} />
  </ChartCard>
{:else}
  <ChartCard title="Confronto" accent={FOCUS_COLOR} wide>
    <ChartEmpty
      message={`${focusKey} non ha ore nel perimetro attuale: e' esclusa dai filtri o non ha worklog nel periodo.`}
    />
  </ChartCard>
{/if}
