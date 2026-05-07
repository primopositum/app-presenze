<script lang="ts">
  import { useJiraSearch } from '$lib/hooks/useJira';
  import JiraCompletedSidebar from '$lib/components/JiraCompletedSidebar.svelte';
  import { onMount } from 'svelte';

  const DOMAIN = (import.meta.env.PUBLIC_JIRA_DOMAIN ?? 'primopositum.atlassian.net').trim();

  let scopeType: 'project' | 'filter' = 'filter';
  let scopeValue = 'Progetti E3 attivi';

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
    };
  };

  let issues: JiraIssue[] = [];
  let activeStatus = 'all';
  let loading = false;
  let error = '';
  let loaded = false;
  let lastUpdate = '';

  // Searchbar state
  let searchQuery = '';
  let assigneeFilter = '';
  let maxResults = 50;

  const STATUS_META: Record<string, { accent: string; text: string }> = {
    'To Do': { accent: '#4f46e5', text: '#a5b4fc' },
    'In Progress': { accent: '#0891b2', text: '#67e8f9' },
    'In Review': { accent: '#d97706', text: '#fcd34d' },
    Done: { accent: '#16a34a', text: '#86efac' },
    Blocked: { accent: '#dc2626', text: '#fca5a5' }
  };

  const PRIORITY_ICON: Record<string, string> = {
    Highest: '^^',
    High: '^',
    Medium: 'o',
    Low: 'v',
    Lowest: 'vv'
  };

  const PRIORITY_COLOR: Record<string, string> = {
    Highest: '#ef4444',
    High: '#f97316',
    Medium: '#eab308',
    Low: '#22c55e',
    Lowest: '#6b7280'
  };

  $: statuses = [...new Set(issues.map((i) => i.fields?.status?.name).filter(Boolean) as string[])];

  $: statusCounts = issues.reduce<Record<string, number>>((acc, i) => {
    const s = i.fields?.status?.name;
    if (!s) return acc;
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  $: normalizedQuery = searchQuery.trim().toLowerCase();
  $: filtered = issues.filter((i) => {
    const statusName = i.fields?.status?.name || '';
    const assigneeName = i.fields?.assignee?.displayName || '';
    const summary = i.fields?.summary || '';
    const matchStatus = activeStatus === 'all' || statusName === activeStatus;
    const matchSearch =
      !normalizedQuery ||
      i.key.toLowerCase().includes(normalizedQuery) ||
      summary.toLowerCase().includes(normalizedQuery) ||
      assigneeName.toLowerCase().includes(normalizedQuery);
    return matchStatus && matchSearch;
  });

  function initials(name?: string) {
    if (!name) return '?';
    return name
      .split(' ')
      .map((w) => w[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();
  }

  function fmtDate(iso?: string) {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: '2-digit' });
  }

  function statusMeta(s?: string) {
    if (!s) return { accent: '#64748b', text: '#334155' };
    return STATUS_META[s] || { accent: '#64748b', text: '#334155' };
  }

  function openIssue(key: string) {
    window.open(`https://${DOMAIN}/browse/${key}`, '_blank', 'noopener,noreferrer');
  }

  async function fetchTasks() {
    error = '';
    loading = true;
    loaded = false;

    try {
      const data = await useJiraSearch({
        scopeType,
        scopeValue,
        assigneeFilter,
        maxResults
      });
      issues = (data?.issues || []) as JiraIssue[];
      lastUpdate = new Date().toLocaleTimeString('it-IT');
      loaded = true;
      if (activeStatus !== 'all' && !statuses.includes(activeStatus)) {
        activeStatus = 'all';
      }
    } catch (e: any) {
      const message = String(e?.message || e || '');
      error = message.includes('Failed to fetch')
        ? 'Errore CORS/rete: usa un proxy backend oppure testa in locale.'
        : message || 'Errore caricamento Jira';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchTasks();
  });

</script>

<main class="page-shell">
  <section class="board">
  <div class="header">
    <div class="header-left">
      <span class="logo-mark">J</span>
      <span class="logo-text">Jira Board</span>
      <code class="project-badge">{scopeType === 'project' ? `PRJ:${scopeValue}` : `FLT:${scopeValue}`}</code>
    </div>
    <div class="header-right">
      <button class="btn-primary" on:click={fetchTasks} disabled={loading}>
        {#if loading}<span class="spinner"></span>{/if}
        {loading ? 'Caricamento...' : 'Carica task'}
      </button>
    </div>
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <div class="searchbar">
    <select class="search-select" bind:value={scopeType}>
      <option value="project">Progetto</option>
      <option value="filter">Filtro Jira</option>
    </select>

    <div class="search-input-wrap">
      <span class="search-icon">#</span>
      <input
        class="search-input"
        bind:value={scopeValue}
        placeholder={scopeType === 'project' ? 'Project key (es. ENG)' : 'Filter ID o nome filtro'}
        type="text"
      />
    </div>

    <div class="search-input-wrap">
      <span class="search-icon">/</span>
      <input
        class="search-input"
        bind:value={searchQuery}
        placeholder="Cerca per titolo, chiave o assegnato..."
        type="text"
      />
      {#if searchQuery}
        <button class="clear-btn" on:click={() => (searchQuery = '')}>x</button>
      {/if}
    </div>

    <select class="search-select" bind:value={assigneeFilter}>
      <option value="">Tutti</option>
      <option value="currentUser()">Solo le mie</option>
    </select>

    <select class="search-select" bind:value={maxResults} on:change={loaded ? fetchTasks : undefined}>
      <option value={10}>10 risultati</option>
      <option value={20}>20 risultati</option>
      <option value={50}>50 risultati</option>
      <option value={100}>100 risultati</option>
    </select>
  </div>

  {#if loaded}
    <div class="board-meta">
      <div class="filters">
        <button class="filter" class:active={activeStatus === 'all'} on:click={() => (activeStatus = 'all')}>
          tutte <span class="count">{issues.length}</span>
        </button>
        {#each statuses as s}
          {@const meta = statusMeta(s)}
          <button
            class="filter"
            class:active={activeStatus === s}
            style={`--accent: ${meta.accent}; --accent-bg: ${meta.accent}22;`}
            on:click={() => (activeStatus = s)}
          >
            {s}
            <span class="count">{statusCounts[s] || 0}</span>
          </button>
        {/each}
      </div>
      <span class="result-info">
        {filtered.length} di {issues.length} issue
        {#if lastUpdate} | {lastUpdate}{/if}
      </span>
    </div>

    {#if filtered.length === 0}
      <div class="empty">Nessuna task trovata</div>
    {:else}
      <div class="cards">
        {#each filtered as issue (issue.key)}
          {@const f = issue.fields || {}}
          {@const status = f.status?.name || 'Unknown'}
          {@const priority = f.priority?.name || 'Medium'}
          {@const meta = statusMeta(status)}
          <article
            class="card"
            style={`--card-accent: ${meta.accent}; --card-text: ${meta.text};`}
            role="button"
            tabindex="0"
            on:click={() => openIssue(issue.key)}
            on:keydown={(e) => (e.key === 'Enter' || e.key === ' ' ? openIssue(issue.key) : undefined)}
          >
            <div class="card-top">
              <code class="issue-key">{f.project?.name || '-'}</code>
              <span class="priority" style={`color: ${PRIORITY_COLOR[priority] || '#888'};`} title={priority}>
                {PRIORITY_ICON[priority] || 'o'}
              </span>
            </div>
            <p class="summary">{f.summary || '-'}</p>
            <div class="card-bottom">
              <span class="status-pill">{status}</span>
              <div class="meta-right">
                {#if f.assignee?.displayName}
                  <div class="avatar" title={f.assignee.displayName}>
                    {initials(f.assignee.displayName)}
                  </div>
                {/if}
                <span class="date">{fmtDate(f.created)}</span>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  {:else if !loading}
    <div class="empty">Premi "Carica task" per iniziare</div>
  {/if}
  </section>

  <aside class="right-rail">
    <JiraCompletedSidebar />
  </aside>
</main>

<style>
  .page-shell {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.25rem 1rem 2.5rem;
    color: #1f2937;
  }

  .board {
    min-width: 0;
  }

  .right-rail {
    position: fixed;
    top: 9.5rem;
    left: calc(50% + 560px + 1rem);
    width: 340px;
    max-height: calc(100vh - 6rem);
    overflow: auto;
    z-index: 20;
  }

  @media (max-width: 1680px) {
    .right-rail {
      left: auto;
      right: 1rem;
      width: 320px;
    }
  }

  @media (max-width: 1400px) {
    .right-rail {
      position: static;
      width: auto;
      max-height: none;
      overflow: visible;
      margin-top: 0.8rem;
    }
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid #fed7aa;
    background: #fff;
    border-radius: 14px;
    padding: 0.85rem 1rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
  }
  .logo-mark {
    width: 30px;
    height: 30px;
    background: #f97316;
    color: #fff;
    font-family: var(--font-mono);
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    flex-shrink: 0;
    font-weight: 700;
  }
  .logo-text {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.02em;
    font-family: var(--font-infinity);
    text-transform: uppercase;
  }
  .project-badge {
    background: #fff7ed;
    color: #c2410c;
    border: 1px solid #fdba74;
    border-radius: 999px;
    font-family: var(--font-mono);
    font-size: 11px;
    padding: 2px 8px;
  }
  .header-right {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
  }

  .btn-primary {
    background: #f97316;
    color: #fff;
    border: 1px solid #ea580c;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 7px;
    transition: background 0.15s ease;
  }
  .btn-primary:hover {
    background: #ea580c;
  }
  .btn-primary:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .btn-ghost {
    background: #fff;
    color: #475569;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 12px;
    font-family: var(--font-mono);
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .btn-ghost:hover {
    border-color: #94a3b8;
    color: #1f2937;
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

  .spinner {
    width: 11px;
    height: 11px;
    border: 2px solid rgba(255, 255, 255, 0.45);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .searchbar {
    display: flex;
    gap: 8px;
    margin-bottom: 0.9rem;
    align-items: center;
    flex-wrap: wrap;
  }
  .search-input-wrap {
    flex: 1;
    min-width: 260px;
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-icon {
    position: absolute;
    left: 10px;
    color: #64748b;
    font-size: 14px;
    pointer-events: none;
    line-height: 1;
  }
  .search-input {
    width: 100%;
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    color: #1f2937;
    font-size: 13px;
    padding: 9px 30px 9px 30px;
    outline: none;
    transition: border-color 0.15s;
  }
  .search-input:focus {
    border-color: #fb923c;
    box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.18);
  }
  .search-input::placeholder {
    color: #94a3b8;
  }
  .clear-btn {
    position: absolute;
    right: 8px;
    background: none;
    border: none;
    color: #64748b;
    font-size: 12px;
    cursor: pointer;
    padding: 2px 4px;
    line-height: 1;
  }
  .clear-btn:hover {
    color: #1f2937;
  }

  .search-select {
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    color: #1f2937;
    font-size: 13px;
    padding: 9px 10px;
    outline: none;
    cursor: pointer;
    white-space: nowrap;
  }
  .search-select:focus {
    border-color: #fb923c;
    box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.18);
  }

  .board-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
    flex-wrap: wrap;
  }
  .filters {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .filter {
    background: #fff;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    color: #475569;
    font-size: 11px;
    font-family: var(--font-mono);
    padding: 4px 10px;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .filter:hover {
    color: #1f2937;
    border-color: #94a3b8;
  }
  .filter.active {
    border-color: var(--accent, #f97316);
    color: var(--accent, #c2410c);
    background: var(--accent-bg, #fff7ed);
  }
  .count {
    font-size: 10px;
    opacity: 0.75;
  }
  .result-info {
    font-size: 11px;
    color: #64748b;
    font-family: var(--font-mono);
    white-space: nowrap;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
  }

  .card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 3px solid var(--card-accent);
    border-radius: 12px;
    padding: 0.95rem;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  }

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .issue-key {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--card-text, #334155);
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 2px 6px;
    border-radius: 6px;
  }
  .priority {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
  }
  .summary {
    font-size: 13px;
    color: #0f172a;
    line-height: 1.45;
    margin-bottom: 12px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .card-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }
  .status-pill {
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--card-text, #334155);
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    padding: 2px 8px;
    white-space: nowrap;
  }
  .meta-right {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .avatar {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    color: #c2410c;
    font-size: 9px;
    font-weight: 700;
    font-family: var(--font-mono);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .date {
    font-size: 11px;
    color: #64748b;
    font-family: var(--font-mono);
  }

  .empty {
    text-align: center;
    padding: 2.8rem 1rem;
    color: #64748b;
    font-family: var(--font-mono);
    font-size: 13px;
    border: 1px dashed #cbd5e1;
    border-radius: 12px;
    background: #fff;
  }

  @media (max-width: 700px) {
    .search-input-wrap {
      min-width: 100%;
    }
    .search-select {
      flex: 1;
      min-width: 0;
    }
    .board-meta {
      flex-direction: column;
      align-items: flex-start;
    }
    .header {
      flex-wrap: wrap;
    }
  }
</style>
