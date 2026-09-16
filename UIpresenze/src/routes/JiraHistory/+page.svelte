<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { useJiraWorklogsByYearStream } from '$lib/hooks/useJira';
  import type { JiraHistoryIssue, JiraYearWorklogResponse } from '$lib/services/jira';
  import JiraWorklogIssuesBar from '$lib/components/Jira/JiraWorklogIssuesBar.svelte';
  import JiraWorklogDetailBar from '$lib/components/Jira/JiraWorklogDetailBar.svelte';
  import JiraHistoryCharts from '$lib/components/Jira/JiraHistoryCharts.svelte';
  import ClientiSection from '$lib/components/Jira/ClientiSection.svelte';
  import { ensureJiraControlLoaded, jiraControl } from '$lib/stores/jiraControl';

  type JiraIssue = JiraHistoryIssue;
  type ContractPoolTask = {
    key: string;
    summary: string;
    seconds: number;
  };

  const MONTHS = [
    'Gennaio',
    'Febbraio',
    'Marzo',
    'Aprile',
    'Maggio',
    'Giugno',
    'Luglio',
    'Agosto',
    'Settembre',
    'Ottobre',
    'Novembre',
    'Dicembre'
  ];
  // v2: il payload espone `worklog_issues` (issue con ore loggate, senza filtro di
  // stato) al posto di `completed_issues`. Il bump invalida le entry gia' in cache.
  const PERIOD_CACHE_ROOT = 'app-presenze:jira-history:period:';
  const PERIOD_CACHE_PREFIX = `${PERIOD_CACHE_ROOT}v2:`;
  const PERIOD_CACHE_TTL_MS = 10 * 60 * 1000;
  const PERIOD_CACHE_MAX_ENTRIES = 6;

  type JiraHistoryPeriodCache = {
    version: 2;
    cachedAt: number;
    year: number;
    month: number | 'all';
    data: JiraYearWorklogResponse;
  };

  let selectedProjectKeys: string[] = [];
  let worklogIssues: JiraIssue[] = [];
  let selectedYear = new Date().getFullYear();
  let selectedMonth: number | 'all' = 'all';
  let yearlyWorklogData: JiraYearWorklogResponse | null = null;
  let yearlyWorklogLoading = false;
  let yearlyWorklogError = '';
  let yearlyWorklogProgress: { loaded: number; total: number } | null = null;
  let lastFetchedPeriod = '';
  let jiraHistoryReady = false;
  let yearlyWorklogRequestId = 0;
  let yearlyWorklogController: AbortController | null = null;

  function periodCacheKey(year: number, month: number | 'all') {
    return `${PERIOD_CACHE_PREFIX}${year}:${month}`;
  }

  function applyYearlyWorklogData(data: JiraYearWorklogResponse) {
    yearlyWorklogData = data;
    worklogIssues = normalizeWorklogIssues(data.worklog_issues || []);
  }

  function readPeriodCache(year: number, month: number | 'all') {
    const key = periodCacheKey(year, month);
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return null;

      const cached = JSON.parse(raw) as Partial<JiraHistoryPeriodCache>;
      if (
        cached.version !== 2 ||
        cached.year !== year ||
        cached.month !== month ||
        typeof cached.cachedAt !== 'number' ||
        !cached.data ||
        !Array.isArray(cached.data.projects)
      ) {
        localStorage.removeItem(key);
        return null;
      }

      return {
        data: cached.data,
        fresh: Date.now() - cached.cachedAt < PERIOD_CACHE_TTL_MS
      };
    } catch {
      return null;
    }
  }

  function prunePeriodCache(currentKey: string, maxEntries = PERIOD_CACHE_MAX_ENTRIES) {
    const entries: { key: string; cachedAt: number }[] = [];
    const legacyKeys: string[] = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (!key?.startsWith(PERIOD_CACHE_ROOT)) continue;
      if (!key.startsWith(PERIOD_CACHE_PREFIX)) {
        // Entry di versioni precedenti dello schema: non verranno mai piu' lette.
        legacyKeys.push(key);
        continue;
      }
      if (key === currentKey) continue;

      try {
        const cached = JSON.parse(localStorage.getItem(key) || '{}') as Partial<JiraHistoryPeriodCache>;
        if (typeof cached.cachedAt === 'number') entries.push({ key, cachedAt: cached.cachedAt });
        else localStorage.removeItem(key);
      } catch {
        localStorage.removeItem(key);
      }
    }

    legacyKeys.forEach((key) => localStorage.removeItem(key));

    entries
      .sort((first, second) => first.cachedAt - second.cachedAt)
      .slice(Math.max(0, maxEntries - 1))
      .forEach(({ key }) => localStorage.removeItem(key));
  }

  function savePeriodCache(year: number, month: number | 'all', data: JiraYearWorklogResponse) {
    const key = periodCacheKey(year, month);
    const value = JSON.stringify({ version: 2, cachedAt: Date.now(), year, month, data } satisfies JiraHistoryPeriodCache);

    try {
      prunePeriodCache(key);
      localStorage.setItem(key, value);
    } catch {
      try {
        prunePeriodCache(key, 1);
        localStorage.setItem(key, value);
      } catch {
        // The response can exceed the browser quota; live data remains available.
      }
    }
  }

  async function fetchYearlyWorklogs(year: number, month: number | 'all', forceRefresh = false) {
    yearlyWorklogController?.abort();
    const requestId = ++yearlyWorklogRequestId;
    yearlyWorklogController = null;
    yearlyWorklogError = '';
    const cached = readPeriodCache(year, month);

    if (cached) {
      applyYearlyWorklogData(cached.data);
      yearlyWorklogProgress = null;
      if (cached.fresh && !forceRefresh) {
        yearlyWorklogLoading = false;
        return;
      }
    } else if (yearlyWorklogData?.year !== year || yearlyWorklogData.month !== month) {
      yearlyWorklogData = null;
      worklogIssues = [];
    }

    const controller = new AbortController();
    yearlyWorklogController = controller;
    yearlyWorklogLoading = true;
    yearlyWorklogProgress = { loaded: 0, total: 0 };
    try {
      const data = await useJiraWorklogsByYearStream(
        year,
        month,
        (progress) => {
          if (requestId === yearlyWorklogRequestId) yearlyWorklogProgress = progress;
        },
        controller.signal
      );
      if (requestId !== yearlyWorklogRequestId) return;
      applyYearlyWorklogData(data);
      savePeriodCache(year, month, data);
    } catch (e: any) {
      if (requestId !== yearlyWorklogRequestId) return;
      if (e?.name === 'AbortError') return;
      if (!yearlyWorklogData) {
        worklogIssues = [];
        yearlyWorklogError = String(e?.message || e || 'Errore caricamento worklog del periodo');
      }
    } finally {
      if (requestId === yearlyWorklogRequestId) {
        yearlyWorklogLoading = false;
        yearlyWorklogController = null;
      }
    }
  }

  function normalizeWorklogIssue(issue: JiraIssue): JiraIssue | null {
    const key = String(issue?.key || '');
    if (!key) return null;

    const fields = issue.fields || {};
    return {
      id: issue.id,
      key,
      self: issue.self,
      fields: {
        summary: fields.summary,
        status: fields.status ? { name: fields.status.name } : undefined,
        assignee: fields.assignee?.displayName ? { displayName: fields.assignee.displayName } : null,
        issuetype: fields.issuetype
          ? { name: fields.issuetype.name, subtask: fields.issuetype.subtask }
          : null,
        parent: fields.parent
          ? { key: fields.parent.key, fields: { summary: fields.parent.fields?.summary } }
          : null,
        subtasks: normalizeWorklogIssues(fields.subtasks || []),
        subtasks_enriched: normalizeWorklogIssues(fields.subtasks_enriched || []),
        project: fields.project ? { key: fields.project.key, name: fields.project.name } : undefined,
        timespent: fields.timespent ?? null,
        aggregatetimespent: fields.aggregatetimespent ?? null,
        timeestimate: fields.timeestimate ?? null,
        aggregatetimeestimate: fields.aggregatetimeestimate ?? null,
        timeoriginalestimate: fields.timeoriginalestimate ?? null,
        aggregatetimeoriginalestimate: fields.aggregatetimeoriginalestimate ?? null,
        timetracking: fields.timetracking
          ? {
              timeSpentSeconds: fields.timetracking.timeSpentSeconds,
              originalEstimateSeconds: fields.timetracking.originalEstimateSeconds
            }
          : null,
        created: fields.created,
        updated: fields.updated,
        resolutiondate: fields.resolutiondate ?? null,
        worklog_authors: (fields.worklog_authors || []).map((author) => ({
          displayName: author.displayName,
          timeSpentSeconds: author.timeSpentSeconds
        })),
        worklog_primary_author: fields.worklog_primary_author
          ? {
              displayName: fields.worklog_primary_author.displayName,
              timeSpentSeconds: fields.worklog_primary_author.timeSpentSeconds
            }
          : undefined
      }
    };
  }

  function normalizeWorklogIssues(issues: JiraIssue[]): JiraIssue[] {
    return (issues || [])
      .map(normalizeWorklogIssue)
      .filter((issue): issue is JiraIssue => issue !== null);
  }

  function flattenWorklogIssues(issues: JiraIssue[]): JiraIssue[] {
    return (issues || []).flatMap((issue) => [
      issue,
      ...flattenWorklogIssues(issue.fields?.subtasks_enriched || [])
    ]);
  }

  $: flattenedWorklogIssues = flattenWorklogIssues(worklogIssues);
  $: chartIssues = flattenedWorklogIssues;
  $: jiraPoolTasks = (yearlyWorklogData?.projects || []).flatMap((project): ContractPoolTask[] =>
    project.issues.map((issue) => ({
      key: issue.issue_key,
      summary: issue.issue_summary || '-',
      seconds: Math.max(0, Number(issue.total_seconds || 0))
    }))
  );
  $: selectedPeriod = `${selectedYear}:${selectedMonth}`;
  $: selectedYearIsValid = Number.isInteger(selectedYear) && selectedYear >= 1900 && selectedYear <= 3000;
  $: if (jiraHistoryReady && selectedYearIsValid && selectedPeriod !== lastFetchedPeriod) {
    lastFetchedPeriod = selectedPeriod;
    void fetchYearlyWorklogs(selectedYear, selectedMonth);
  }

  onMount(async () => {
    const jiraEnabled = await ensureJiraControlLoaded();
    if (!jiraEnabled) {
      goto('/', { replaceState: true });
      return;
    }
    jiraHistoryReady = true;
  });

  onDestroy(() => {
    yearlyWorklogController?.abort();
  });

  $: if ($jiraControl.loaded && !$jiraControl.enabled) {
    goto('/', { replaceState: true });
  }
</script>

<main class="history-page">
  <h1 class="page-title">Jira History</h1>
  <header class="page-header" data-history-hover>
    <div class="header-main">
      <div>
        <button
          class="back-arrow-btn"
          type="button"
          on:click={() => goto('/JiraBoard')}
          aria-label="Torna alla Jira Board"
          title="Torna alla Jira Board"
        >
          ←
        </button>
        <p>Entrambe le viste mostrano le ore registrate nella data del worklog per il periodo selezionato.</p>
      </div>
      <div class="period-filters">
        <div class="period-filter">
          <label for="year-filter">Anno</label>
          <input
            id="year-filter"
            class="period-input"
            type="number"
            min="1900"
            max="3000"
            step="1"
            bind:value={selectedYear}
          />
        </div>
        <div class="period-filter">
          <label for="month-filter">Mese</label>
          <select id="month-filter" class="period-input" bind:value={selectedMonth}>
            <option value="all">Tutti i mesi</option>
            {#each MONTHS as monthName, index (monthName)}
              <option value={index + 1}>{monthName}</option>
            {/each}
          </select>
        </div>
        <button
          type="button"
          class="refresh-period-btn"
          on:click={() => fetchYearlyWorklogs(selectedYear, selectedMonth, true)}
          disabled={yearlyWorklogLoading || !selectedYearIsValid}
        >
          {yearlyWorklogLoading ? 'Aggiorno...' : 'Aggiorna'}
        </button>
      </div>
    </div>
  </header>

  <section class="layout-row">
    <div class="left-pane">
      <JiraWorklogIssuesBar
        bind:issuesData={worklogIssues}
        bind:selectedProjectKeys
        loading={yearlyWorklogLoading}
        error={yearlyWorklogError}
      />
    </div>

    <div class="right-pane">
      <JiraWorklogDetailBar
        data={yearlyWorklogData}
        issues={flattenedWorklogIssues}
        {selectedProjectKeys}
        loading={yearlyWorklogLoading}
        error={yearlyWorklogError}
        progress={yearlyWorklogProgress}
      />
    </div>
  </section>

  <ClientiSection jiraTasks={jiraPoolTasks} />

  <JiraHistoryCharts issues={chartIssues} {selectedProjectKeys} />
</main>

<style>
  .history-page {
    max-width: 1456px;
    margin: 0 auto;
    padding: 1.25rem 0 2.4rem;
    display: flex;
    flex-direction: column;
  }
  .page-title {
    margin: 0 0 0.7rem;
    font-size: 2.21rem;
    line-height: 1.05;
    color: #0f172a;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-family: var(--font-infinity);
  }

  .page-header {
    margin-bottom: 0.9rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    background: #ffffff;
  }
  .header-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.9rem;
  }

  .page-header p {
    margin: 0;
    color: #475569;
    font-size: 0.82rem;
    font-family: var(--font-mono);
  }
  .period-filters {
    display: flex;
    align-items: flex-end;
    gap: 0.55rem;
  }
  .period-filter {
    display: grid;
    gap: 0.22rem;
    min-width: 125px;
  }
  .period-filter label {
    font-size: 0.7rem;
    color: #64748b;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .period-input {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    font-size: 13px;
    color: #0f172a;
    background: #fff;
    padding: 8px 10px;
    outline: none;
    min-height: 36px;
  }
  .period-input:focus {
    border-color: #94a3b8;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.2);
  }
  .refresh-period-btn {
    min-height: 36px;
    border: 1px solid #d97706;
    border-radius: 9px;
    background: #f97316;
    color: #fff;
    font-size: 0.72rem;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    font-family: var(--font-mono);
  }
  .refresh-period-btn:hover:not(:disabled) {
    background: #ea580c;
  }
  .refresh-period-btn:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }
  .back-arrow-btn {
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #334155;
    border-radius: 999px;
    width: 34px;
    height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.4rem;
    font-size: 18px;
    line-height: 1;
    font-family: var(--font-mono);
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
  }
  .back-arrow-btn:hover {
    border-color: #94a3b8;
    color: #0f172a;
    background: #f8fafc;
  }
  .layout-row {
    /* Altezza fissa: non dipende dai progetti filtrati nella ricerca. */
    --history-panes-height: clamp(460px, 62vh, 600px);
    display: grid;
    grid-template-columns: minmax(0, 36fr) minmax(0, 64fr);
    grid-auto-rows: var(--history-panes-height);
    gap: 12px;
  }

  .left-pane,
  .right-pane {
    min-width: 0;
    min-height: 0;
  }

  @media (max-width: 1200px) {
    .page-title {
      font-size: 1.76rem;
      margin-bottom: 0.55rem;
    }
    .header-main {
      flex-direction: column;
    }
    .period-filters {
      width: 100%;
    }
    .period-filter {
      flex: 1 1 0;
    }
    .layout-row {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  @media (max-width: 480px) {
    .page-title {
      font-size: 1.56rem;
    }
  }
</style>
