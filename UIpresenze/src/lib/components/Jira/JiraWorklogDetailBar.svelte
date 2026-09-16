<script lang="ts">
  import type {
    JiraHistoryIssue,
    JiraYearWorklogIssue,
    JiraYearWorklogProgress,
    JiraYearWorklogResponse
  } from '$lib/services/jira';

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

  export let data: JiraYearWorklogResponse | null = null;
  // Issue con ore loggate gia' appiattite (subtask incluse): servono a riconoscere le sottotask.
  export let issues: JiraHistoryIssue[] = [];
  export let selectedProjectKeys: string[] = [];
  export let loading = false;
  export let error = '';
  export let progress: JiraYearWorklogProgress | null = null;

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

  function worklogIssueIsSubtask(issue: JiraHistoryIssue) {
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

  $: knownSubtaskKeys = new Set(issues.filter(worklogIssueIsSubtask).map((issue) => issue.key));
  $: userSubtaskGroups = groupSubtasksByUser(data, knownSubtaskKeys, selectedProjectKeys);
  $: userSubtasksTotalSeconds = userSubtaskGroups.reduce((total, user) => total + user.seconds, 0);
  $: selectedKeys = new Set(selectedProjectKeys);
  $: visibleProjects =
    selectedProjectKeys.length > 0
      ? (data?.projects || []).filter((project) => selectedKeys.has(project.project_key))
      : [];
  $: visibleSummary = {
    projectsCount: visibleProjects.length,
    issuesCount: visibleProjects.reduce((total, project) => total + project.issues_count, 0),
    worklogsCount: visibleProjects.reduce((total, project) => total + project.worklogs_count, 0),
    totalSeconds: visibleProjects.reduce((total, project) => total + project.total_seconds, 0)
  };
</script>

<div class="detail-bar">
  <section class="panel subtask-users" data-history-hover hidden>
    <div class="subtask-users-head">
      <div>
        <h3>Ore sottotask per utente</h3>
        <p>Ore effettive dei worklog del periodo selezionato, separate per autore e sottotask.</p>
      </div>
      {#if userSubtaskGroups.length > 0}
        <strong>{userSubtaskGroups.length} utenti · {fmtHours(userSubtasksTotalSeconds)}</strong>
      {/if}
    </div>

    {#if loading && !data}
      <div class="stream-progress" data-history-hover-exclude>
        <div>
          <span>Caricamento worklog del periodo...</span>
          {#if progress?.total}
            <strong>{progress.loaded}/{progress.total}</strong>
          {/if}
        </div>
        <progress max={Math.max(1, progress?.total || 1)} value={progress?.loaded || 0}></progress>
      </div>
    {:else if error}
      <p class="tree-state error">{error}</p>
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

  <section class="panel worklogs-tree" data-history-hover>
    <div class="tree-head">
      <h3>Worklog del periodo</h3>
    </div>
    <p class="tree-subtitle">
      Ore effettivamente loggate nel periodo selezionato, attribuite per data del singolo worklog
      (indipendentemente dall'anno di chiusura dell'issue).
    </p>

    {#if loading && !data}
      <p class="tree-state">
        Caricamento worklog del periodo...
        {#if progress?.total}
          {progress.loaded}/{progress.total}
        {/if}
      </p>
    {:else if error}
      <p class="tree-state error">{error}</p>
    {:else if selectedProjectKeys.length === 0}
      <p class="tree-state">Seleziona almeno un progetto completato per visualizzare i worklog annuali.</p>
    {:else if !data || data.projects_count === 0}
      <p class="tree-state">Nessun worklog trovato per il periodo selezionato.</p>
    {:else if visibleProjects.length === 0}
      <p class="tree-state">Nessun worklog trovato per i progetti selezionati nel periodo scelto.</p>
    {:else}
      <p class="tree-summary">
        Progetti: {visibleSummary.projectsCount} · Issue: {visibleSummary.issuesCount} · Worklog: {visibleSummary.worklogsCount} · Ore: {fmtHours(visibleSummary.totalSeconds)}
      </p>
      <div class="tree-projects">
        {#each visibleProjects as project (project.project_key)}
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
</div>

<style>
  /* Altezza imposta dal contenitore: le liste scorrono all'interno dei pannelli. */
  .detail-bar {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    height: 100%;
    min-width: 0;
    min-height: 0;
  }
  .panel {
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    min-height: 0;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.85rem 0.95rem;
  }
  .panel[hidden] {
    display: none;
  }

  .subtask-users {
    background: #fff;
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
    flex: 1 1 auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-content: start;
    gap: 0.65rem;
    min-height: 0;
    margin-top: 0.7rem;
    padding-right: 4px;
    overflow-y: auto;
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
    background: #c9ccf8;
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
    flex: 1 1 auto;
    align-content: start;
    gap: 0.65rem;
    min-height: 0;
    padding-right: 4px;
    overflow-y: auto;
  }
  .tree-project-card {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #f2d9ec;
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
    background: #f8fafc;
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
</style>
