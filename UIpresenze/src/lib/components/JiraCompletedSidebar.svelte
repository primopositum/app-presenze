<script lang="ts">
  import { onMount } from 'svelte';
  import { jiraSearch } from '$lib/services/jira';

  type JiraIssue = {
    key: string;
    fields?: {
      summary?: string;
      status?: { name?: string };
      assignee?: { displayName?: string } | null;
      updated?: string;
      project?: { key?: string; name?: string };
    };
  };

  let loading = false;
  let error = '';
  let issues: JiraIssue[] = [];

  function fmtDate(iso?: string) {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: 'short',
      year: '2-digit'
    });
  }

  async function fetchCompleted() {
    loading = true;
    error = '';
    try {
      const data = await jiraSearch({
        jql: '(statusCategory = Done OR status in ("Completed","Completata")) ORDER BY updated DESC',
        fields: 'summary,status,assignee,updated,project',
        maxResults: 100
      });
      issues = (data?.issues || []) as JiraIssue[];
    } catch (e: any) {
      error = String(e?.message || e || 'Errore caricamento');
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchCompleted();
  });
</script>

<aside class="completed-sidebar">
  <div class="head">
    <h3>Attivita completate</h3>
    <button type="button" on:click={fetchCompleted} disabled={loading}>
      {loading ? '...' : 'Aggiorna'}
    </button>
  </div>

  {#if error}
    <div class="state error">{error}</div>
  {:else if loading && issues.length === 0}
    <div class="state">Caricamento...</div>
  {:else if issues.length === 0}
    <div class="state">Nessuna attivita trovata</div>
  {:else}
    <ul class="list">
      {#each issues as issue (issue.key)}
        <li class="row">
          <div class="top">
            <code>{issue.fields?.project?.name || '-'}</code>
            <span>{issue.fields?.status?.name || 'Done'}</span>
          </div>
          <p>{issue.fields?.summary || '-'}</p>
          <div class="meta">
            <span>{issue.key}</span>
            <span>{issue.fields?.assignee?.displayName || 'Unassigned'}</span>
            <span>{fmtDate(issue.fields?.updated)}</span>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</aside>

<style>
  .completed-sidebar {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 0.9rem;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.65rem;
  }

  .head h3 {
    font-size: 0.86rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
  }

  .head button {
    border: 1px solid #cbd5e1;
    background: #fff;
    border-radius: 8px;
    font-size: 0.72rem;
    padding: 4px 8px;
    cursor: pointer;
  }

  .head button:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  .state {
    font-size: 0.78rem;
    color: #64748b;
    padding: 0.4rem 0.1rem;
  }

  .state.error {
    color: #b91c1c;
  }

  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.55rem;
    max-height: 70vh;
    overflow: auto;
  }

  .row {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.55rem 0.6rem;
    background: #f8fafc;
  }

  .top {
    display: flex;
    justify-content: space-between;
    gap: 0.4rem;
    margin-bottom: 0.3rem;
  }

  .top code {
    font-size: 0.68rem;
    color: #334155;
    background: #fff;
    border: 1px solid #dbeafe;
    border-radius: 6px;
    padding: 1px 6px;
  }

  .top span {
    font-size: 0.66rem;
    color: #166534;
    background: #dcfce7;
    border: 1px solid #86efac;
    border-radius: 999px;
    padding: 1px 6px;
    white-space: nowrap;
  }

  .row p {
    margin: 0;
    font-size: 0.78rem;
    color: #0f172a;
    line-height: 1.35;
  }

  .meta {
    margin-top: 0.35rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    font-size: 0.64rem;
    color: #64748b;
    font-family: var(--font-mono);
  }
</style>
