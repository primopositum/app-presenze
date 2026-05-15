<script lang="ts">
  import { onMount } from 'svelte';
  import { jiraSearch } from '$lib/services/jira';

  type JiraIssue = {
    key: string;
    fields?: {
      summary?: string;
      status?: { name?: string };
      assignee?: { displayName?: string } | null;
      issuetype?: { name?: string; subtask?: boolean } | null;
      parent?: { key?: string; fields?: { summary?: string } } | null;
      project?: { key?: string; name?: string };
      timespent?: number | null;
      aggregatetimespent?: number | null;
      timeestimate?: number | null;
      aggregatetimeestimate?: number | null;
      timeoriginalestimate?: number | null;
      aggregatetimeoriginalestimate?: number | null;
      timetracking?: {
        timeSpentSeconds?: number;
        originalEstimateSeconds?: number;
      } | null;
    };
  };

  type ProjectSummary = {
    key: string;
    name: string;
    seconds: number;
    issueCount: number;
  };

  export let issuesData: JiraIssue[] = [];
  export let selectedProjectKeys: string[] = [];
  export let searchQuery = '';

  let loading = false;
  let error = '';

  function clearSelection() {
    selectedProjectKeys = [];
  }

  function taskTotalSeconds(fields?: JiraIssue['fields']) {
    if (!fields) return 0;
    return (
      fields.aggregatetimespent ??
      fields.timespent ??
      fields.timetracking?.timeSpentSeconds ??
      fields.aggregatetimeestimate ??
      fields.timeestimate ??
      fields.aggregatetimeoriginalestimate ??
      fields.timeoriginalestimate ??
      fields.timetracking?.originalEstimateSeconds ??
      0
    );
  }

  function fmtHours(seconds: number) {
    const hours = seconds / 3600;
    const rounded = Math.round(hours * 10) / 10;
    return Number.isInteger(rounded)
      ? `${rounded.toFixed(0)}h`
      : `${rounded.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}h`;
  }

  function normalizeSelection() {
    const availableKeys = new Set(projects.map((p) => p.key));
    selectedProjectKeys = selectedProjectKeys.filter((key) => availableKeys.has(key));
  }

  function toggleProject(key: string) {
    if (!key) return;
    selectedProjectKeys = selectedProjectKeys.includes(key)
      ? selectedProjectKeys.filter((k) => k !== key)
      : [...selectedProjectKeys, key];
  }

  function isSubtask(issue: JiraIssue) {
    const issueType = issue.fields?.issuetype;
    const typeName = String(issueType?.name || '').toLowerCase();
    return Boolean(issueType?.subtask) || typeName.includes('sub-task') || typeName.includes('subtask') || Boolean(issue.fields?.parent);
  }

  async function fetchCompleted() {
    loading = true;
    error = '';
    try {
      const data = await jiraSearch({
        jql: '(statusCategory = Done OR status in ("Completed","Completata")) ORDER BY updated DESC',
        fields:
          'summary,status,assignee,issuetype,parent,project,timetracking,timespent,aggregatetimespent,timeestimate,aggregatetimeestimate,timeoriginalestimate,aggregatetimeoriginalestimate'
      });
      issuesData = (data?.issues || []) as JiraIssue[];
      normalizeSelection();
    } catch (e: any) {
      error = String(e?.message || e || 'Errore caricamento');
    } finally {
      loading = false;
    }
  }

  $: normalizedSearch = searchQuery.trim().toLowerCase();
  $: projects = Object.values(
    issuesData.reduce<Record<string, ProjectSummary>>((acc, issue) => {
      const projectKey = issue.fields?.project?.key || 'N/D';
      const projectName = issue.fields?.project?.name || 'Progetto non disponibile';
      if (!acc[projectKey]) {
        acc[projectKey] = {
          key: projectKey,
          name: projectName,
          seconds: 0,
          issueCount: 0
        };
      }
      acc[projectKey].seconds += Math.max(0, Number(taskTotalSeconds(issue.fields) || 0));
      acc[projectKey].issueCount += 1;
      return acc;
    }, {})
  ).sort((a, b) => b.seconds - a.seconds);

  $: filteredProjects = projects.filter((project) => {
    if (!normalizedSearch) return true;
    return (
      project.key.toLowerCase().includes(normalizedSearch) ||
      project.name.toLowerCase().includes(normalizedSearch)
    );
  });

  $: selectedCount = selectedProjectKeys.length;
  $: totalCount = filteredProjects.length;
  $: totalHours = filteredProjects.reduce((acc, p) => acc + p.seconds, 0);
  $: selectedHours = filteredProjects
    .filter((p) => selectedProjectKeys.includes(p.key))
    .reduce((acc, p) => acc + p.seconds, 0);
  $: selectedIssues = issuesData.filter((issue) => selectedProjectKeys.includes(issue.fields?.project?.key || 'N/D'));
  $: completedSubtasks = selectedIssues.filter(isSubtask);
  $: if (selectedProjectKeys.length > 0) {
    const available = new Set(projects.map((p) => p.key));
    selectedProjectKeys = selectedProjectKeys.filter((key) => available.has(key));
  }

  onMount(fetchCompleted);
</script>

<section class="completed-bar">
  <div class="head">
    <div>
      <h2>Progetti completati</h2>
      <p class="subhead">{selectedCount} selezionati su {totalCount}</p>
      <p class="subhead hours">
        Ore: {fmtHours(selectedCount > 0 ? selectedHours : totalHours)}
      </p>
    </div>
    <div class="head-actions">
      <button type="button" class="ghost" on:click={clearSelection} disabled={loading || selectedCount === 0}>
        Pulisci
      </button>
      <button type="button" on:click={fetchCompleted} disabled={loading}>{loading ? '...' : 'Aggiorna'}</button>
    </div>
  </div>

  {#if error}
    <div class="state error">{error}</div>
  {:else if loading && issuesData.length === 0}
    <div class="state">Caricamento...</div>
  {:else if filteredProjects.length === 0}
    <div class="state">Nessun progetto completato trovato</div>
  {:else}
    <div class="cards-scroll">
      <div class="cards">
        {#each filteredProjects as project (project.key)}
          <div
            class="project-card"
            class:selected={selectedProjectKeys.includes(project.key)}
            role="button"
            tabindex="0"
            on:click={() => toggleProject(project.key)}
            on:keydown={(e) => (e.key === 'Enter' || e.key === ' ' ? toggleProject(project.key) : undefined)}
          >
            <div class="row-top">
              <span class="project-key">{project.key}</span>
              <span class="issues-pill">{project.issueCount} issue</span>
            </div>
            <h3>{project.name}</h3>
            <p class="hours-pill">Ore totali: {fmtHours(project.seconds)}</p>
          </div>
        {/each}
      </div>
    </div>
    {#if selectedProjectKeys.length > 0}
      <div class="subtasks-panel">
        <h4>Sottotask completate ({completedSubtasks.length})</h4>
        {#if completedSubtasks.length === 0}
          <p class="subtasks-empty">Nessuna sottotask completata trovata per i progetti selezionati.</p>
        {:else}
          <div class="subtasks-list">
            {#each completedSubtasks as issue (issue.key)}
              <article class="subtask-item">
                <div class="subtask-head">
                  <span class="subtask-key">{issue.key}</span>
                  <span class="subtask-hours">{fmtHours(Math.max(0, Number(taskTotalSeconds(issue.fields) || 0)))}</span>
                </div>
                <p class="subtask-summary">{issue.fields?.summary || '-'}</p>
                <p class="subtask-meta">
                  {issue.fields?.assignee?.displayName || 'Unassigned'}
                  {#if issue.fields?.status?.name}
                    • {issue.fields?.status?.name}
                  {/if}
                </p>
              </article>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</section>

<style>
  .completed-bar {
    border: 1px solid #bbf7d0;
    border-radius: 14px;
    background: linear-gradient(180deg, #f0fdf4, #ffffff 35%);
    padding: 0.9rem;
    min-width: 0;
  }

  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.8rem;
    margin-bottom: 0.8rem;
    position: sticky;
    top: 0;
    z-index: 4;
    background: linear-gradient(180deg, #f0fdf4 76%, rgba(240, 253, 244, 0));
    padding-bottom: 0.35rem;
  }

  .head h2 {
    margin: 0;
    font-size: 0.95rem;
    color: #14532d;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    font-family: var(--font-mono);
  }

  .subhead {
    margin: 0.12rem 0 0;
    color: #166534;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }
  .subhead.hours {
    font-weight: 700;
  }

  .head-actions {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .head button {
    border: 1px solid #86efac;
    background: #ffffff;
    color: #166534;
    border-radius: 8px;
    font-size: 0.72rem;
    padding: 4px 8px;
    cursor: pointer;
    font-family: var(--font-mono);
  }

  .head .ghost {
    background: #f8fff9;
    color: #14532d;
  }

  .head button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .state {
    font-size: 0.82rem;
    color: #166534;
    padding: 0.4rem 0;
    font-family: var(--font-mono);
  }

  .state.error {
    color: #b91c1c;
  }

  .cards-scroll {
    margin-top: 0.9rem;
    max-height: 68vh;
    overflow-y: auto;
    padding-right: 4px;
  }

  .cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .project-card {
    position: relative;
    border-radius: 12px;
    cursor: pointer;
    border: 1px solid #bbf7d0;
    background: #ffffff;
    padding: 0.7rem 0.75rem;
    transition: box-shadow 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
  }
  .project-card:hover {
    transform: translateY(-1px);
    border-color: #86efac;
    box-shadow: 0 6px 14px rgba(22, 163, 74, 0.14);
  }
  .project-card.selected {
    border-color: #22c55e;
    box-shadow: 0 0 0 2px #22c55e, 0 6px 14px rgba(22, 163, 74, 0.2);
    background: #f0fdf4;
  }
  .row-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 0.42rem;
  }
  .project-key {
    font-size: 11px;
    color: #14532d;
    background: #ecfdf5;
    border: 1px solid #86efac;
    border-radius: 999px;
    padding: 2px 8px;
    font-family: var(--font-mono);
  }
  .issues-pill {
    font-size: 10px;
    color: #14532d;
    font-family: var(--font-mono);
    background: #ffffff;
    border: 1px solid #bbf7d0;
    border-radius: 999px;
    padding: 2px 7px;
  }
  h3 {
    margin: 0 0 0.4rem;
    font-size: 0.86rem;
    color: #14532d;
    line-height: 1.2;
    font-family: var(--font-infinity);
    letter-spacing: 0.01em;
  }
  .hours-pill {
    margin: 0;
    font-size: 0.74rem;
    color: #166534;
    font-family: var(--font-mono);
  }
  .subtasks-panel {
    margin-top: 0.85rem;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    background: #f8fff9;
    padding: 0.65rem;
  }
  .subtasks-panel h4 {
    margin: 0 0 0.55rem;
    font-size: 0.76rem;
    color: #14532d;
    text-transform: uppercase;
    font-family: var(--font-mono);
    letter-spacing: 0.03em;
  }
  .subtasks-empty {
    margin: 0;
    font-size: 0.74rem;
    color: #166534;
    font-family: var(--font-mono);
  }
  .subtasks-list {
    display: grid;
    gap: 7px;
    max-height: 260px;
    overflow: auto;
    padding-right: 3px;
  }
  .subtask-item {
    border: 1px solid #dcfce7;
    background: #ffffff;
    border-radius: 9px;
    padding: 0.5rem 0.6rem;
  }
  .subtask-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 7px;
    margin-bottom: 0.25rem;
  }
  .subtask-key,
  .subtask-hours {
    font-size: 10px;
    font-family: var(--font-mono);
    color: #14532d;
    background: #ecfdf5;
    border: 1px solid #86efac;
    border-radius: 999px;
    padding: 2px 7px;
    white-space: nowrap;
  }
  .subtask-summary {
    margin: 0 0 0.25rem;
    font-size: 0.74rem;
    color: #14532d;
    line-height: 1.3;
  }
  .subtask-meta {
    margin: 0;
    font-size: 0.68rem;
    color: #166534;
    font-family: var(--font-mono);
  }

  @media (max-width: 1100px) {
    .cards-scroll {
      max-height: 56vh;
    }
  }
</style>
