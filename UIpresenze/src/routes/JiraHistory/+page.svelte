<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { useJiraWorklogsByYearStream } from '$lib/hooks/useJira';
  import type {
    JiraHistoryIssue,
    JiraYearWorklogIssue,
    JiraYearWorklogResponse
  } from '$lib/services/jira';
  import JiraCompletedBar from '$lib/components/Jira/JiraCompletedBar.svelte';
  import JiraHistoryCharts from '$lib/components/Jira/JiraHistoryCharts.svelte';
  import { ensureJiraControlLoaded, jiraControl } from '$lib/stores/jiraControl';

  type JiraIssue = JiraHistoryIssue;
  type UserSubtask = {
    key: string;
    summary: string;
    projectKey: string;
    parentKey: string;
    parentSummary: string;
    seconds: number;
    worklogsCount: number;
  };
  type UserSubtaskGroup = {
    id: string;
    name: string;
    seconds: number;
    worklogsCount: number;
    subtasks: UserSubtask[];
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

  let selectedProjectKeys: string[] = [];
  let completedIssues: JiraIssue[] = [];
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
  let leftPaneEl: HTMLDivElement | null = null;
  let chartsMaxHeight = '';
  let layoutResizeObserver: ResizeObserver | null = null;

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

  async function fetchYearlyWorklogs(year: number, month: number | 'all') {
    yearlyWorklogController?.abort();
    const controller = new AbortController();
    yearlyWorklogController = controller;
    const requestId = ++yearlyWorklogRequestId;
    yearlyWorklogLoading = true;
    yearlyWorklogData = null;
    completedIssues = [];
    yearlyWorklogError = '';
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
      yearlyWorklogData = data;
      completedIssues = normalizeCompletedIssues(data.completed_issues || []);
    } catch (e: any) {
      if (requestId !== yearlyWorklogRequestId) return;
      if (e?.name === 'AbortError') return;
      yearlyWorklogData = null;
      completedIssues = [];
      yearlyWorklogError = String(e?.message || e || 'Errore caricamento worklog del periodo');
    } finally {
      if (requestId === yearlyWorklogRequestId) {
        yearlyWorklogLoading = false;
        yearlyWorklogController = null;
      }
    }
  }

  function syncChartsMaxHeight() {
    if (!leftPaneEl) {
      chartsMaxHeight = '';
      return;
    }

    const height = leftPaneEl.getBoundingClientRect().height;
    chartsMaxHeight = height > 0 ? `${Math.ceil(height)}px` : '';
  }

  function completedIssueIsSubtask(issue: JiraIssue) {
    const typeName = String(issue.fields?.issuetype?.name || '').toLowerCase();
    return Boolean(
      issue.fields?.issuetype?.subtask ||
      typeName.includes('sub-task') ||
      typeName.includes('subtask') ||
      typeName.includes('sotto-attività') ||
      typeName.includes('sottoattività') ||
      typeName.includes('sottotask')
    );
  }

  function streamIssueIsSubtask(issue: JiraYearWorklogIssue, knownSubtaskKeys: Set<string>) {
    const typeName = String(issue.issue_type || '').toLowerCase();
    return Boolean(
      issue.is_subtask ||
      knownSubtaskKeys.has(issue.issue_key) ||
      typeName.includes('sub-task') ||
      typeName.includes('subtask') ||
      typeName.includes('sotto-attività') ||
      typeName.includes('sottoattività') ||
      typeName.includes('sottotask')
    );
  }

  function groupSubtasksByUser(
    data: JiraYearWorklogResponse | null,
    knownSubtaskKeys: Set<string>,
    selectedKeys: string[]
  ): UserSubtaskGroup[] {
    if (!data) return [];

    const selected = new Set(selectedKeys);
    const users = new Map<string, UserSubtaskGroup>();
    for (const project of data.projects || []) {
      if (selected.size > 0 && !selected.has(project.project_key)) continue;

      for (const issue of project.issues || []) {
        if (!streamIssueIsSubtask(issue, knownSubtaskKeys)) continue;

        const issueUsers = new Map<string, { name: string; seconds: number; worklogsCount: number }>();
        for (const worklog of issue.worklogs || []) {
          const seconds = Math.max(0, Number(worklog.time_spent_seconds || 0));
          if (seconds <= 0) continue;
          const name = String(worklog.author || '').trim() || 'Utente non assegnato';
          const userId = String(worklog.author_account_id || '').trim() || name;
          const row = issueUsers.get(userId) || { name, seconds: 0, worklogsCount: 0 };
          row.seconds += seconds;
          row.worklogsCount += 1;
          issueUsers.set(userId, row);
        }

        for (const [userId, issueUser] of issueUsers) {
          const user = users.get(userId) || {
            id: userId,
            name: issueUser.name,
            seconds: 0,
            worklogsCount: 0,
            subtasks: []
          };
          user.seconds += issueUser.seconds;
          user.worklogsCount += issueUser.worklogsCount;
          user.subtasks.push({
            key: issue.issue_key,
            summary: issue.issue_summary || '-',
            projectKey: project.project_key,
            parentKey: issue.parent_key || '',
            parentSummary: issue.parent_summary || '',
            seconds: issueUser.seconds,
            worklogsCount: issueUser.worklogsCount
          });
          users.set(userId, user);
        }
      }
    }

    return Array.from(users.values())
      .map((user) => ({
        ...user,
        subtasks: user.subtasks.sort((a, b) => b.seconds - a.seconds || a.key.localeCompare(b.key))
      }))
      .sort((a, b) => b.seconds - a.seconds || a.name.localeCompare(b.name));
  }

  function normalizeCompletedIssue(issue: JiraIssue): JiraIssue | null {
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
        subtasks: normalizeCompletedIssues(fields.subtasks || []),
        subtasks_enriched: normalizeCompletedIssues(fields.subtasks_enriched || []),
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

  function normalizeCompletedIssues(issues: JiraIssue[]): JiraIssue[] {
    return (issues || [])
      .map(normalizeCompletedIssue)
      .filter((issue): issue is JiraIssue => issue !== null);
  }

  function flattenCompletedIssues(issues: JiraIssue[]): JiraIssue[] {
    return (issues || []).flatMap((issue) => [
      issue,
      ...flattenCompletedIssues(issue.fields?.subtasks_enriched || [])
    ]);
  }

  $: flattenedCompletedIssues = flattenCompletedIssues(completedIssues);
  $: chartIssues = flattenedCompletedIssues;
  $: knownSubtaskKeys = new Set(
    flattenedCompletedIssues.filter(completedIssueIsSubtask).map((issue) => issue.key)
  );
  $: userSubtaskGroups = groupSubtasksByUser(yearlyWorklogData, knownSubtaskKeys, selectedProjectKeys);
  $: userSubtasksTotalSeconds = userSubtaskGroups.reduce((total, user) => total + user.seconds, 0);
  $: selectedYearlyProjectKeys = new Set(selectedProjectKeys);
  $: visibleYearlyWorklogProjects =
    selectedProjectKeys.length > 0
      ? (yearlyWorklogData?.projects || []).filter((project) =>
          selectedYearlyProjectKeys.has(project.project_key)
        )
      : [];
  $: visibleYearlyWorklogSummary = {
    projectsCount: visibleYearlyWorklogProjects.length,
    issuesCount: visibleYearlyWorklogProjects.reduce((total, project) => total + project.issues_count, 0),
    worklogsCount: visibleYearlyWorklogProjects.reduce((total, project) => total + project.worklogs_count, 0),
    totalSeconds: visibleYearlyWorklogProjects.reduce((total, project) => total + project.total_seconds, 0)
  };
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
    requestAnimationFrame(syncChartsMaxHeight);
    if (leftPaneEl) {
      layoutResizeObserver = new ResizeObserver(syncChartsMaxHeight);
      layoutResizeObserver.observe(leftPaneEl);
    }
    jiraHistoryReady = true;
  });

  onDestroy(() => {
    yearlyWorklogController?.abort();
    layoutResizeObserver?.disconnect();
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
      </div>
    </div>
  </header>

  <section class="layout-row">
    <div class="left-pane" bind:this={leftPaneEl}>
      <JiraCompletedBar
        bind:issuesData={completedIssues}
        bind:selectedProjectKeys
        loading={yearlyWorklogLoading}
        error={yearlyWorklogError}
        on:refresh={() => fetchYearlyWorklogs(selectedYear, selectedMonth)}
      />
    </div>

    <aside class="right-pane" style={chartsMaxHeight ? `max-height:${chartsMaxHeight}` : undefined}>
      <JiraHistoryCharts issues={chartIssues} {selectedProjectKeys} />
    </aside>
  </section>

  <section class="subtask-users" data-history-hover>
    <div class="subtask-users-head">
      <div>
        <h3>Ore sottotask per utente</h3>
        <p>Ore effettive dei worklog del periodo selezionato, separate per autore e sottotask.</p>
      </div>
      {#if userSubtaskGroups.length > 0}
        <strong>{userSubtaskGroups.length} utenti · {fmtHours(userSubtasksTotalSeconds)}</strong>
      {/if}
    </div>

    {#if yearlyWorklogLoading && !yearlyWorklogData}
      <div class="stream-progress" data-history-hover-exclude>
        <div>
          <span>Caricamento worklog del periodo...</span>
          {#if yearlyWorklogProgress?.total}
            <strong>{yearlyWorklogProgress.loaded}/{yearlyWorklogProgress.total}</strong>
          {/if}
        </div>
        <progress
          max={Math.max(1, yearlyWorklogProgress?.total || 1)}
          value={yearlyWorklogProgress?.loaded || 0}
        ></progress>
      </div>
    {:else if yearlyWorklogError}
      <p class="tree-state error">{yearlyWorklogError}</p>
    {:else if userSubtaskGroups.length === 0}
      <p class="tree-state">
        Nessuna sottotask con ore trovata{selectedProjectKeys.length > 0 ? ' per i progetti selezionati' : ''}.
      </p>
    {:else}
      <div class="user-subtask-grid">
        {#each userSubtaskGroups as user (user.id)}
          <article class="user-subtask-card" data-history-hover>
            <header>
              <div>
                <h4>{user.name}</h4>
                <span>{user.subtasks.length} sottotask · {user.worklogsCount} worklog</span>
              </div>
              <strong>{fmtHours(user.seconds)}</strong>
            </header>
            <ul>
              {#each user.subtasks as subtask (`${user.id}-${subtask.key}`)}
                <li data-history-hover>
                  <div class="user-subtask-main">
                    <span class="subtask-project" data-history-hover-exclude>{subtask.projectKey}</span>
                    <span class="subtask-key">{subtask.key}</span>
                    <span class="user-subtask-summary">{subtask.summary}</span>
                  </div>
                  <strong>{fmtHours(subtask.seconds)}</strong>
                  {#if subtask.parentKey}
                    <small>
                      Parent: {subtask.parentKey}{subtask.parentSummary ? ` · ${subtask.parentSummary}` : ''}
                    </small>
                  {/if}
                </li>
              {/each}
            </ul>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  <section class="worklogs-tree" data-history-hover>
    <div class="tree-head">
      <h3>Worklog del periodo</h3>
      <button type="button" class="refresh-tree-btn" on:click={() => fetchYearlyWorklogs(selectedYear, selectedMonth)} disabled={yearlyWorklogLoading}>
        {yearlyWorklogLoading ? 'Aggiorno...' : 'Aggiorna'}
      </button>
    </div>
    <p class="tree-subtitle">
      Ore effettivamente loggate nel periodo selezionato, attribuite per data del singolo worklog
      (indipendentemente dall'anno di chiusura dell'issue).
    </p>

    {#if yearlyWorklogLoading && !yearlyWorklogData}
      <p class="tree-state">
        Caricamento worklog del periodo...
        {#if yearlyWorklogProgress?.total}
          {yearlyWorklogProgress.loaded}/{yearlyWorklogProgress.total}
        {/if}
      </p>
    {:else if yearlyWorklogError}
      <p class="tree-state error">{yearlyWorklogError}</p>
    {:else if selectedProjectKeys.length === 0}
      <p class="tree-state">Seleziona almeno un progetto completato per visualizzare i worklog annuali.</p>
    {:else if !yearlyWorklogData || yearlyWorklogData.projects_count === 0}
      <p class="tree-state">Nessun worklog trovato per il periodo selezionato.</p>
    {:else if visibleYearlyWorklogProjects.length === 0}
      <p class="tree-state">Nessun worklog trovato per i progetti selezionati nel periodo scelto.</p>
    {:else}
      <p class="tree-summary">
        Progetti: {visibleYearlyWorklogSummary.projectsCount} · Issue: {visibleYearlyWorklogSummary.issuesCount} · Worklog: {visibleYearlyWorklogSummary.worklogsCount} · Ore: {fmtHours(visibleYearlyWorklogSummary.totalSeconds)}
      </p>
      <div class="tree-projects">
        {#each visibleYearlyWorklogProjects as project (project.project_key)}
          <article class="tree-project-card" data-history-hover>
            <h4>{project.project_key} - {project.project_name}</h4>
            <p class="project-meta">
              {project.issues_count} issue · {project.worklogs_count} worklog · {fmtHours(project.total_seconds)}
            </p>

            <div class="tree-issues">
              {#each project.issues as issue (issue.issue_key)}
                <details class="tree-issue" data-history-hover>
                  <summary>
                    <span class="issue-key">{issue.issue_key}</span>
                    <span class="issue-summary">{issue.issue_summary || '-'}</span>
                    <span class="issue-meta">{issue.worklogs_count} worklog · {fmtHours(issue.total_seconds)}</span>
                  </summary>
                  <ul class="worklog-list">
                    {#each issue.worklogs as worklog (worklog.worklog_id || `${issue.issue_key}-${worklog.started || ''}`)}
                      <li data-history-hover>
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

  .right-pane {
    overflow-y: auto;
    padding-right: 4px;
  }

  .subtask-users {
    order: 4;
    margin-top: 0.95rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    padding: 0.85rem 0.95rem;
  }
  .subtask-users-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.8rem;
  }
  .subtask-users-head h3 {
    margin: 0;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #0f172a;
    font-family: var(--font-mono);
  }
  .subtask-users-head p {
    margin: 0.22rem 0 0;
    color: #64748b;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }
  .subtask-users-head > strong {
    color: #0f172a;
    font-size: 0.78rem;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .stream-progress {
    display: grid;
    gap: 0.4rem;
    margin-top: 0.7rem;
  }
  .stream-progress div {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    color: #475569;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }
  .stream-progress progress {
    width: 100%;
    height: 7px;
    accent-color: #2563eb;
  }
  .user-subtask-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin-top: 0.7rem;
  }
  .user-subtask-card {
    min-width: 0;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: #f8fafc;
    padding: 0.65rem;
  }
  .user-subtask-card > header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.7rem;
    margin-bottom: 0.5rem;
  }
  .user-subtask-card h4 {
    margin: 0;
    color: #0f172a;
    font-size: 0.82rem;
    font-family: var(--font-mono);
  }
  .user-subtask-card header span {
    display: block;
    margin-top: 0.18rem;
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
  }
  .user-subtask-card header strong {
    color: #0f172a;
    font-size: 0.82rem;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .user-subtask-card ul {
    display: grid;
    gap: 5px;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .user-subtask-card li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 8px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #fff;
    padding: 0.42rem 0.5rem;
  }
  .user-subtask-main {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 6px;
  }
  .subtask-project,
  .subtask-key,
  .user-subtask-card li > strong {
    color: #334155;
    font-size: 0.67rem;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .subtask-project {
    border-radius: 999px;
    background: #e0e7ff;
    color: #3730a3;
    padding: 0.12rem 0.35rem;
  }
  .user-subtask-summary {
    min-width: 0;
    overflow: hidden;
    color: #0f172a;
    font-size: 0.72rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .user-subtask-card small {
    grid-column: 1 / -1;
    overflow: hidden;
    color: #64748b;
    font-size: 0.63rem;
    font-family: var(--font-mono);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .worklogs-tree {
    order: 3;
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
  .tree-subtitle {
    margin: 0.35rem 0 0;
    max-width: 70ch;
    color: #64748b;
    font-size: 0.7rem;
    line-height: 1.35;
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
    .period-filters {
      width: 100%;
    }
    .period-filter {
      flex: 1 1 0;
    }
    .layout-row {
      grid-template-columns: 1fr;
    }

    .left-pane {
      position: static;
    }

    .right-pane {
      max-height: none !important;
      overflow: visible;
      padding-right: 0;
    }
  }
  @media (max-width: 720px) {
    .subtask-users-head {
      flex-direction: column;
    }
    .user-subtask-grid {
      grid-template-columns: 1fr;
    }
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
