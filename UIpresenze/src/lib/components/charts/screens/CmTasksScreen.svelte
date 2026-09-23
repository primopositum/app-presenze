<script lang="ts">
  /**
   * Schermata D del cubo: solo le task marcate "CM" (marcatore nella chiave
   * della issue o del progetto), indipendentemente dai progetti selezionati.
   *
   * La quota sul periodo e' una cifra sola con la sua barra di riempimento: una
   * ciambella con due spicchi direbbe la stessa cosa occupando una card intera.
   */
  import { chartsData } from '$lib/remo/chartsData';
  import { addGrouped, buildChartRows, totalOf, type ChartGroups } from '../chartData';
  import { fmtHours, fmtHoursAxis, fmtInt, fmtPercent } from '../format';
  import {
    CM_MARKER,
    addIssueUserSeconds,
    issueLoggedSeconds,
    issueProjectKey,
    issueProjectLabel,
    issueTitle,
    worklogTimeline
  } from '../jiraSelectors';
  import { CARD_ACCENT, SERIES } from '../palette';
  import { activeCount, chartFilters, resolveValues } from '../filters/core/filterState';
  import {
    applyCmFilters,
    cmTasksDisplay,
    cmTasksFilters as FILTERS
  } from '../filters/cmTasks/apply';
  import { compareIssue } from '../filters/core/issueCompare';
  import IssueCompareCards from '../filters/core/IssueCompareCards.svelte';
  import AreaLineChart from '../atoms/AreaLineChart.svelte';
  import BarChart from '../atoms/BarChart.svelte';
  import ChartCard from '../atoms/ChartCard.svelte';
  import ChartEmpty from '../atoms/ChartEmpty.svelte';
  import ChartScreenLayout from '../atoms/ChartScreenLayout.svelte';
  import ChartTooltip from '../atoms/ChartTooltip.svelte';
  import MetricCard from '../atoms/MetricCard.svelte';
  import type { ChartTooltipState } from '../atoms/tooltip';

  type Props = {
    /** Marcatore da cercare nelle chiavi: di default "CM". */
    marker?: string;
    topCount?: number;
  };

  let { marker: defaultMarker = CM_MARKER, topCount: defaultTopCount = 12 }: Props = $props();

  let tooltip = $state<ChartTooltipState | null>(null);

  const filters = $derived(resolveValues(FILTERS, $chartFilters[FILTERS.id]));
  const filterCount = $derived(activeCount(FILTERS, $chartFilters[FILTERS.id]));
  const display = $derived(cmTasksDisplay(filters, { topCount: defaultTopCount }));
  const topCount = $derived(display.topCount);

  const scoped = $derived(
    applyCmFilters($chartsData.issues, $chartsData.worklogEntries, filters, defaultMarker)
  );
  const marker = $derived(scoped.marker);
  const cmIssues = $derived(scoped.issues);
  const periodSeconds = $derived(scoped.periodSeconds);

  const taskRows = $derived.by(() => {
    const groups: ChartGroups = {};
    cmIssues.forEach((issue) =>
      addGrouped(groups, issue.key, `${issue.key} · ${issueTitle(issue)}`, issueLoggedSeconds(issue))
    );
    return buildChartRows(groups, { format: fmtHours });
  });

  const userRows = $derived.by(() => {
    const groups: ChartGroups = {};
    cmIssues.forEach((issue) => addIssueUserSeconds(groups, issue));
    return buildChartRows(groups, { format: fmtHours, color: SERIES[2] });
  });

  const projectRows = $derived.by(() => {
    const groups: ChartGroups = {};
    cmIssues.forEach((issue) =>
      addGrouped(groups, issueProjectKey(issue), issueProjectLabel(issue), issueLoggedSeconds(issue))
    );
    return buildChartRows(groups, { format: fmtHours });
  });

  const timeline = $derived(
    worklogTimeline(scoped.entries, display.bucket)
  );
  const timelinePoints = $derived(
    timeline.points.map((point) => ({ key: point.key, label: point.label, value: point.seconds }))
  );

  // Termine di confronto: le altre task CM dello stesso perimetro.
  const comparison = $derived(
    display.compareKey
      ? compareIssue(cmIssues, scoped.entries, display.compareKey, display)
      : null
  );

  const cmSeconds = $derived(totalOf(taskRows));
  const cmShare = $derived(periodSeconds > 0 ? cmSeconds / periodSeconds : 0);
  const bucketName = $derived(timeline.bucket === 'month' ? 'mese' : 'giorno');
</script>

<ChartScreenLayout
  title={`Task ${marker}`}
  subtitle={`Solo le issue con "${marker}" nella chiave, indipendentemente dai progetti selezionati.${
    filterCount > 0 ? ` · ${filterCount} filtri dal pannello` : ''
  }`}
  loading={$chartsData.jiraLoading && taskRows.length === 0}
  refreshing={$chartsData.jiraLoading && taskRows.length > 0}
  error={$chartsData.jiraError}
  empty={taskRows.length === 0}
  emptyMessage={filterCount > 0
    ? `Nessuna task ${marker} passa i filtri attivi: allargali dal pannello filtri.`
    : `Nessuna task ${marker} con ore loggate nel periodo selezionato.`}
>
  {#snippet metrics()}
    <MetricCard label={`Ore ${marker}`} value={fmtHours(cmSeconds)} lead />
    <MetricCard
      label="Quota sul periodo"
      value={fmtPercent(cmShare * 100)}
      hint={`su ${fmtHours(periodSeconds)} totali`}
      meter={{ ratio: cmShare, color: SERIES[3] }}
    />
    <MetricCard label={`Task ${marker}`} value={fmtInt(taskRows.length)} />
    <MetricCard label="Persone coinvolte" value={fmtInt(userRows.length)} />
    <MetricCard label="Progetti toccati" value={fmtInt(projectRows.length)} />
  {/snippet}

  <ChartCard
    title={`Andamento ore ${marker} per ${bucketName}`}
    subtitle={fmtHours(cmSeconds)}
    accent={CARD_ACCENT.time}
    wide
  >
    {#if timelinePoints.length > 1}
      <AreaLineChart
        points={timelinePoints}
        title={`Ore ${marker} per ${bucketName}`}
        format={fmtHours}
        axisFormat={fmtHoursAxis}
        color={SERIES[3]}
        valueLabel="ore"
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Serve piu' di un periodo con worklog per disegnare un andamento." />
    {/if}
  </ChartCard>

  <ChartCard
    title={`Top ${Math.min(topCount, taskRows.length)} task ${marker} per ore`}
    subtitle={`${fmtInt(taskRows.length)} task`}
    accent={CARD_ACCENT.jira}
    wide
  >
    <BarChart
      rows={taskRows}
      limit={topCount}
      title={`Ore per task ${marker}`}
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard title="Ore per persona" subtitle={`${fmtInt(userRows.length)} persone`} accent={CARD_ACCENT.people}>
    {#if userRows.length > 0}
      <BarChart
        rows={userRows}
        limit={topCount}
        title={`Ore ${marker} per persona`}
        axisFormat={fmtHoursAxis}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message={`Nessun worklog con autore sulle task ${marker}.`} />
    {/if}
  </ChartCard>

  <ChartCard title="Ore per progetto" subtitle={`${fmtInt(projectRows.length)} progetti`} accent={CARD_ACCENT.money}>
    <BarChart
      rows={projectRows}
      limit={topCount}
      title={`Ore ${marker} per progetto`}
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  {#if display.compareKey}
    <IssueCompareCards
      {comparison}
      focusKey={display.compareKey}
      noun={`task ${marker}`}
      ontooltip={(next) => (tooltip = next)}
    />
  {/if}
</ChartScreenLayout>

<ChartTooltip {tooltip} />
