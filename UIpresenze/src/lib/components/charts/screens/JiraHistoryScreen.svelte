<script lang="ts">
  /**
   * Schermata A del cubo: le ore Jira del periodo.
   *
   * Ogni grafico ha una domanda sola:
   * - quando sono state loggate (andamento nel tempo);
   * - da chi e su cosa (classifiche a barre);
   * - in che proporzione fra i tipi di attivita' (ciambella, poche voci);
   * - quanto si sono discostate dalle stime (confronto a due punte).
   */
  import { chartsData } from '$lib/remo/chartsData';
  import {
    addGrouped,
    buildChartRows,
    totalOf,
    withOther,
    type ChartGroups
  } from '../chartData';
  import { fmtHours, fmtHoursAxis, fmtInt, fmtPercent } from '../format';
  import {
    addIssueUserSeconds,
    estimateComparisons,
    issueLoggedSeconds,
    issueProjectKey,
    issueProjectLabel,
    issueTitle,
    issueTypeLabel,
    weekdayTotals,
    worklogTimeline
  } from '../jiraSelectors';
  import { CARD_ACCENT, SERIES } from '../palette';
  import { activeCount, chartFilters, resolveValues } from '../filters/core/filterState';
  import {
    applyJiraHistoryFilters,
    filterEstimates,
    jiraHistoryDisplay,
    jiraHistoryFilters as FILTERS
  } from '../filters/jiraHistory/apply';
  import { compareIssue } from '../filters/core/issueCompare';
  import IssueCompareCards from '../filters/core/IssueCompareCards.svelte';
  import AreaLineChart from '../atoms/AreaLineChart.svelte';
  import BarChart from '../atoms/BarChart.svelte';
  import ChartCard from '../atoms/ChartCard.svelte';
  import ChartEmpty from '../atoms/ChartEmpty.svelte';
  import ChartScreenLayout from '../atoms/ChartScreenLayout.svelte';
  import ChartTooltip from '../atoms/ChartTooltip.svelte';
  import ColumnChart from '../atoms/ColumnChart.svelte';
  import DonutPanel from '../atoms/DonutPanel.svelte';
  import DumbbellChart from '../atoms/DumbbellChart.svelte';
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

  const typeRows = $derived.by(() => {
    const groups: ChartGroups = {};
    selectedIssues.forEach((issue) =>
      addGrouped(groups, issueTypeLabel(issue), issueTypeLabel(issue), issueLoggedSeconds(issue))
    );
    return withOther(buildChartRows(groups, { format: fmtHours, palette: 'identity' }), 6, fmtHours);
  });

  const timeline = $derived(worklogTimeline(worklogEntries, display.bucket));
  const timelinePoints = $derived(
    timeline.points.map((point) => ({ key: point.key, label: point.label, value: point.seconds }))
  );
  const weekdayPoints = $derived(
    weekdayTotals(worklogEntries).map((day) => ({ key: day.key, label: day.label.slice(0, 3), value: day.seconds }))
  );

  /** Solo le issue della selezione che hanno davvero una stima con cui confrontarsi. */
  const estimateRows = $derived(
    filterEstimates(estimateComparisons(selectedIssues), filters)
      .map((row) => ({
        id: row.key,
        label: `${row.key} · ${row.title}`,
        from: row.estimateSeconds,
        to: row.loggedSeconds,
        hint:
          row.deviationPercent >= 0
            ? `${fmtPercent(row.deviationPercent, 0)} sopra la stima`
            : `${fmtPercent(Math.abs(row.deviationPercent), 0)} sotto la stima`
      }))
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
    title={`Andamento ore per ${bucketName}`}
    subtitle={fmtHours(totalSeconds)}
    accent={CARD_ACCENT.time}
    wide
    note="I periodi senza worklog restano sull'asse: saltarli mostrerebbe una continuita' che non c'e'."
  >
    {#if timelinePoints.length > 1}
      <AreaLineChart
        points={timelinePoints}
        title={`Ore loggate per ${bucketName}`}
        format={fmtHours}
        axisFormat={fmtHoursAxis}
        valueLabel="ore"
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Serve piu' di un periodo con worklog per disegnare un andamento." />
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
  >
    <BarChart
      rows={issueRows}
      limit={topCount}
      title="Ore per issue"
      axisFormat={fmtHoursAxis}
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title="Composizione per tipo di attivita'"
    subtitle={`${fmtInt(typeRows.length)} voci`}
    accent={CARD_ACCENT.time}
  >
    {#if typeRows.length > 1}
      <DonutPanel
        rows={typeRows}
        title="Ore per tipo di issue"
        centerValue={fmtHours(totalSeconds)}
        centerLabel="totale"
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Le issue del periodo appartengono a un solo tipo." />
    {/if}
  </ChartCard>

  <ChartCard
    title="Ore per giorno della settimana"
    subtitle={fmtHours(totalSeconds)}
    accent={CARD_ACCENT.people}
  >
    <ColumnChart
      points={weekdayPoints}
      title="Ore per giorno della settimana"
      format={fmtHours}
      axisFormat={fmtHoursAxis}
      color={SERIES[2]}
      valueLabel="ore"
      ontooltip={(next) => (tooltip = next)}
    />
  </ChartCard>

  <ChartCard
    title="Stima contro consuntivo"
    subtitle={`${fmtInt(estimateRows.length)} issue`}
    accent={CARD_ACCENT.forecast}
    wide
    note="Solo le issue che hanno una stima originale in Jira, ordinate per scostamento."
  >
    {#if estimateRows.length > 0}
      <DumbbellChart
        rows={estimateRows}
        title="Stima contro ore loggate"
        format={fmtHours}
        axisFormat={fmtHoursAxis}
        fromLabel="Stimato"
        toLabel="Loggato"
        fromColor="#9ec5f4"
        toColor={SERIES[0]}
        ontooltip={(next) => (tooltip = next)}
      />
    {:else}
      <ChartEmpty message="Nessuna issue del periodo ha una stima originale con cui confrontare le ore." />
    {/if}
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
