<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';
  import {
    jiraSearch,
    jiraAddWorklog,
    type JiraWorklogCreatedEvent
  } from '$lib/services/jira';

  export let day: string | null = null;
  export let issueKey: string | null = null;
  export let projectCode: string | null = null;
  export let issueSummary: string | null = null;
  export let blocked = false;
  export let blockedReason = '';

  type JiraLoggableIssue = {
    key: string;
    fields?: {
      summary?: string;
      project?: { key?: string; name?: string };
      status?: { name?: string };
    };
  };

  const dispatch = createEventDispatcher<{
    created: JiraWorklogCreatedEvent;
    notify: { success: boolean; message: string };
  }>();

  let showWorklogComposer = false;
  let loadingLoggableIssues = false;
  let loggableIssuesLoaded = false;
  let loggableIssuesError = '';
  let loggableIssues: JiraLoggableIssue[] = [];
  let loggableSearch = '';
  let selectedIssueKey = '';
  let worklogValue = '';
  let worklogTime = '09:00';
  let worklogDate = '';
  let worklogComment = '';
  let creatingWorklog = false;
  let createWorklogError = '';
  let createWorklogSuccess = '';

  function todayIsoDate() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  function normalizeUpper(value: string | null | undefined) {
    return String(value || '').trim().toUpperCase();
  }

  function normalizeTrim(value: string | null | undefined) {
    return String(value || '').trim();
  }

  $: fixedIssueKey = normalizeTrim(issueKey);
  $: hintedProjectCode =
    normalizeUpper(projectCode) || (fixedIssueKey ? normalizeUpper(fixedIssueKey.split('-')[0] || '') : '');
  $: activeDate = normalizeTrim(worklogDate) || normalizeTrim(day) || todayIsoDate();
  $: if (fixedIssueKey && selectedIssueKey !== fixedIssueKey) {
    selectedIssueKey = fixedIssueKey;
  }

  if (!worklogDate) {
    worklogDate = todayIsoDate();
  }

  $: if (day && !showWorklogComposer) {
    worklogDate = day;
  }

  // Lock body scroll when modal is open — avoids layout shift conflicts
  $: if (typeof document !== 'undefined') {
    if (showWorklogComposer) {
      document.body.style.overflow = 'hidden';
      document.body.classList.add('jira-worklog-modal-open');
    } else {
      document.body.style.overflow = '';
      document.body.classList.remove('jira-worklog-modal-open');
    }
  }

  onDestroy(() => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
      document.body.classList.remove('jira-worklog-modal-open');
    }
  });

  // Portal: move modal to body to escape any parent stacking context / z-index conflicts
  function portalToBody(node: HTMLElement) {
    if (typeof document === 'undefined') return;
    const placeholder = document.createComment('portal-placeholder');
    node.parentNode?.insertBefore(placeholder, node);
    document.body.appendChild(node);

    return {
      destroy() {
        if (document.body.contains(node)) {
          document.body.removeChild(node);
        }
        if (placeholder.parentNode) {
          placeholder.parentNode.removeChild(placeholder);
        }
      }
    };
  }

  function issueProjectLabel(issue: JiraLoggableIssue) {
    const projectKey = issue.fields?.project?.key || '';
    const projectName = issue.fields?.project?.name || '';
    if (projectKey && projectName) return `${projectKey} - ${projectName}`;
    if (projectKey) return projectKey;
    if (projectName) return projectName;
    return '-';
  }

  function buildStartedValue(dateValue: string, timeValue: string) {
    const [year, month, dayPart] = dateValue.split('-').map((part) => Number(part));
    const [hour, minute] = (timeValue || '09:00').split(':').map((part) => Number(part));
    const local = new Date(year, (month || 1) - 1, dayPart || 1, hour || 0, minute || 0, 0, 0);

    const yyyy = local.getFullYear();
    const mm = String(local.getMonth() + 1).padStart(2, '0');
    const dd = String(local.getDate()).padStart(2, '0');
    const hh = String(local.getHours()).padStart(2, '0');
    const mi = String(local.getMinutes()).padStart(2, '0');
    const ss = String(local.getSeconds()).padStart(2, '0');

    const offsetMinutes = -local.getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? '+' : '-';
    const absMinutes = Math.abs(offsetMinutes);
    const offH = String(Math.floor(absMinutes / 60)).padStart(2, '0');
    const offM = String(absMinutes % 60).padStart(2, '0');

    return `${yyyy}-${mm}-${dd}T${hh}:${mi}:${ss}.000${sign}${offH}${offM}`;
  }

  function clearComposerMessages() {
    createWorklogError = '';
    createWorklogSuccess = '';
  }

  async function loadLoggableIssues(force = false) {
    if (blocked) {
      createWorklogError = blockedReason || 'Inserimento worklog bloccato.';
      return;
    }
    if (!activeDate) {
      createWorklogError = 'Data non disponibile.';
      return;
    }
    if (loadingLoggableIssues) return;

    clearComposerMessages();
    loggableIssuesError = '';
    showWorklogComposer = true;
    if (fixedIssueKey) {
      selectedIssueKey = fixedIssueKey;
      return;
    }

    if (loggableIssuesLoaded && !force) return;

    loadingLoggableIssues = true;
    try {
      const data = await jiraSearch({
        jql: 'created is not EMPTY ORDER BY updated DESC',
        fields: 'summary,project,status',
        // 0 delega al backend la paginazione completa tramite nextPageToken Jira.
        maxResults: 0
      });
      const issuesByKey = new Map<string, JiraLoggableIssue>();
      for (const issue of (data?.issues || []) as JiraLoggableIssue[]) {
        const key = normalizeTrim(issue?.key);
        if (key && !issuesByKey.has(normalizeUpper(key))) {
          issuesByKey.set(normalizeUpper(key), issue);
        }
      }
      loggableIssues = [...issuesByKey.values()];
      loggableIssuesLoaded = true;
      const preferredIssueKey = selectedIssueKey;
      if (
        preferredIssueKey &&
        loggableIssues.some((issue) => normalizeUpper(issue.key) === normalizeUpper(preferredIssueKey))
      ) {
        selectedIssueKey = preferredIssueKey;
      } else if (!selectedIssueKey && loggableIssues.length > 0) {
        selectedIssueKey = loggableIssues[0].key;
      }
    } catch (e: any) {
      loggableIssuesError = String(e?.message || e || 'Errore caricamento issue Jira');
    } finally {
      loadingLoggableIssues = false;
    }
  }

  function closeComposer() {
    showWorklogComposer = false;
    clearComposerMessages();
  }

  // Only close on backdrop click, never bubble up to parent hover handlers
  function handleBackdropPointerDown(e: PointerEvent) {
    e.stopPropagation();
  }

  function handleBackdropClick(e: MouseEvent) {
    e.stopPropagation();
    if (creatingWorklog || loadingLoggableIssues) return;
    closeComposer();
  }

  function stopAll(e: Event) {
    e.stopPropagation();
  }

  function pickIssue(key: string) {
    selectedIssueKey = key;
    clearComposerMessages();
  }

  async function createWorklog() {
    clearComposerMessages();
    if (blocked) {
      createWorklogError = blockedReason || 'Inserimento worklog bloccato.';
      return;
    }
    if (!activeDate) {
      createWorklogError = 'Data non disponibile.';
      return;
    }
    if (!selectedIssueKey) {
      createWorklogError = 'Seleziona un progetto/issue dalla lista.';
      return;
    }
    if (!worklogValue.trim()) {
      createWorklogError = 'Inserisci il valore worklog (es. 2h o 30m).';
      return;
    }

    creatingWorklog = true;
    try {
      const selectedIssue = loggableIssues.find(
        (issue) => normalizeUpper(issue.key) === normalizeUpper(selectedIssueKey)
      );
      const computedProjectCode =
        selectedIssue?.fields?.project?.key || hintedProjectCode || selectedIssueKey.split('-')[0] || '';
      const commentText = worklogComment.trim();
      const withProjectCode = computedProjectCode
        ? `[${computedProjectCode}]${commentText ? ` ${commentText}` : ''}`
        : commentText;
      const requestedTimeSpent = worklogValue.trim();
      const requestedStarted = buildStartedValue(activeDate, worklogTime || '09:00');

      const result = await jiraAddWorklog(selectedIssueKey, {
        timeSpent: requestedTimeSpent,
        started: requestedStarted,
        comment: withProjectCode
      });

      dispatch('created', {
        day: activeDate,
        activity: {
          issue_key: selectedIssueKey,
          issue_summary: selectedIssue?.fields?.summary || issueSummary || '',
          project_key: selectedIssue?.fields?.project?.key || computedProjectCode || undefined,
          project_name: selectedIssue?.fields?.project?.name || undefined,
          worklog_id: String(result?.id || `optimistic-${Date.now()}`),
          author: result?.author?.displayName,
          started: result?.started || requestedStarted,
          time_spent: result?.timeSpent || requestedTimeSpent,
          time_spent_seconds: result?.timeSpentSeconds,
          comment: withProjectCode
        }
      });

      createWorklogSuccess = `Worklog creato su ${selectedIssueKey} (${activeDate} ${worklogTime || '09:00'}).`;
      dispatch('notify', {
        success: true,
        message: `Worklog Jira inserito correttamente su ${selectedIssueKey}.`
      });
      worklogValue = '';
      worklogComment = '';
      closeComposer();
    } catch (e: any) {
      createWorklogError = String(e?.message || e || 'Errore creazione worklog');
      dispatch('notify', {
        success: false,
        message: createWorklogError
      });
    } finally {
      creatingWorklog = false;
    }
  }

  $: normalizedLoggableSearch = loggableSearch.trim().toLowerCase();
  $: filteredLoggableIssues = loggableIssues.filter((issue) => {
    if (!normalizedLoggableSearch) return true;
    const key = issue.key || '';
    const summary = issue.fields?.summary || '';
    const projectKey = issue.fields?.project?.key || '';
    const projectName = issue.fields?.project?.name || '';
    return (
      key.toLowerCase().includes(normalizedLoggableSearch) ||
      summary.toLowerCase().includes(normalizedLoggableSearch) ||
      projectKey.toLowerCase().includes(normalizedLoggableSearch) ||
      projectName.toLowerCase().includes(normalizedLoggableSearch)
    );
  });
</script>

<div class="jira-worklog">
  <!--
    FIX: un solo handler on:click con |stopPropagation inline.
    Rimuove il doppio on:click che causava race condition
    con i listener hover del componente padre.
  -->
  <button
    class="worklog-btn"
    type="button"
    on:click|stopPropagation={() => loadLoggableIssues(false)}
    on:mousedown|stopPropagation
    on:keydown|stopPropagation
    disabled={!activeDate || loadingLoggableIssues || blocked}
    title={blocked ? blockedReason : ''}
  >
    {loadingLoggableIssues ? 'Caricamento spazi...' : 'Aggiungi worklog Jira'}
  </button>

  {#if blocked && blockedReason}
    <p class="worklog-blocked">{blockedReason}</p>
  {/if}

  {#if showWorklogComposer}
    <!--
      FIX: overlay gestisce pointerdown + click separatamente.
      Il pointerdown blocca subito la propagazione verso la card padre
      (mouseleave/mouseenter), impedendo il loop apri-chiudi.
      Il composer interno blocca tutti gli eventi risalenti.
    -->
    <div
      class="worklog-overlay"
      use:portalToBody
      on:pointerdown={handleBackdropPointerDown}
      on:click={handleBackdropClick}
      on:mouseenter|stopPropagation
      on:mouseleave|stopPropagation
      on:mouseover|stopPropagation
      on:mouseout|stopPropagation
    >
      <div
        class="worklog-composer"
        role="dialog"
        aria-modal="true"
        on:click={stopAll}
        on:pointerdown={stopAll}
        on:mouseenter|stopPropagation
        on:mouseleave|stopPropagation
        on:mouseover|stopPropagation
        on:mouseout|stopPropagation
      >
        <div class="composer-head">
          <strong>Nuovo worklog</strong>
          <div class="composer-actions">
            {#if !fixedIssueKey}
              <button
                class="composer-ghost"
                type="button"
                on:click|stopPropagation={() => loadLoggableIssues(true)}
                disabled={loadingLoggableIssues || creatingWorklog}
              >
                Aggiorna lista
              </button>
            {/if}
            <button
              class="composer-ghost"
              type="button"
              on:click|stopPropagation={closeComposer}
              disabled={creatingWorklog}
            >
              Chiudi
            </button>
          </div>
        </div>

        {#if loggableIssuesError}
          <p class="state error">{loggableIssuesError}</p>
        {/if}

        <div class="composer-grid">
          <label>
            <span>Data</span>
            <input type="date" bind:value={worklogDate} />
          </label>
          <label>
            <span>Ora</span>
            <input type="time" bind:value={worklogTime} />
          </label>
          <label>
            <span>Valore worklog</span>
            <input type="text" bind:value={worklogValue} placeholder="es. 2h, 1h 30m, 45m" />
          </label>
        </div>

        {#if fixedIssueKey}
          <div class="composer-block">
            <span>Issue selezionata automaticamente</span>
            <div class="issue-live-list issue-context-list" aria-live="polite">
              <div class="issue-item selected issue-item-static">
                <small>{fixedIssueKey}</small>
                <strong>{hintedProjectCode || '-'}</strong>
                <span>{issueSummary || 'Issue selezionata dal contesto'}</span>
              </div>
            </div>
          </div>
        {:else}
          {#if hintedProjectCode}
            <p class="project-lock">Progetto suggerito: <code>{hintedProjectCode}</code></p>
          {/if}

          <label class="composer-block">
            <span>Cerca progetto/issue</span>
            <input
              type="text"
              bind:value={loggableSearch}
              placeholder="Filtra per codice progetto, issue key o summary..."
              disabled={loadingLoggableIssues}
            />
          </label>

          <label class="composer-block">
            <span>Progetto / issue selezionato: {selectedIssueKey || 'nessuno'}</span>
            <div class="issue-live-list" aria-live="polite">
              {#if filteredLoggableIssues.length === 0}
                <p class="issue-empty">Nessun risultato</p>
              {:else}
                {#each filteredLoggableIssues.slice(0, 20) as issue (issue.key)}
                  <button
                    type="button"
                    class="issue-item"
                    class:selected={normalizeUpper(selectedIssueKey) === normalizeUpper(issue.key)}
                    on:click|stopPropagation={() => pickIssue(issue.key)}
                  >
                    <small>{issue.key}</small>
                    <strong>{issueProjectLabel(issue)}</strong>
                    <span>{issue.fields?.summary || '-'}</span>
                  </button>
                {/each}
              {/if}
            </div>
          </label>
        {/if}

        <label class="composer-block">
          <span>Commento (opzionale)</span>
          <textarea
            rows="2"
            bind:value={worklogComment}
            placeholder="Commento worklog"
            disabled={creatingWorklog}
          ></textarea>
        </label>

        {#if createWorklogError}
          <p class="state error">{createWorklogError}</p>
        {/if}
        {#if createWorklogSuccess}
          <p class="state success">{createWorklogSuccess}</p>
        {/if}

        <div class="composer-submit">
          <button
            class="worklog-submit"
            type="button"
            on:click|stopPropagation={createWorklog}
            disabled={creatingWorklog || loadingLoggableIssues || !activeDate}
          >
            {creatingWorklog ? 'Invio in corso...' : 'Registra worklog'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .jira-worklog {
    width: 100%;
  }

  .worklog-btn {
    border: 1px solid #fdba74;
    background: #fff7ed;
    color: #c2410c;
    border-radius: 9px;
    padding: 0.35rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
    cursor: pointer;
  }

  .worklog-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .worklog-blocked {
    margin: 0.35rem 0 0;
    font-size: 0.68rem;
    color: #b91c1c;
    font-family: var(--font-mono);
  }

  .project-lock {
    margin: 0 0 0.4rem;
    font-size: 0.72rem;
    color: #475569;
    font-family: var(--font-mono);
  }

  .project-lock code {
    color: #c2410c;
  }

  /*
   * FIX: isolation: isolate crea un nuovo stacking context nel composer,
   * impedendo che z-index dei figli "sfuggano" verso la card padre.
   * will-change: transform forza la GPU a trattarlo come layer separato.
   */
  .worklog-overlay {
    position: fixed;
    inset: 0;
    z-index: 2147483000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(2px);
    isolation: isolate;
    /* Evita che il repaint dell'overlay tocchi il layer della card padre */
    will-change: opacity;
    contain: strict;
  }

  .worklog-composer {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #f8fafc;
    padding: 0.7rem;
    width: min(860px, calc(100vw - 2rem));
    max-height: calc(100vh - 3rem);
    overflow: auto;
    box-shadow: 0 20px 45px rgba(15, 23, 42, 0.28);
    /* Stacking context proprio: i figli non competono con la card */
    isolation: isolate;
    position: relative;
    z-index: 1;
  }

  .composer-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.55rem;
  }

  .composer-head strong {
    font-size: 0.8rem;
    color: #0f172a;
  }

  .composer-actions {
    display: flex;
    gap: 0.4rem;
  }

  .composer-ghost {
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #334155;
    border-radius: 8px;
    font-size: 0.68rem;
    padding: 0.25rem 0.45rem;
    cursor: pointer;
  }

  .composer-ghost:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .composer-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.45rem;
    margin-bottom: 0.45rem;
  }

  .composer-grid label,
  .composer-block {
    display: flex;
    flex-direction: column;
    gap: 0.28rem;
  }

  .composer-grid span,
  .composer-block span {
    font-size: 0.68rem;
    color: #475569;
    font-family: var(--font-mono);
  }

  .composer-grid input,
  .composer-block input,
  .composer-block textarea {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #fff;
    color: #0f172a;
    font-size: 0.76rem;
    padding: 0.38rem 0.5rem;
    outline: none;
  }

  .composer-grid input:focus,
  .composer-block input:focus,
  .composer-block textarea:focus {
    border-color: #fb923c;
    box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.15);
  }

  .composer-block {
    margin-bottom: 0.45rem;
  }

  .composer-submit {
    display: flex;
    justify-content: flex-end;
  }

  .issue-live-list {
    display: grid;
    gap: 0.35rem;
    max-height: 180px;
    overflow: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #fff;
    padding: 0.35rem;
  }

  .issue-context-list {
    max-height: none;
  }

  .issue-item {
    display: grid;
    gap: 0.12rem;
    text-align: left;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    background: #f8fafc;
    color: #0f172a;
    padding: 0.4rem 0.45rem;
    cursor: pointer;
  }

  .issue-item:hover {
    border-color: #fb923c;
    background: #fff7ed;
  }

  .issue-item.selected {
    border-color: #ea580c;
    background: #ffedd5;
  }

  .issue-item-static {
    cursor: default;
  }

  .issue-item strong {
    font-size: 0.72rem;
    line-height: 1.1;
  }

  .issue-item span {
    font-size: 0.68rem;
    color: #475569;
    font-family: var(--font-mono);
  }

  .issue-item small {
    font-size: 0.68rem;
    color: #1f2937;
    line-height: 1.25;
  }

  .issue-empty {
    margin: 0;
    font-size: 0.72rem;
    color: #64748b;
    padding: 0.35rem;
  }

  .worklog-submit {
    border: 1px solid #ea580c;
    background: #f97316;
    color: #fff;
    border-radius: 9px;
    font-size: 0.74rem;
    font-weight: 700;
    padding: 0.38rem 0.6rem;
    cursor: pointer;
  }

  .worklog-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .state {
    margin: 0;
    font-size: 0.86rem;
    color: #64748b;
  }

  .state.error {
    color: #b91c1c;
  }

  .state.success {
    color: #166534;
  }

  @media (max-width: 860px) {
    .worklog-overlay {
      align-items: flex-start;
      padding-top: 1.25rem;
    }

    .worklog-composer {
      width: calc(100vw - 1.25rem);
      max-height: calc(100vh - 2.5rem);
    }

    .composer-grid {
      grid-template-columns: 1fr;
    }

    .composer-actions {
      flex-wrap: wrap;
      justify-content: flex-end;
    }
  }

  /*
   * FIX: quando il modale è aperto, disabilita completamente hover e
   * transform sulla card padre tramite pointer-events: none sull'overlay
   * che copre tutto. Il pannello hover viene nascosto con !important
   * per evitare conflitti di z-index con l'overlay portato nel body.
   */
  :global(body.jira-worklog-modal-open) {
    /* Blocca tutti gli eventi pointer sugli elementi sotto l'overlay */
    pointer-events: none;
  }

  /* Il solo overlay (portato nel body) deve restare interagibile */
  :global(body.jira-worklog-modal-open .worklog-overlay) {
    pointer-events: auto;
  }

  :global(body.jira-worklog-modal-open .hover-comments .panel) {
    opacity: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
    transform: translateY(-4px) !important;
    transition: none !important;
  }

  :global(body.jira-worklog-modal-open .card),
  :global(body.jira-worklog-modal-open .card:hover),
  :global(body.jira-worklog-modal-open .card:focus-within) {
    z-index: 1 !important;
    transform: none !important;
    transition: none !important;
  }
</style>
