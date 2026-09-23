<script lang="ts">
  /**
   * Schermata C del cubo: quanto rende il tempo speso.
   *
   * Incrocia il valore maturato dei contratti con le ore Jira loggate sulle task
   * del loro pool. Da li' escono la tariffa oraria effettiva, i contratti che
   * rendono piu' della media e il valore attribuito alle singole task.
   *
   * Restano fuori i contratti senza ore nel periodo: dividere un valore per zero
   * ore darebbe una tariffa infinita, non un contratto redditizio.
   */
  import { onMount } from 'svelte';
  import { chartsData, ensureContrattiLoaded } from '$lib/remo/chartsData';
  import { fmtEuro, fmtEuroAxis, fmtHours, fmtHoursAxis, fmtInt, fmtRate } from '../format';
  import { CARD_ACCENT, SERIES } from '../palette';
  import {
    contractHoursRows,
    hourlyRateRows,
    profitabilityList,
    taskValueRows,
    tasksByKey
  } from '../contractsSelectors';
  import { activeCount, chartFilters, resolveValues } from '../filters/core/filterState';
  import {
    applyRedditivitaFilters,
    redditivitaDisplay,
    redditivitaFilters as FILTERS
  } from '../filters/redditivita/apply';
  import { compareProfitability } from '../filters/redditivita/compare';
  import ProfitabilityCompareCards from '../filters/redditivita/CompareCards.svelte';
  import BarChart from '../atoms/BarChart.svelte';
  import ChartCard from '../atoms/ChartCard.svelte';
  import ChartEmpty from '../atoms/ChartEmpty.svelte';
  import ChartScreenLayout from '../atoms/ChartScreenLayout.svelte';
  import ChartTooltip from '../atoms/ChartTooltip.svelte';
  import MetricCard from '../atoms/MetricCard.svelte';
  import ScatterChart from '../atoms/ScatterChart.svelte';
  import type { ChartTooltipState } from '../atoms/tooltip';

  type Props = { topCount?: number };

  let { topCount: defaultTopCount = 12 }: Props = $props();

  let tooltip = $state<ChartTooltipState | null>(null);

  const filters = $derived(resolveValues(FILTERS, $chartFilters[FILTERS.id]));
  const filterCount = $derived(activeCount(FILTERS, $chartFilters[FILTERS.id]));
  const display = $derived(redditivitaDisplay(filters, { topCount: defaultTopCount }));
  const topCount = $derived(display.topCount);

  onMount(() => {
    void ensureContrattiLoaded().catch(() => undefined);
  });

  const contracts = $derived($chartsData.contratti);
  const pool = $derived(tasksByKey($chartsData.poolTasks));
  const fullList = $derived(profitabilityList(contracts, pool));
  const filtered = $derived(applyRedditivitaFilters(contracts, fullList, filters));
  const list = $derived(filtered.list);

  const rateRows = $derived(hourlyRateRows(list));
  const hoursRows = $derived(contractHoursRows(list));
  const valueRows = $derived(taskValueRows(list));
  const averageRate = $derived(filtered.averageRate);
  const comparison = $derived(
    display.compareId
      ? compareProfitability(fullList, list, display.compareId, { averageRate, topCount })
      : null
  );

  const totalHours = $derived(list.reduce((total, row) => total + row.hours, 0));
  const totalValue = $derived(list.reduce((total, row) => total + row.value, 0));
  const missingTasks = $derived(list.reduce((total, row) => total + row.missingTasks, 0));
  const pooledTasks = $derived(list.reduce((total, row) => total + row.poolSize, 0));
  const best = $derived(list[0] ?? null);
  const worst = $derived(list[list.length - 1] ?? null);

  const scatterPoints = $derived(
    list.map((row) => ({
      id: String(row.id),
      label: row.contractId,
      x: row.hours,
      y: row.value,
      hint: `${row.clientName} · ${fmtRate(row.hourlyRate)}`
    }))
  );

  const contractsWithPool = $derived(
    contracts.filter((contract) => (contract.pool_task || []).length > 0).length
  );
</script>

<ChartScreenLayout
  title="Redditivita' dei contratti"
  subtitle={filterCount > 0
    ? `${fmtInt(list.length)} contratti su ${fmtInt(fullList.length)} · ${filterCount} filtri dal pannello`
    : 'Valore maturato diviso le ore Jira loggate sulle task del pool, nel periodo selezionato.'}
  loading={$chartsData.contrattiLoading}
  refreshing={$chartsData.contrattiRefreshing}
  error={$chartsData.contrattiError}
  empty={list.length === 0}
  emptyMessage={fullList.length > 0
    ? 'Nessun contratto passa i filtri attivi: allargali dal pannello filtri.'
    : contractsWithPool === 0
    ? 'Nessun contratto ha task nel pool: aggiungine almeno una per calcolare la redditivita’.'
    : 'Nessuna task dei pool ha ore loggate nel periodo selezionato.'}
>
  {#snippet metrics()}
    <MetricCard
      label="Tariffa oraria media"
      value={fmtRate(averageRate)}
      hint="valore totale diviso ore totali"
      lead
    />
    <MetricCard
      label="Contratti misurati"
      value={fmtInt(list.length)}
      hint={`${fmtInt(contractsWithPool)} con pool`}
    />
    <MetricCard label="Ore sui pool" value={fmtHours(totalHours * 3600)} />
    <MetricCard label="Valore coinvolto" value={fmtEuro(totalValue)} />
    <MetricCard
      label="Task del pool con ore"
      value={fmtInt(pooledTasks - missingTasks)}
      hint={`${fmtInt(missingTasks)} senza worklog nel periodo`}
      meter={{ ratio: pooledTasks > 0 ? (pooledTasks - missingTasks) / pooledTasks : 0 }}
    />
  {/snippet}

  <ChartCard
    title="Tariffa oraria per contratto"
    subtitle={best ? `migliore ${fmtRate(best.hourlyRate)}` : undefined}
    accent={CARD_ACCENT.money}
    wide
    note="La linea verticale e' la tariffa media: a destra i contratti che rendono piu' della media, a sinistra quelli che rendono meno."
  >
    <BarChart
      rows={rateRows}
      limit={topCount}
      title="Tariffa oraria effettiva per contratto"
      axisFormat={(value) => `${Math.round(value)} €`}
      reference={{ value: averageRate, label: 'media' }}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title="Ore contro valore per contratto"
    subtitle={`${fmtInt(list.length)} contratti`}
    accent={CARD_ACCENT.time}
    wide
    note="La retta e' il rapporto medio fra ore e valore: sopra la retta si e' incassato di piu' per ora."
  >
    {#if scatterPoints.length > 1}
      <ScatterChart
        points={scatterPoints}
        title="Ore loggate contro valore maturato"
        xLabel="ore sul pool"
        yLabel="valore maturato"
        formatX={(value) => fmtHours(value * 3600)}
        formatY={fmtEuro}
        axisFormatX={(value) => `${Math.round(value)} h`}
        axisFormatY={fmtEuroAxis}
        reference={averageRate > 0 ? { slope: averageRate, label: 'tariffa media' } : null}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Serve piu' di un contratto con ore loggate per confrontare i rapporti." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Ore sul pool per contratto"
    subtitle={fmtHours(totalHours * 3600)}
    accent={CARD_ACCENT.jira}
  >
    <BarChart
      rows={hoursRows}
      limit={topCount}
      title="Ore loggate sulle task del pool"
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title={`Top ${Math.min(topCount, valueRows.length)} task per valore generato`}
    subtitle={`${fmtInt(valueRows.length)} task`}
    accent={CARD_ACCENT.people}
    wide
    note="Il valore del contratto ripartito fra le sue task in proporzione alle ore."
  >
    {#if valueRows.length > 0}
      <BarChart
        rows={valueRows}
        limit={topCount}
        title="Valore generato per task"
        axisFormat={fmtEuroAxis}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessuna task del pool ha ore nel periodo." />
    {/if}
  </ChartCard>

  {#if best && worst && best.id !== worst.id}
    <ChartCard title="Estremi del periodo" accent={SERIES[6]}>
      <dl class="extremes">
        <div>
          <dt>Piu' remunerativo</dt>
          <dd>
            <strong>{best.contractId}</strong>
            <span>{best.clientName}</span>
            <em>{fmtRate(best.hourlyRate)} · {fmtEuro(best.value)} su {fmtHours(best.seconds)}</em>
          </dd>
        </div>
        <div>
          <dt>Meno remunerativo</dt>
          <dd>
            <strong>{worst.contractId}</strong>
            <span>{worst.clientName}</span>
            <em>{fmtRate(worst.hourlyRate)} · {fmtEuro(worst.value)} su {fmtHours(worst.seconds)}</em>
          </dd>
        </div>
      </dl>
    </ChartCard>
  {/if}

  {#if display.compareId}
    <ProfitabilityCompareCards
      {comparison}
      {averageRate}
      ontooltip={(next) => (tooltip = next)}
    />
  {/if}
</ChartScreenLayout>

<ChartTooltip {tooltip} />

<style>
  .extremes {
    display: grid;
    gap: 0.6rem;
    margin: 0;
  }

  .extremes dt {
    color: #64748b;
    font-size: 0.64rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .extremes dd {
    display: grid;
    gap: 0.1rem;
    margin: 0.2rem 0 0;
  }

  .extremes strong {
    color: #0f172a;
    font-size: 0.9rem;
  }

  .extremes span,
  .extremes em {
    color: #475569;
    font-size: 0.7rem;
    font-family: var(--font-mono);
    font-style: normal;
  }

  .extremes em {
    color: #64748b;
  }
</style>
