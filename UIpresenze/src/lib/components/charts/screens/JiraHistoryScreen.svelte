<script lang="ts">
  /**
   * Schermata A del cubo: le ore Jira del periodo.
   *
   * Ogni grafico ha una domanda sola:
   * - quante task si aprono e si chiudono nella settimana corrente (colonne affiancate);
   * - da chi e su cosa (classifiche a barre).
   */
  import { onMount } from 'svelte';
  import { chartsData, ensureWeekIssuesLoaded } from '$lib/remo/chartsData';
  import {
    addGrouped,
    buildChartRows,
    totalOf,
    type ChartGroups
  } from '../chartData';
  import { fmtHours, fmtHoursAxis, fmtInt } from '../format';
  import {
    addIssueUserSeconds,
    issueLoggedSeconds,
    issueProjectKey,
    issueProjectLabel,
    issueTitle,
    weekOpenedClosed,
    worklogTimeline
  } from '../jiraSelectors';
  import { CARD_ACCENT, SERIES } from '../palette';
  import { activeCount, chartFilters, resolveValues } from '../filters/core/filterState';
  import {
    applyJiraHistoryFilters,
    jiraHistoryDisplay,
    jiraHistoryFilters as FILTERS
  } from '../filters/jiraHistory/apply';
  import { compareIssue } from '../filters/core/issueCompare';
  import IssueCompareCards from '../filters/core/IssueCompareCards.svelte';
  import BarChart from '../atoms/BarChart.svelte';
  import ChartCard from '../atoms/ChartCard.svelte';
  import ChartEmpty from '../atoms/ChartEmpty.svelte';
  import ChartScreenLayout from '../atoms/ChartScreenLayout.svelte';
  import ChartTooltip from '../atoms/ChartTooltip.svelte';
  import GroupedColumnChart from '../atoms/GroupedColumnChart.svelte';
  import MetricCard from '../atoms/MetricCard.svelte';
  import type { ChartTooltipState } from '../atoms/tooltip';

  type Props = {
    /** Quante voci restano nelle classifiche: il resto vive nelle barre di pagina. */
    topCount?: number;
  };

  let { topCount: defaultTopCount = 12 }: Props = $props();

  let tooltip = $state<ChartTooltipState | null>(null);

  const filters = $derived(resolveValues(FILTERS, $chartFilters[FILTERS.id]));
  const filterCount = $derived(activeCount(FILTERS, $chartFilters[FILTERS.id]));
  const display = $derived(jiraHistoryDisplay(filters, { topCount: defaultTopCount }));
  const topCount = $derived(display.topCount);

  const issues = $derived($chartsData.issues);
  const selectedProjectKeys = $derived($chartsData.selectedProjectKeys);
  const hasSelection = $derived(selectedProjectKeys.length > 0);
  const selectedSet = $derived(new Set(selectedProjectKeys));
  // Prima la selezione della barra di sinistra, poi i filtri del pannello.
  const scoped = $derived(
    applyJiraHistoryFilters(
      hasSelection ? issues.filter((issue) => selectedSet.has(issueProjectKey(issue))) : issues,
      hasSelection
        ? $chartsData.worklogEntries.filter((entry) => selectedSet.has(entry.projectKey))
        : $chartsData.worklogEntries,
      filters
    )
  );
  const selectedIssues = $derived(scoped.issues);
  const worklogEntries = $derived(scoped.entries);

  const projectRows = $derived.by(() => {
    const groups: ChartGroups = {};
    selectedIssues.forEach((issue) =>
      addGrouped(groups, issueProjectKey(issue), issueProjectLabel(issue), issueLoggedSeconds(issue))
    );
    return buildChartRows(groups, { format: fmtHours });
  });

  const userRows = $derived.by(() => {
    const groups: ChartGroups = {};
    selectedIssues.forEach((issue) => addIssueUserSeconds(groups, issue));
    return buildChartRows(groups, { format: fmtHours, color: SERIES[2] });
  });

  const issueRows = $derived.by(() => {
    const groups: ChartGroups = {};
    selectedIssues.forEach((issue) =>
      addGrouped(groups, issue.key, `${issue.key} · ${issueTitle(issue)}`, issueLoggedSeconds(issue))
    );
    return buildChartRows(groups, { format: fmtHours });
  });

  const timeline = $derived(worklogTimeline(worklogEntries, display.bucket));

  onMount(() => {
    void ensureWeekIssuesLoaded();
  });

  /** Aperte contro chiuse nella settimana corrente: vale la sola selezione dei progetti di sinistra. */
  const WEEK_SERIES = [
    { id: 'opened', label: 'Aperte', color: SERIES[0] },
    { id: 'closed', label: 'Chiuse', color: SERIES[1] }
  ];
  const weekIssues = $derived(
    hasSelection
      ? $chartsData.weekIssues.filter((issue) => selectedSet.has(issueProjectKey(issue)))
      : $chartsData.weekIssues
  );
  const weekPoints = $derived(
    weekOpenedClosed(weekIssues, new Date()).map((day) => ({
      key: day.key,
      label: day.label,
      values: { opened: day.opened, closed: day.closed }
    }))
  );
  const weekHasData = $derived(
    weekPoints.some((point) => point.values.opened > 0 || point.values.closed > 0)
  );

  // Si calcola solo con una task scelta: senza, il confronto non costa nulla.
  const comparison = $derived(
    display.compareKey
      ? compareIssue(selectedIssues, worklogEntries, display.compareKey, display)
      : null
  );

  const totalSeconds = $derived(totalOf(projectRows));
  const activeDays = $derived(timeline.points.filter((point) => point.seconds > 0).length);
  const dailyAverage = $derived(activeDays > 0 ? totalSeconds / activeDays : 0);
  const bucketName = $derived(timeline.bucket === 'month' ? 'mese' : 'giorno');
</script>

<ChartScreenLayout
  title="Ore Jira del periodo"
  subtitle={`${
    hasSelection
      ? `Filtro attivo sui progetti: ${selectedProjectKeys.join(', ')}`
      : 'Nessun progetto selezionato: sono incluse tutte le ore del periodo.'
  }${filterCount > 0 ? ` · ${filterCount} filtri dal pannello` : ''}`}
  loading={$chartsData.jiraLoading && projectRows.length === 0}
  refreshing={$chartsData.jiraLoading && projectRows.length > 0}
  error={$chartsData.jiraError}
  empty={projectRows.length === 0}
  emptyMessage={filterCount > 0
    ? 'Nessuna ora passa i filtri attivi: allargali dal pannello filtri.'
    : 'Nessuna ora loggata nel periodo selezionato.'}
>
  {#snippet metrics()}
    <MetricCard label="Ore totali" value={fmtHours(totalSeconds)} lead />
    <MetricCard label="Progetti" value={fmtInt(projectRows.length)} />
    <MetricCard label="Persone" value={fmtInt(userRows.length)} />
    <MetricCard label="Issue con ore" value={fmtInt(issueRows.length)} />
    <MetricCard
      label={`Media per ${bucketName} attivo`}
      value={fmtHours(dailyAverage)}
      hint={`${fmtInt(activeDays)} su ${fmtInt(timeline.points.length)}`}
    />
  {/snippet}

  <ChartCard
    title="Task aperte e chiuse questa settimana"
    subtitle={weekPoints.length > 0 ? `${weekPoints[0].label} - ${weekPoints[weekPoints.length - 1].label}` : undefined}
    accent={CARD_ACCENT.time}
    wide
    note="Aperte: create quel giorno. Chiuse: passate a Done (o Completata) quel giorno. Settimana corrente, indipendente dal periodo scelto; vale solo la selezione dei progetti."
  >
    {#if $chartsData.weekIssuesLoading && !weekHasData}
      <ChartEmpty message="Caricamento delle task della settimana..." />
    {:else if $chartsData.weekIssuesError}
      <ChartEmpty message={`Impossibile caricare le task della settimana: ${$chartsData.weekIssuesError}`} />
    {:else if weekHasData}
      <GroupedColumnChart
        points={weekPoints}
        series={WEEK_SERIES}
        title="Task aperte e chiuse per giorno, settimana corrente"
        format={(value) => fmtInt(value)}
        integer
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessuna task aperta o chiusa questa settimana." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Ore per progetto"
    subtitle={`${fmtInt(projectRows.length)} progetti`}
    accent={CARD_ACCENT.jira}
  >
    <BarChart
      rows={projectRows}
      limit={topCount}
      title="Ore per progetto"
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title="Ore per persona"
    subtitle={`${fmtInt(userRows.length)} persone`}
    accent={CARD_ACCENT.people}
  >
    {#if userRows.length > 0}
      <BarChart
        rows={userRows}
        limit={topCount}
        title="Ore per persona"
        axisFormat={fmtHoursAxis}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessun worklog con autore nel periodo." />
    {/if}
  </ChartCard>

  <ChartCard
    title={`Top ${Math.min(topCount, issueRows.length)} issue per ore`}
    subtitle={`${fmtInt(issueRows.length)} issue`}
    accent={CARD_ACCENT.jira}
    wide
  >
    <BarChart
      rows={issueRows}
      limit={topCount}
      title="Ore per issue"
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  {#if display.compareKey}
    <IssueCompareCards
      {comparison}
      focusKey={display.compareKey}
      ontooltip={(next) => (tooltip = next)}
    />
  {/if}
</ChartScreenLayout>

<ChartTooltip {tooltip} />
