<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { jiraSearch } from '$lib/services/jira';
  import JiraCard from '$lib/components/Jira/JiraCard.svelte';

  type JiraIssue = {
    key: string;
    fields?: {
      summary?: string;
      status?: { name?: string };
      priority?: { name?: string };
      assignee?: { displayName?: string } | null;
      created?: string;
      updated?: string;
      issuetype?: { name?: string };
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

  let loading = false;
  let loaded = false;
  let error = '';
  let issues: JiraIssue[] = [];
  let lastUpdate = '';
  let isOpen = false;
  const PRIORITY_WEIGHT: Record<string, number> = {
    Highest: 5,
    High: 4,
    Medium: 3,
    Low: 2,
    Lowest: 1
  };

  function compareByPriority(a: JiraIssue, b: JiraIssue) {
    const aPriority = String(a.fields?.priority?.name || '');
    const bPriority = String(b.fields?.priority?.name || '');
    const aWeight = PRIORITY_WEIGHT[aPriority] ?? 0;
    const bWeight = PRIORITY_WEIGHT[bPriority] ?? 0;
    if (aWeight !== bWeight) return bWeight - aWeight;
    const aTs = new Date(a.fields?.created || 0).getTime();
    const bTs = new Date(b.fields?.created || 0).getTime();
    return bTs - aTs;
  }

  async function fetchPersonalTasks() {
    loading = true;
    loaded = false;
    error = '';
    try {
      const data = await jiraSearch({
        jql: 'assignee = currentUser() AND statusCategory != Done ORDER BY priority DESC, created DESC',
        fields:
          'summary,status,priority,assignee,created,updated,issuetype,project,timetracking,timespent,aggregatetimespent,timeestimate,aggregatetimeestimate,timeoriginalestimate,aggregatetimeoriginalestimate',
        maxResults: 20,
        startAt: 0
      });
      issues = ((data?.issues || []) as JiraIssue[]).filter((issue) => {
        const status = String(issue.fields?.status?.name || '').toLowerCase();
        return status !== 'done' && status !== 'closed' && status !== 'resolved';
      });
      lastUpdate = new Date().toLocaleTimeString('it-IT');
      loaded = true;
    } catch (e: any) {
      error = String(e?.message || e || 'Errore caricamento task personali Jira');
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchPersonalTasks();
  });

  onDestroy(() => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
    }
  });

  $: sortedIssues = [...issues].sort(compareByPriority);
  $: if (typeof document !== 'undefined') {
    const isMobile = window.matchMedia('(max-width: 900px)').matches;
    document.body.style.overflow = isOpen && isMobile ? 'hidden' : '';
  }
</script>

<div class="personal-task-shell" class:open={isOpen}>
  <button
    class="toggle-handle"
    type="button"
    on:click={() => (isOpen = !isOpen)}
    aria-expanded={isOpen}
    aria-controls="jira-personal-sidebar"
    aria-label={isOpen ? 'Chiudi task personali Jira' : 'Apri task personali Jira'}
  >
    <img class="toggle-icon" src="/JrightUp.png" alt="" aria-hidden="true" />
  </button>

  <button
    class="mobile-overlay"
    class:visible={isOpen}
    type="button"
    aria-label="Chiudi pannello task personali"
    on:click={() => (isOpen = false)}
  ></button>

  <aside id="jira-personal-sidebar" class="personal-jira" class:open={isOpen}>
    <div class="head">
      <h2>Le Tue Task Jira</h2>
      <div class="head-actions">
        <button class="refresh" type="button" on:click={fetchPersonalTasks} disabled={loading}>
          {loading ? 'Caricamento...' : 'Aggiorna'}
        </button>
      </div>
    </div>

    {#if error}
      <div class="error-bar">{error}</div>
    {/if}

    {#if loaded}
      <div class="meta">
        <span>{issues.length} issue assegnate</span>
        {#if lastUpdate}<span>Aggiornato alle {lastUpdate}</span>{/if}
      </div>
      {#if issues.length === 0}
        <div class="empty">Nessuna task assegnata.</div>
      {:else}
        <div class="cards">
          {#each sortedIssues as issue (issue.key)}
            <div class="card-item">
              <JiraCard {issue} />
            </div>
          {/each}
        </div>
      {/if}
    {:else if !loading}
      <div class="empty">Carica le task personali per iniziare.</div>
    {/if}
  </aside>
</div>

<style>
  .personal-task-shell {
    --sidebar-width: min(460px, calc(100vw - 2.25rem));
    position: fixed;
    inset: 0;
    z-index: 88;
    pointer-events: none;
  }

  .toggle-handle {
    position: fixed;
    top: 50%;
    left: 0.55rem;
    transform: translateY(-50%);
    pointer-events: auto;
    border: none;
    background: transparent;
    appearance: none;
    -webkit-appearance: none;
    color: #9a3412;
    border-radius: 10px;
    padding: 0.45rem 0.5rem;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: none;
    transition: left 0.22s ease, background 0.15s ease, color 0.15s ease;
    z-index: 92;
  }

  .toggle-handle:hover {
    background: transparent;
    color: #7c2d12;
  }

  .toggle-text {
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .toggle-icon {
    width: 67px;
    height: 67px;
    display: block;
    object-fit: contain;
    transition: transform 0.2s ease;
  }

  .personal-task-shell.open .toggle-handle {
    left: var(--sidebar-width);
    transform: translate(-50%, -50%);
  }

  .personal-task-shell.open .toggle-icon {
    transform: rotate(180deg);
  }

  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.38);
    border: 0;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s ease;
    z-index: 89;
  }

  .personal-jira {
    position: fixed;
    top: 50%;
    left: 0;
    width: var(--sidebar-width);
    max-height: 82vh;
    transform: translate(-100%, -50%);
    pointer-events: auto;
    border: 1px solid #fed7aa;
    border-radius: 14px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    background: #fff;
    padding: 0.9rem;
    box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
    transition: transform 0.22s ease;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    z-index: 91;
  }

  .personal-jira.open {
    transform: translate(0, -50%);
  }

  .personal-jira {
    scrollbar-gutter: stable;
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    margin-bottom: 0.8rem;
  }

  .head h2 {
    margin: 0;
    font-size: 1rem;
    color: #0f172a;
    font-family: var(--font-infinity);
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .head-actions {
    display: flex;
    align-items: center;
    gap: 0.55rem;
  }

  .sort-label {
    display: inline-flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: #475569;
  }

  .refresh {
    background: #f97316;
    color: #fff;
    border: 1px solid #ea580c;
    border-radius: 9px;
    padding: 0.35rem 0.6rem;
    font-size: 0.74rem;
    font-weight: 700;
    cursor: pointer;
  }

  .refresh:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .meta {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.7rem;
    font-size: 0.72rem;
    color: #64748b;
    font-family: var(--font-mono);
    flex-wrap: wrap;
  }

  .cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    max-height: calc(82vh - 9.2rem);
    overflow-y: auto;
    padding-right: 0.25rem;
  }

  .error-bar {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    font-size: 12px;
    font-family: var(--font-mono);
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 0.9rem;
  }

  .empty {
    text-align: center;
    padding: 1.2rem 0.75rem;
    color: #64748b;
    font-family: var(--font-mono);
    font-size: 13px;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    background: #fff;
  }

  @media (max-width: 900px) {
    .personal-task-shell {
      --sidebar-width: min(420px, calc(100vw - 1.75rem));
    }

    .mobile-overlay.visible {
      opacity: 1;
      pointer-events: auto;
    }

    .personal-task-shell.open .toggle-handle {
      left: calc(var(--sidebar-width) + 0.35rem);
      transform: translate(0, -50%);
    }

    .head {
      flex-direction: column;
      align-items: flex-start;
    }

    .head-actions {
      width: 100%;
      justify-content: space-between;
    }

    .sort-label {
      flex: 1 1 auto;
    }
  }

  @media (max-width: 640px) {
    .personal-jira {
      max-height: 86vh;
      border-radius: 12px;
      border-top-left-radius: 0;
      border-bottom-left-radius: 0;
    }

    .cards {
      max-height: calc(86vh - 9.2rem);
    }

    .toggle-handle {
      left: 0.4rem;
      padding: 0.4rem 0.46rem;
    }

    .toggle-text {
      display: none;
    }
  }
</style>
