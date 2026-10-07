<script lang="ts">
  /**
   * Schermata B del cubo: i contratti commerciali.
   *
   * Il grafico per contratto mostra il solo valore maturato. Affiancare anche il
   * valore iniziale raddoppiava le barre per dire una cosa che il riquadro delle
   * cifre gia' dice, e con molti contratti dimezzava lo spazio di ognuna.
   */
  import { onMount } from 'svelte';
  import { chartsData, ensureContrattiLoaded } from '$lib/remo/chartsData';
  import { withOther } from '../chartData';
  import { fmtEuro, fmtEuroAxis, fmtInt, fmtDays } from '../format';
  import { CARD_ACCENT, SERIES } from '../palette';
  import {
    clientValueRows,
    contractInitialValue,
    contractValueRows,
    contractsSummary,
    expiryRows,
    forecastByClient,
    forecastStack,
    forecastUntilYearEnd,
    signedByMonth
  } from '../contractsSelectors';
  import { activeCount, chartFilters, resolveValues } from '../filters/core/filterState';
  import {
    applyContrattiFilters,
    contrattiDisplay,
    contrattiFilters as FILTERS
  } from '../filters/contratti/apply';
  import { compareContract } from '../filters/contratti/compare';
  import ContractCompareCards from '../filters/contratti/CompareCards.svelte';
  import AreaLineChart from '../atoms/AreaLineChart.svelte';
  import BarChart from '../atoms/BarChart.svelte';
  import ChartCard from '../atoms/ChartCard.svelte';
  import ChartEmpty from '../atoms/ChartEmpty.svelte';
  import ChartScreenLayout from '../atoms/ChartScreenLayout.svelte';
  import ChartTooltip from '../atoms/ChartTooltip.svelte';
  import ColumnChart from '../atoms/ColumnChart.svelte';
  import DonutPanel from '../atoms/DonutPanel.svelte';
  import MetricCard from '../atoms/MetricCard.svelte';
  import StackedColumnChart from '../atoms/StackedColumnChart.svelte';
  import type { ChartTooltipState } from '../atoms/tooltip';

  type Props = {
    /** Data di riferimento per contratti attivi, scadenze e previsione. */
    referenceDate?: Date;
    expiringDays?: number;
    forecastMonths?: number;
    topCount?: number;
  };

  let {
    referenceDate: defaultReferenceDate = new Date(),
    expiringDays: defaultExpiringDays = 90,
    forecastMonths: defaultForecastMonths = 12,
    topCount: defaultTopCount = 12
  }: Props = $props();

  let tooltip = $state<ChartTooltipState | null>(null);

  const filters = $derived(resolveValues(FILTERS, $chartFilters[FILTERS.id]));
  const filterCount = $derived(activeCount(FILTERS, $chartFilters[FILTERS.id]));
  const display = $derived(
    contrattiDisplay(filters, {
      referenceDate: defaultReferenceDate,
      expiringDays: defaultExpiringDays,
      forecastMonths: defaultForecastMonths,
      topCount: defaultTopCount
    })
  );
  const referenceDate = $derived(display.referenceDate);
  const expiringDays = $derived(display.expiringDays);
  const forecastMonths = $derived(display.forecastMonths);
  const topCount = $derived(display.topCount);
  const expiryHorizon = $derived(display.expiryHorizon);
  const donutSlices = $derived(display.donutSlices);

  onMount(() => {
    void ensureContrattiLoaded().catch(() => undefined);
  });

  const allContracts = $derived($chartsData.contratti);
  const contracts = $derived(applyContrattiFilters(allContracts, filters, referenceDate));
  const summary = $derived(contractsSummary(contracts, referenceDate, expiringDays));
  const valueByContract = $derived(contractValueRows(contracts));
  // Solo il valore firmato: i compensi periodici maturati restano fuori dalla ciambella.
  const valueByClient = $derived(clientValueRows(contracts, contractInitialValue));
  const expiries = $derived(expiryRows(contracts, referenceDate, expiryHorizon));
  /** Ogni colonna divisa per cliente: i primi cinque con la loro tinta, il resto in "Altri". */
  const forecastClients = $derived(forecastByClient(contracts, referenceDate, forecastMonths));
  const forecast = $derived(forecastStack(forecastClients, 6));
  const forecastTotal = $derived(forecast.total);
  const yearEnd = $derived(forecastUntilYearEnd(contracts, referenceDate));
  const yearEndTotal = $derived(yearEnd.reduce((total, point) => total + point.value, 0));
  const nextExpiry = $derived(expiries[0] ?? null);
  const signedYear = $derived(display.signedYear);
  const signed = $derived(signedByMonth(contracts, signedYear));
  const signedTotal = $derived(signed.reduce((total, point) => total + point.value, 0));
  const comparison = $derived(
    display.compareId
      ? compareContract(allContracts, contracts, display.compareId, display)
      : null
  );
</script>

<ChartScreenLayout
  title="Contratti commerciali"
  subtitle={filterCount > 0
    ? `${fmtInt(contracts.length)} contratti su ${fmtInt(allContracts.length)} · ${filterCount} filtri dal pannello`
    : 'Valore maturato, canoni ricorrenti, incassi previsti e scadenze.'}
  loading={$chartsData.contrattiLoading}
  refreshing={$chartsData.contrattiRefreshing}
  error={$chartsData.contrattiError}
  empty={contracts.length === 0}
  emptyMessage={allContracts.length > 0
    ? 'Nessun contratto passa i filtri attivi: allargali dal pannello filtri.'
    : 'Nessun contratto commerciale registrato.'}
>
  {#snippet metrics()}
    <MetricCard label="Valore da compensi periodici" value={fmtEuro(summary.currentValue)} lead />
    <MetricCard
      label="Contratti attivi"
      value={fmtInt(summary.active.length)}
      hint={`${fmtInt(contracts.length)} in archivio`}
    />
    <MetricCard
      label="Da compensi periodici oltre il firmato"
      value={fmtEuro(summary.accruedValue)}
      hint={`firmato ${fmtEuro(summary.initialValue)}`}
    />
    <MetricCard
      label="Canone mensile"
      value={fmtEuro(summary.monthlyRecurring)}
      hint="normalizzato a 30 giorni"
    />
    <MetricCard
      label={`In scadenza entro ${expiringDays} gg`}
      value={fmtInt(summary.expiring.length)}
      hint={nextExpiry ? `prossima fra ${fmtDays(nextExpiry.value)}` : 'nessuna scadenza fissata'}
    />
  {/snippet}

  <ChartCard
    title="Valore da compensi periodici per contratto"
    subtitle={`${fmtInt(valueByContract.length)} contratti`}
    accent={CARD_ACCENT.money}
    wide
    note={valueByContract.length > topCount
      ? `In classifica i primi ${topCount}: apri il grafico a schermo intero per l'elenco completo.`
      : undefined}
  >
    <BarChart
      rows={valueByContract}
      limit={topCount}
      title="Valore da compensi periodici per contratto"
      axisFormat={fmtEuroAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title={`Incassi previsti, prossimi ${forecastMonths} mesi`}
    subtitle={fmtEuro(forecastTotal)}
    accent={CARD_ACCENT.forecast}
    wide
    note="Proiezione dei soli contratti con periodicita' impostata. Ogni colonna e' divisa per cliente: a schermo intero la legenda li elenca tutti."
  >
    {#if forecastTotal > 0}
      <StackedColumnChart
        categories={forecastClients.months}
        series={forecast.series}
        legend={forecast.legend}
        fullLegend={forecast.fullLegend}
        title="Incassi previsti per mese, divisi per cliente"
        format={fmtEuro}
        axisFormat={fmtEuroAxis}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessun contratto ricorrente con periodicita' impostata." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Valore contratto"
    subtitle={`${fmtInt(valueByClient.length)} clienti`}
    accent={CARD_ACCENT.money}
  >
    {#if valueByClient.length > 0}
      <DonutPanel
        rows={withOther(valueByClient, donutSlices, fmtEuro)}
        allRows={valueByClient}
        title="Valore contratto per cliente"
        centerValue={fmtEuro(summary.initialValue)}
        centerLabel="firmato"
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessun valore contrattuale impostato." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Incassi fino a fine anno"
    subtitle={fmtEuro(yearEndTotal)}
    accent={CARD_ACCENT.forecast}
    note={`Incassi periodici previsti fino al 31/12/${referenceDate.getFullYear()}.`}
  >
    {#if yearEndTotal > 0}
      <ColumnChart
        points={yearEnd}
        title="Incassi periodici previsti fino a fine anno"
        format={fmtEuro}
        axisFormat={fmtEuroAxis}
        color={SERIES[1]}
        valueLabel="previsto"
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessun incasso periodico previsto entro fine anno." />
    {/if}
  </ChartCard>

  <ChartCard
    title={`Contratti firmati nel ${signedYear}`}
    subtitle={`${fmtInt(signedTotal)} contratti`}
    accent={CARD_ACCENT.money}
    wide
    note="Ogni contratto conta nel mese della sua data di inizio: i picchi sono i mesi di maggiore attivita' commerciale."
  >
    {#if signedTotal > 0}
      <AreaLineChart
        points={signed}
        title={`Contratti firmati per mese nel ${signedYear}`}
        format={fmtInt}
        valueLabel="firmati"
        integer
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message={`Nessun contratto con inizio nel ${signedYear}.`} />
    {/if}
  </ChartCard>

  <ChartCard
    title={expiryHorizon === 365 ? 'Scadenze entro 12 mesi' : `Scadenze entro ${fmtInt(expiryHorizon)} giorni`}
    subtitle={`${fmtInt(expiries.length)} contratti`}
    accent={CARD_ACCENT.risk}
    wide
    note="Barra rossa sotto i 30 giorni, gialla sotto i 90: il colore accompagna il numero di giorni, non lo sostituisce."
  >
    {#if expiries.length > 0}
      <BarChart
        rows={expiries}
        limit={topCount}
        title="Giorni alla scadenza"
        axisFormat={(value) => `${Math.round(value)} gg`}
        reference={{ value: expiringDays, label: `${expiringDays} gg` }}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessun contratto in scadenza nell'orizzonte scelto." />
    {/if}
  </ChartCard>

  {#if display.compareId}
    <ContractCompareCards
      {comparison}
      {forecastMonths}
      ontooltip={(next) => (tooltip = next)}
    />
  {/if}
</ChartScreenLayout>

<ChartTooltip {tooltip} />
