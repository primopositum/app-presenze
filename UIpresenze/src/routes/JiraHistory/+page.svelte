<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { useJiraCompletedHistory, useJiraWorklogsByYear } from '$lib/hooks/useJira';
  import type { JiraHistoryIssue, JiraYearWorklogResponse } from '$lib/services/jira';
  import JiraCompletedBar from '$lib/components/Jira/JiraCompletedBar.svelte';
  import JiraHistoryCharts from '$lib/components/Jira/JiraHistoryCharts.svelte';
  import { ensureJiraControlLoaded, jiraControl } from '$lib/stores/jiraControl';

  type JiraIssue = JiraHistoryIssue;
  type CompletedHistoryCache = {
    version: 1;
    cachedAt: string;
    issues: JiraIssue[];
  };

  const COMPLETED_HISTORY_CACHE_KEY = 'app-presenze:jira-history:completed:v1';

  let selectedProjectKeys: string[] = [];
  let searchQuery = '';
  let completedIssues: JiraIssue[] = [];
  let completedLoading = false;
  let completedError = '';
  let completedRequestId = 0;
  let selectedYear = 'all';
  let yearlyWorklogData: JiraYearWorklogResponse | null = null;
  let yearlyWorklogLoading = false;
  let yearlyWorklogError = '';
  let lastFetchedYear = '';
  let yearlyWorklogRequestId = 0;

  function issueYear(issue: JiraIssue) {
    const dateValue =
      issue.fields?.resolutiondate ||
      issue.fields?.updated ||
      issue.fields?.created;
    if (!dateValue) return null;
    const parsed = new Date(dateValue);
    const year = parsed.getFullYear();
    return Number.isFinite(year) ? year : null;
  }

  function fmtHours(seconds: number) {
    const hours = seconds / 3600;
    const rounded = Math.round(hours * 10) / 10;
    return Number.isInteger(rounded)
      ? `${rounded.toFixed(0)}h`
      : `${rounded.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}h`;
  }

  function fmtDateTime(value?: string) {
    if (!value) return '-';
    const parsed = new Date(value);
    if (!Number.isFinite(parsed.getTime())) return value;
    return parsed.toLocaleString('it-IT', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  async function fetchYearlyWorklogs(year: string) {
    const requestId = ++yearlyWorklogRequestId;
    yearlyWorklogLoading = true;
    yearlyWorklogError = '';
    try {
      const data = await useJiraWorklogsByYear(year);
      if (requestId !== yearlyWorklogRequestId) return;
      yearlyWorklogData = data;
    } catch (e: any) {
      if (requestId !== yearlyWorklogRequestId) return;
      yearlyWorklogData = null;
      yearlyWorklogError = String(e?.message || e || 'Errore caricamento worklog annuali');
    } finally {
      if (requestId === yearlyWorklogRequestId) {
        yearlyWorklogLoading = false;
      }
    }
  }

  function normalizeCompletedIssues(issues: JiraIssue[]): JiraIssue[] {
    return (issues || [])
      .map((issue) => {
        const fields = issue.fields || {};
        return {
          key: String(issue.key || ''),
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
      })
      .filter((issue) => issue.key);
  }

  function loadCompletedHistoryCache() {
    try {
      const raw = localStorage.getItem(COMPLETED_HISTORY_CACHE_KEY);
      if (!raw) return false;

      const payload = JSON.parse(raw) as Partial<CompletedHistoryCache>;
      if (payload.version !== 1 || !Array.isArray(payload.issues)) {
        localStorage.removeItem(COMPLETED_HISTORY_CACHE_KEY);
        return false;
      }

      completedIssues = normalizeCompletedIssues(payload.issues);
      try {
        localStorage.setItem(
          COMPLETED_HISTORY_CACHE_KEY,
          JSON.stringify({
            version: 1,
            cachedAt: String(payload.cachedAt || new Date().toISOString()),
            issues: completedIssues
          } satisfies CompletedHistoryCache)
        );
      } catch {
        void 0;
      }
      completedError = '';
      return true;
    } catch {
      localStorage.removeItem(COMPLETED_HISTORY_CACHE_KEY);
      return false;
    }
  }

  function saveCompletedHistoryCache(issues: JiraIssue[]) {
    const payload: CompletedHistoryCache = {
      version: 1,
      cachedAt: new Date().toISOString(),
      issues,
    };

    try {
      localStorage.setItem(COMPLETED_HISTORY_CACHE_KEY, JSON.stringify(payload));
    } catch {
      return;
    }
  }

  async function fetchCompletedHistory(forceRefresh = false) {
    if (!forceRefresh && loadCompletedHistoryCache()) return;

    const requestId = ++completedRequestId;
    completedLoading = true;
    completedError = '';
    try {
      const data = await useJiraCompletedHistory('all');
      if (requestId !== completedRequestId) return;
      completedIssues = normalizeCompletedIssues(data.issues || []);
      saveCompletedHistoryCache(completedIssues);
    } catch (e: any) {
      if (requestId !== completedRequestId) return;
      completedError = String(e?.message || e || 'Errore caricamento issue completate');
    } finally {
      if (requestId === completedRequestId) {
        completedLoading = false;
      }
    }
  }

  $: availableYears = Array.from(
    new Set(
      completedIssues
        .map((issue) => issueYear(issue))
        .filter((year): year is number => year !== null)
    )
  ).sort((a, b) => b - a);

  $: chartIssues =
    selectedYear === 'all'
      ? completedIssues
      : completedIssues.filter((issue) => String(issueYear(issue) || '') === selectedYear);
  $: if (selectedYear === 'all') {
    yearlyWorklogData = null;
    yearlyWorklogError = '';
    yearlyWorklogLoading = false;
    lastFetchedYear = '';
  }
  $: if (selectedYear !== 'all' && selectedYear !== lastFetchedYear) {
    lastFetchedYear = selectedYear;
    void fetchYearlyWorklogs(selectedYear);
  }

  onMount(async () => {
    const jiraEnabled = await ensureJiraControlLoaded();
    if (!jiraEnabled) {
      goto('/', { replaceState: true });
      return;
    }
    void fetchCompletedHistory();
  });

  $: if ($jiraControl.loaded && !$jiraControl.enabled) {
    goto('/', { replaceState: true });
  }
</script>

<main class="history-page">
  <h1 class="page-title">Jira History</h1>
  <header class="page-header">
    <div class="header-main">
      <div>
        <button
          class="back-arrow-btn"
          type="button"
          on:click={() => goto('/business')}
          aria-label="Torna alla pagina business"
          title="Torna alla pagina business"
        >
          ←
        </button>
        <p>Analisi ore su progetti completati e distribuzione in base ai progetti selezionati.</p>
      </div>
      <div class="search-wrap">
        <span class="search-ico">/</span>
        <input
          type="text"
          class="search-input"
          bind:value={searchQuery}
          placeholder="Cerca progetto (chiave o nome)..."
        />
      </div>
      <div class="year-wrap">
        <label for="year-filter">Anno</label>
        <select id="year-filter" class="year-select" bind:value={selectedYear}>
          <option value="all">Tutti</option>
          {#each availableYears as year (year)}
            <option value={String(year)}>{year}</option>
          {/each}
        </select>
      </div>
    </div>
  </header>

  <section class="layout-row">
    <div class="left-pane">
      <JiraCompletedBar
        bind:issuesData={completedIssues}
        bind:selectedProjectKeys
        {searchQuery}
        {selectedYear}
        loading={completedLoading}
        error={completedError}
        on:refresh={() => fetchCompletedHistory(true)}
      />
    </div>

    <aside class="right-pane">
      <JiraHistoryCharts issues={chartIssues} {selectedProjectKeys} />
    </aside>
  </section>

  <section class="worklogs-tree">
    <div class="tree-head">
      <h3>Worklog annuali</h3>
      {#if selectedYear !== 'all'}
        <button type="button" class="refresh-tree-btn" on:click={() => fetchYearlyWorklogs(selectedYear)} disabled={yearlyWorklogLoading}>
          {yearlyWorklogLoading ? 'Aggiorno...' : 'Aggiorna'}
        </button>
      {/if}
    </div>

    {#if selectedYear === 'all'}
      <p class="tree-state">Seleziona un anno per caricare i worklog annuali per progetto → issue → worklog.</p>
    {:else if yearlyWorklogLoading && !yearlyWorklogData}
      <p class="tree-state">Caricamento worklog annuali...</p>
    {:else if yearlyWorklogError}
      <p class="tree-state error">{yearlyWorklogError}</p>
    {:else if !yearlyWorklogData || yearlyWorklogData.projects_count === 0}
      <p class="tree-state">Nessun worklog trovato per l'anno selezionato.</p>
    {:else}
      <p class="tree-summary">
        Progetti: {yearlyWorklogData.projects_count} · Issue: {yearlyWorklogData.issues_count} · Worklog: {yearlyWorklogData.worklogs_count} · Ore: {fmtHours(yearlyWorklogData.total_seconds)}
      </p>
      <div class="tree-projects">
        {#each yearlyWorklogData.projects as project (project.project_key)}
          <article class="tree-project-card">
            <h4>{project.project_key} - {project.project_name}</h4>
            <p class="project-meta">
              {project.issues_count} issue · {project.worklogs_count} worklog · {fmtHours(project.total_seconds)}
            </p>

            <div class="tree-issues">
              {#each project.issues as issue (issue.issue_key)}
                <details class="tree-issue">
                  <summary>
                    <span class="issue-key">{issue.issue_key}</span>
                    <span class="issue-summary">{issue.issue_summary || '-'}</span>
                    <span class="issue-meta">{issue.worklogs_count} worklog · {fmtHours(issue.total_seconds)}</span>
                  </summary>
                  <ul class="worklog-list">
                    {#each issue.worklogs as worklog (worklog.worklog_id || `${issue.issue_key}-${worklog.started || ''}`)}
                      <li>
                        <span class="worklog-time">{fmtDateTime(worklog.started)}</span>
                        <span class="worklog-author">{worklog.author || 'Unassigned'}</span>
                        <span class="worklog-value">{worklog.time_spent || fmtHours(worklog.time_spent_seconds || 0)}</span>
                        {#if worklog.comment}
                          <p class="worklog-comment">{worklog.comment}</p>
                        {/if}
                      </li>
                    {/each}
                  </ul>
                </details>
              {/each}
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</main>

<style>
  .history-page {
    max-width: 1456px;
    margin: 0 auto;
    padding: 1.25rem 0 2.4rem;
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
  .search-wrap {
    min-width: 320px;
    width: min(420px, 100%);
    position: relative;
  }
  .year-wrap {
    display: grid;
    gap: 0.22rem;
    min-width: 130px;
  }
  .year-wrap label {
    font-size: 0.7rem;
    color: #64748b;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .year-select {
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    font-size: 13px;
    color: #0f172a;
    background: #fff;
    padding: 8px 10px;
    outline: none;
    min-height: 36px;
  }
  .year-select:focus {
    border-color: #94a3b8;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.2);
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
  .search-ico {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #64748b;
    font-size: 13px;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    font-size: 13px;
    color: #0f172a;
    background: #fff;
    padding: 8px 10px 8px 28px;
    outline: none;
  }
  .search-input:focus {
    border-color: #94a3b8;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.2);
  }

  .layout-row {
    display: grid;
    grid-template-columns: 45% minmax(0, 55%);
    gap: 12px;
    align-items: start;
  }

  .left-pane,
  .right-pane {
    min-width: 0;
  }

  .left-pane {
    position: sticky;
    top: 1rem;
  }

  .worklogs-tree {
    margin-top: 0.95rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    padding: 0.85rem 0.95rem;
  }
  .tree-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
  }
  .tree-head h3 {
    margin: 0;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #0f172a;
    font-family: var(--font-mono);
  }
  .refresh-tree-btn {
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    background: #fff;
    color: #334155;
    font-size: 0.72rem;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    font-family: var(--font-mono);
  }
  .refresh-tree-btn:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }
  .tree-state {
    margin: 0.6rem 0 0;
    font-size: 0.78rem;
    color: #475569;
    font-family: var(--font-mono);
  }
  .tree-state.error {
    color: #b91c1c;
  }
  .tree-summary {
    margin: 0.55rem 0 0.7rem;
    font-size: 0.75rem;
    color: #334155;
    font-family: var(--font-mono);
  }
  .tree-projects {
    display: grid;
    gap: 0.65rem;
  }
  .tree-project-card {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #f8fafc;
    padding: 0.6rem 0.7rem;
  }
  .tree-project-card h4 {
    margin: 0;
    font-size: 0.8rem;
    color: #0f172a;
    font-family: var(--font-mono);
  }
  .project-meta {
    margin: 0.22rem 0 0.45rem;
    font-size: 0.7rem;
    color: #475569;
    font-family: var(--font-mono);
  }
  .tree-issues {
    display: grid;
    gap: 0.45rem;
  }
  .tree-issue {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #fff;
    padding: 0.38rem 0.45rem;
  }
  .tree-issue summary {
    list-style: none;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }
  .issue-key,
  .issue-meta {
    font-size: 0.68rem;
    color: #334155;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .issue-summary {
    min-width: 0;
    font-size: 0.74rem;
    color: #0f172a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .worklog-list {
    margin: 0.45rem 0 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 5px;
  }
  .worklog-list li {
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    background: #f8fafc;
    padding: 0.35rem 0.45rem;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 7px;
  }
  .worklog-time,
  .worklog-author,
  .worklog-value {
    font-size: 0.68rem;
    color: #334155;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .worklog-comment {
    margin: 0.2rem 0 0;
    grid-column: 1 / -1;
    font-size: 0.7rem;
    color: #475569;
    line-height: 1.3;
  }

  @media (max-width: 1200px) {
    .page-title {
      font-size: 1.76rem;
      margin-bottom: 0.55rem;
    }
    .header-main {
      flex-direction: column;
    }
    .search-wrap {
      min-width: 0;
      width: 100%;
    }
    .year-wrap {
      width: 100%;
    }
    .layout-row {
      grid-template-columns: 1fr;
    }

    .left-pane {
      position: static;
    }
  }
  @media (max-width: 720px) {
    .tree-issue summary {
      grid-template-columns: 1fr;
      align-items: start;
    }
    .worklog-list li {
      grid-template-columns: 1fr;
      align-items: start;
    }
    .issue-summary {
      white-space: normal;
    }
  }
  @media (max-width: 480px) {
    .page-title {
      font-size: 1.56rem;
    }
  }
</style>
