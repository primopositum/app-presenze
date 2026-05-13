<script lang="ts">
  import {
    useJiraSearch,
    useJiraFiltersGet,
    useJiraFiltersPost,
    parseScopePreset,
    type JiraScopeType
  } from '$lib/hooks/useJira';
  import JiraScopeModal from '$lib/components/JiraScopeModal.svelte';
  import JiraCompletedSidebar from '$lib/components/JiraCompletedSidebar.svelte';
  import JiraWorklogCard from '$lib/components/JiraWorklogCard.svelte';
  import { onMount } from 'svelte';

  const DOMAIN = (import.meta.env.PUBLIC_JIRA_DOMAIN ?? 'primopositum.atlassian.net').trim();

  let scopeValue = '';
  let scopePresets: string[] = [];
  let scopeFiltersLoading = false;
  let scopeFiltersError = '';
  let showScopeModal = false;
  let scopeModalType: JiraScopeType = 'filter';
  let scopeModalValue = '';
  let selectedScopePreset: { raw: string; type: JiraScopeType; value: string } | null = null;

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

  let issues: JiraIssue[] = [];
  let activeStatus = 'all';
  let loading = false;
  let error = '';
  let loaded = false;
  let lastUpdate = '';
  let showBackToTop = false;

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

  const PRIORITY_THEME: Record<string, { accent: string; soft: string; ink: string; badgeText: string }> = {
     Highest: {
    accent: '#DC2626',     // red-600
    soft: '#FEE2E2',       // red-100
    ink: '#7F1D1D',        // red-900
    badgeText: '#FFFFFF'
  },

  High: {
    accent: '#EA580C',     // orange-600
    soft: '#FFEDD5',       // orange-100
    ink: '#9A3412',        // orange-900
    badgeText: '#FFFFFF'
  },

  Medium: {
    accent: '#CA8A04',     // yellow-600
    soft: '#FEF9C3',       // yellow-100
    ink: '#713F12',        // amber-900
    badgeText: '#111827'
  },

  Low: {
    accent: '#0891B2',     // cyan-600
    soft: '#CFFAFE',       // cyan-100
    ink: '#164E63',        // cyan-900
    badgeText: '#FFFFFF'
  },

  Lowest: {
    accent: '#4F46E5',     // indigo-600
    soft: '#E0E7FF',       // indigo-100
    ink: '#312E81',        // indigo-900
    badgeText: '#FFFFFF'
  }
  };

  function priorityTheme(name?: string) {
    if (!name) return PRIORITY_THEME.Medium;
    return PRIORITY_THEME[name] || PRIORITY_THEME.Medium;
  }

  $: statuses = [...new Set(issues.map((i) => i.fields?.status?.name).filter(Boolean) as string[])];

  $: statusCounts = issues.reduce<Record<string, number>>((acc, i) => {
    const s = i.fields?.status?.name;
    if (!s) return acc;
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  $: normalizedQuery = searchQuery.trim().toLowerCase();
  $: parsedScopePresets = scopePresets
    .map((raw) => parseScopePreset(raw))
    .filter((preset): preset is { raw: string; type: JiraScopeType; value: string } => !!preset);
  $: selectedScopePreset = parseScopePreset(scopeValue);
  $: filtered = issues.filter((i) => {
    const statusName = i.fields?.status?.name || '';
    const assigneeName = i.fields?.assignee?.displayName || '';
    const summary = i.fields?.summary || '';
    const projectName = i.fields?.project?.name || '';
    const projectKey = i.fields?.project?.key || '';
    const matchStatus = activeStatus === 'all' || statusName === activeStatus;
    const matchSearch =
      !normalizedQuery ||
      i.key.toLowerCase().includes(normalizedQuery) ||
      summary.toLowerCase().includes(normalizedQuery) ||
      assigneeName.toLowerCase().includes(normalizedQuery) ||
      projectName.toLowerCase().includes(normalizedQuery) ||
      projectKey.toLowerCase().includes(normalizedQuery);
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

  function fmtHours(seconds?: number | null) {
    const safeSeconds = Number(seconds ?? 0);
    if (!Number.isFinite(safeSeconds) || safeSeconds <= 0) return '0h';
    const hours = safeSeconds / 3600;
    const rounded = Math.round(hours * 10) / 10;
    const label = Number.isInteger(rounded)
      ? rounded.toFixed(0)
      : rounded.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `${label}h`;
  }

  function statusMeta(s?: string) {
    if (!s) return { accent: '#64748b', text: '#334155' };
    return STATUS_META[s] || { accent: '#64748b', text: '#334155' };
  }

  function openIssue(key: string) {
    window.open(`https://${DOMAIN}/browse/${key}`, '_blank', 'noopener,noreferrer');
  }

  function scopeTypeLabel(type: JiraScopeType) {
    if (type === 'project') return 'Progetto';
    if (type === 'labels') return 'Label';
    return 'Filtro';
  }

  function handleWindowScroll() {
    showBackToTop = window.scrollY > 260;
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function loadScopePresets(initial = false) {
    scopeFiltersError = '';
    scopeFiltersLoading = true;
    try {
      const data = await useJiraFiltersGet();
      scopePresets = Array.isArray(data?.filters) ? data.filters : [];
      if (initial && scopePresets.length > 0) {
        const first = parseScopePreset(scopePresets[0]);
        if (first) {
          scopeValue = first.raw;
        }
      }
    } catch (e) {
      scopeFiltersError = e instanceof Error ? e.message : 'Errore caricamento filtri Jira';
    } finally {
      scopeFiltersLoading = false;
    }
  }

  async function addScopePreset() {
    const value = String(scopeModalValue || '').trim();
    if (!value) return;
    scopeFiltersError = '';
    scopeFiltersLoading = true;
    try {
      const data = await useJiraFiltersPost(scopeModalType, value, true);
      scopePresets = Array.isArray(data?.filters) ? data.filters : [];
      const preset = scopePresets.find((item) => {
        const parsed = parseScopePreset(item);
        return parsed?.type === scopeModalType && parsed?.value === value;
      });
      scopeValue = preset || scopeValue;
      showScopeModal = false;
      scopeModalValue = '';
    } catch (e) {
      scopeFiltersError = e instanceof Error ? e.message : 'Errore salvataggio filtro Jira';
    } finally {
      scopeFiltersLoading = false;
    }
  }

  async function removeCurrentScopePreset() {
    const selected = parseScopePreset(scopeValue);
    if (!selected) return;
    scopeFiltersError = '';
    scopeFiltersLoading = true;
    try {
      const data = await useJiraFiltersPost(selected.type, selected.value, false);
      scopePresets = Array.isArray(data?.filters) ? data.filters : [];
      if (scopePresets.length === 0) {
        scopeValue = '';
      } else if (!scopePresets.includes(scopeValue)) {
        const first = parseScopePreset(scopePresets[0]);
        scopeValue = first ? first.raw : scopePresets[0];
      }
    } catch (e) {
      scopeFiltersError = e instanceof Error ? e.message : 'Errore rimozione filtro Jira';
    } finally {
      scopeFiltersLoading = false;
    }
  }

  function openScopeModal() {
    if (scopeFiltersLoading) return;
    scopeModalType = 'filter';
    scopeModalValue = '';
    showScopeModal = true;
  }

  function closeScopeModal() {
    if (scopeFiltersLoading) return;
    showScopeModal = false;
  }

  async function fetchTasks() {
    error = '';
    loading = true;
    loaded = false;

    try {
      const data = await useJiraSearch({
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

  onMount(async () => {
    await loadScopePresets(true);
    fetchTasks();
    handleWindowScroll();
  });

</script>

<svelte:window on:scroll={handleWindowScroll} />

<main class="page-shell">
  <section class="board">
  <div class="header">
    <div class="header-left">
      <span class="logo-mark">J</span>
      <span class="logo-text">Jira Board</span>
      <code class="project-badge">{scopeValue || 'SCOPE N/D'}</code>
    </div>
    <div class="header-right">
      <button class="btn-primary" on:click={fetchTasks} disabled={loading}>
        {#if loading}<span class="spinner"></span>{/if}
        {loading ? 'Caricamento...' : 'Scarica task'}
      </button>
    </div>
  </div>

  {#if error}
    <div class="error-bar">{error}</div>
  {/if}

  <div class="searchbar">
    <div class="scope-value-wrap">
      <div class="search-input-wrap">
        <span class="search-icon">#</span>
        <select class="search-input scope-dropdown" bind:value={scopeValue}>
          {#if parsedScopePresets.length === 0}
            <option value="">Nessun filtro disponibile</option>
          {:else}
            {#each parsedScopePresets as preset}
              <option value={preset.raw}>{scopeTypeLabel(preset.type)}: {preset.value}</option>
            {/each}
          {/if}
        </select>
      </div>
      <button
        class="scope-add-btn"
        on:click={openScopeModal}
        disabled={scopeFiltersLoading}
        title="Aggiungi filtro/progetto"
      >
        +
      </button>
      <button
        class="scope-remove-btn"
        on:click={removeCurrentScopePreset}
        disabled={scopeFiltersLoading || !selectedScopePreset}
        title="Rimuovi filtro corrente"
      >
        X
      </button>
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
  {#if scopeFiltersError}
    <div class="scope-error">{scopeFiltersError}</div>
  {/if}

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
          {@const totalSeconds = taskTotalSeconds(f)}
          {@const meta = statusMeta(status)}
          {@const pmeta = priorityTheme(priority)}
          <article
            class="card"
            style={`--card-text: ${meta.text}; --priority-accent: ${pmeta.accent}; --priority-soft: ${pmeta.soft}; --priority-ink: ${pmeta.ink}; --priority-badge-text: ${pmeta.badgeText};`}
            role="button"
            tabindex="0"
            on:click={() => openIssue(issue.key)}
            on:keydown={(e) => (e.key === 'Enter' || e.key === ' ' ? openIssue(issue.key) : undefined)}
          >
            <div class="card-top">
              <code class="issue-key">{f.project?.name || '-'}</code>
              <span class="priority" title={priority}>
                {PRIORITY_ICON[priority] || 'o'} {priority}
              </span>
            </div>
            <p class="summary">{f.summary || '-'}</p>
            <div class="worklog-slot">
              <JiraWorklogCard
                issueKey={issue.key}
                projectCode={f.project?.key || issue.key.split('-')[0] || ''}
                issueSummary={f.summary || ''}
              />
            </div>
            <div class="card-bottom">
              <span class="status-pill">{status}</span>
              <div class="meta-right">
                <span class="task-hours" title={`Tempo totale task: ${Math.max(totalSeconds, 0)}s`}>
                  Ore {fmtHours(totalSeconds)}
                </span>
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


</main>

<JiraScopeModal
  open={showScopeModal}
  loading={scopeFiltersLoading}
  defaultType={scopeModalType}
  defaultValue={scopeModalValue}
  on:close={closeScopeModal}
  on:submit={(e) => {
    scopeModalType = e.detail.type;
    scopeModalValue = e.detail.value;
    addScopePreset();
  }}
/>

<button
  class="mobile-back-top"
  class:visible={showBackToTop}
  type="button"
  on:click={scrollToTop}
  aria-label="Torna in cima"
  title="Torna in cima"
>
  ˄
</button>

<style>
  .page-shell {
    max-width: 100%;
    margin: 0 auto;
    padding: 1.25rem 0 2.5rem;
    color: #1f2937;
  }

  .board {
    min-width: 0;
    width: 100%;
    max-width: 1456px;
    margin: 0 auto;
  }
  .right-rail {
    position: fixed;
    top: 9.5rem;
    left: auto;
    right: 1rem;
    width: 320px;
    max-height: calc(100vh - 6rem);
    overflow: auto;
    z-index: 20;
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
  .scope-dropdown {
    appearance: none;
    cursor: pointer;
    padding-right: 30px;
  }
  .scope-value-wrap {
    flex: 1.2;
    min-width: 300px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .scope-add-btn {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #0f172a;
    font-size: 18px;
    line-height: 1;
    font-weight: 700;
    cursor: pointer;
  }
  .scope-add-btn:hover {
    border-color: #94a3b8;
    background: #f8fafc;
  }
  .scope-remove-btn {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    border: 1px solid #fecaca;
    background: #fff;
    color: #b91c1c;
    font-size: 14px;
    line-height: 1;
    font-weight: 700;
    cursor: pointer;
  }
  .scope-remove-btn:hover {
    border-color: #fca5a5;
    background: #fef2f2;
  }
  .scope-add-btn:disabled,
  .scope-remove-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .scope-error {
    margin-top: -2px;
    margin-bottom: 8px;
    font-size: 11px;
    color: #b91c1c;
    font-family: var(--font-mono);
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
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid var(--priority-accent, #d1a900);
    border-radius: 12px;
    padding: 1.1rem;
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
    background: var(--priority-soft, #fbf4d7);
    border: 1px solid var(--priority-accent, #d1a900);
    border-radius: 9px;
    padding: 6px 8px;
  }
  .issue-key {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--priority-ink, #334155);
    background: #ffffff;
    border: 1px solid var(--priority-accent, #d1a900);
    padding: 2px 6px;
    border-radius: 6px;
  }
  .priority {
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--priority-badge-text, #ffffff);
    background: var(--priority-accent, #d1a900);
    border: 1px solid var(--priority-accent, #d1a900);
    padding: 2px 8px;
    border-radius: 999px;
    letter-spacing: 0.02em;
    white-space: nowrap;
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
  .worklog-slot {
    margin: 0 0 0.55rem;
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
  .task-hours {
    font-size: 10px;
    font-family: var(--font-mono);
    color: #0f172a;
    background: #fff7ed;
    border: 1px solid #fdba74;
    border-radius: 999px;
    padding: 2px 8px;
    white-space: nowrap;
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

  .mobile-back-top {
    display: none;
  }

  @media (max-width: 1024px) {
    .page-shell {
      padding-top: 1rem;
    }
    .header {
      flex-wrap: wrap;
    }
    .header-right {
      width: 100%;
      justify-content: flex-end;
    }
    .search-input-wrap {
      min-width: 220px;
    }
    .scope-value-wrap {
      min-width: 260px;
    }
    .cards {
      grid-template-columns: 1fr;
    }
    .result-info {
      white-space: normal;
    }
  }

  @media (max-width: 700px) {
    .page-shell {
      padding-top: 0.75rem;
    }
    .header {
      gap: 0.6rem;
      padding: 0.75rem;
    }
    .header-left {
      width: 100%;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .logo-text {
      font-size: 0.92rem;
    }
    .project-badge {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .header-right {
      width: 100%;
      justify-content: stretch;
    }
    .btn-primary {
      width: 100%;
      justify-content: center;
    }
    .searchbar {
      gap: 0.55rem;
    }
    .cards {
      grid-template-columns: 1fr;
    }
    .scope-value-wrap {
      min-width: 100%;
      flex: 1;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .scope-add-btn,
    .scope-remove-btn {
      width: 38px;
      height: 38px;
    }
    .search-input-wrap {
      min-width: 100%;
    }
    .search-select {
      width: 100%;
      min-width: 100%;
    }
    .board-meta {
      flex-direction: column;
      align-items: flex-start;
    }
    .filters {
      width: 100%;
    }
    .filter {
      padding: 6px 10px;
    }
    .card {
      padding: 0.9rem;
    }
    .card-top {
      flex-wrap: wrap;
      row-gap: 0.35rem;
    }
    .issue-key {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .card-bottom {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.45rem;
    }
    .meta-right {
      width: 100%;
      justify-content: space-between;
    }
    .task-hours,
    .status-pill,
    .date {
      font-size: 10px;
    }
    .mobile-back-top {
      display: flex;
      position: fixed;
      right: 0.85rem;
      bottom: 0.95rem;
      width: 34px;
      height: 34px;
      align-items: center;
      justify-content: center;
      border: 1px solid #fdba74;
      border-radius: 999px;
      background: #fff7ed;
      color: #c2410c;
      font-size: 16px;
      font-weight: 800;
      box-shadow: 0 8px 22px rgba(194, 65, 12, 0.18);
      opacity: 0;
      transform: translateY(8px);
      pointer-events: none;
      transition: opacity 0.18s ease, transform 0.18s ease;
      z-index: 50;
    }
    .mobile-back-top.visible {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }
  }

  @media (max-width: 480px) {
    .page-shell {
      padding-top: 0.65rem;
    }
    .logo-mark {
      width: 28px;
      height: 28px;
      font-size: 13px;
    }
    .logo-text {
      font-size: 0.84rem;
    }
    .project-badge {
      font-size: 10px;
    }
    .search-input,
    .search-select {
      font-size: 12px;
      padding-top: 8px;
      padding-bottom: 8px;
    }
    .summary {
      font-size: 12px;
    }
    .card {
      border-radius: 10px;
    }
  }
</style>
