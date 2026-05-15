<script lang="ts">
  import { jiraTimesheet, jiraDeleteWorklog, jiraAddWorklog, jiraUpdateWorklog, type JiraTimesheetActivity } from '$lib/services/jira';
  import JiraWorklogCard from '$lib/components/Jira/JiraWorklogCard.svelte';
  import ConfirmCard from '$lib/components/ConfirmCard.svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faTrash } from '@fortawesome/free-solid-svg-icons';

  export let day: string | null = null;
  export let ore: number | string | null = null;

  let loading = false;
  let error = '';
  let activities: JiraTimesheetActivity[] = [];
  let lastLoadedDay = '';
  let deletingWorklogId = '';
  let worklogActionError = '';
  let completeActionError = '';
  let completeActionSuccess = '';
  let completing = false;
  let deleteConfirmTarget: { issueKey: string; worklogId: string } | null = null;
  const COMPLETE_ISSUE_KEY = 'AM-1';

  function toNumber(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  function parseTimeToSeconds(timeStr?: string): number {
    if (!timeStr) return 0;
    const text = timeStr.toLowerCase();
    const hours = text.match(/(\d+)\s*h/);
    const minutes = text.match(/(\d+)\s*m/);
    const seconds = text.match(/(\d+)\s*s/);

    let total = 0;
    if (hours) total += Number(hours[1]) * 3600;
    if (minutes) total += Number(minutes[1]) * 60;
    if (seconds) total += Number(seconds[1]);
    return total;
  }

  function activitySeconds(item: JiraTimesheetActivity) {
    const fromField = Number(item.time_spent_seconds);
    if (Number.isFinite(fromField) && fromField > 0) return fromField;
    return parseTimeToSeconds(item.time_spent);
  }

  function formatDateTime(value?: string) {
    if (!value) return '';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value;
    return dt.toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function formatHours(seconds: number) {
    return (seconds / 3600).toFixed(2);
  }

  async function load() {
    if (!day || day === lastLoadedDay) return;
    loading = true;
    error = '';
    try {
      const data = await jiraTimesheet(day);
      activities = data.activities || [];
      lastLoadedDay = day;
    } catch (e: any) {
      error = String(e?.message || e || 'Errore caricamento attivita');
    } finally {
      loading = false;
    }
  }

  $: if (day && day !== lastLoadedDay) {
    load();
  }

  $: if (!day) {
    activities = [];
    lastLoadedDay = '';
    error = '';
  }

  async function refreshAfterWorklogCreate() {
    lastLoadedDay = '';
    await load();
  }

  function secondsToJiraTimeSpent(totalSeconds: number) {
    const safe = Math.max(0, Math.round(totalSeconds));
    if (safe <= 0) return '';
    const h = Math.floor(safe / 3600);
    const m = Math.floor((safe % 3600) / 60);
    const s = safe % 60;
    const chunks: string[] = [];
    if (h > 0) chunks.push(`${h}h`);
    if (m > 0) chunks.push(`${m}m`);
    if (s > 0) chunks.push(`${s}s`);
    return chunks.join(' ');
  }

  function buildStartedForDay(dayValue: string, baseStarted?: string) {
    if (baseStarted) return baseStarted;
    const [year, month, dayPart] = dayValue.split('-').map((part) => Number(part));
    const local = new Date(year, (month || 1) - 1, dayPart || 1, 9, 0, 0, 0);
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

  async function completeWithAm1() {
    completeActionError = '';
    completeActionSuccess = '';
    if (!day) {
      completeActionError = 'Seleziona un giorno prima di completare.';
      return;
    }
    if (completing) return;
    if (expectedSeconds <= 0) {
      completeActionError = 'Target giornaliero non valido.';
      return;
    }

    const am1Entry = activities.find((item) => (item.issue_key || '').toUpperCase() === COMPLETE_ISSUE_KEY);
    const am1CurrentSeconds = am1Entry ? activitySeconds(am1Entry) : 0;
    const coveredWithoutAm1 = Math.max(0, totalActivitySeconds - am1CurrentSeconds);
    const missingSeconds = expectedSeconds - coveredWithoutAm1;
    if (missingSeconds <= 0) {
      completeActionError = 'Copertura già completa: nessuna ora da aggiungere su AM-1.';
      return;
    }

    const timeSpent = secondsToJiraTimeSpent(missingSeconds);
    if (!timeSpent) {
      completeActionError = 'Impossibile calcolare il timeSpent da registrare.';
      return;
    }

    completing = true;
    try {
      const started = buildStartedForDay(day, am1Entry?.started);
      if (am1Entry?.worklog_id) {
        await jiraUpdateWorklog(COMPLETE_ISSUE_KEY, am1Entry.worklog_id, { timeSpent, started });
      } else {
        await jiraAddWorklog(COMPLETE_ISSUE_KEY, { timeSpent, started });
      }
      await refreshAfterWorklogCreate();
      completeActionSuccess = `Completamento registrato su ${COMPLETE_ISSUE_KEY}: ${timeSpent}.`;
    } catch (e: any) {
      completeActionError = String(e?.message || e || `Errore completamento su ${COMPLETE_ISSUE_KEY}`);
    } finally {
      completing = false;
    }
  }

  async function removeWorklog(issueKey: string, worklogId: string) {
    if (!issueKey || !worklogId || deletingWorklogId) return;
    deletingWorklogId = worklogId;
    worklogActionError = '';
    try {
      await jiraDeleteWorklog(issueKey, worklogId);
      await refreshAfterWorklogCreate();
    } catch (e: any) {
      worklogActionError = String(e?.message || e || 'Errore rimozione worklog');
    } finally {
      deletingWorklogId = '';
    }
  }

  function askDeleteWorklog(issueKey: string, worklogId: string) {
    if (!issueKey || !worklogId || deletingWorklogId) return;
    deleteConfirmTarget = { issueKey, worklogId };
  }

  function closeDeleteConfirm() {
    if (deletingWorklogId) return;
    deleteConfirmTarget = null;
  }

  async function confirmDeleteWorklog() {
    if (!deleteConfirmTarget) return;
    const target = deleteConfirmTarget;
    deleteConfirmTarget = null;
    await removeWorklog(target.issueKey, target.worklogId);
  }

  let expectedHours = 0;
  let expectedSeconds = 0;
  let totalActivitySeconds = 0;
  let denominatorSeconds = 0;
  let progressPercent = 0;
  let rawCoveragePercent = 0;
  let worklogCreationBlocked = false;
  let worklogBlockReason = '';
  let segments: Array<{
    key: string;
    worklogId: string;
    widthPct: number;
    color: string;
    issueKey: string;
    summary: string;
    timeSpent: string;
    project: string;
    author: string;
    started: string;
    comment: string;
  }> = [];

  $: expectedHours = Math.max(0, toNumber(ore));
  $: expectedSeconds = expectedHours * 3600;
  $: totalActivitySeconds = activities.reduce((acc, item) => acc + activitySeconds(item), 0);
  $: denominatorSeconds = expectedSeconds > 0 ? expectedSeconds : totalActivitySeconds;
  $: rawCoveragePercent = denominatorSeconds > 0 ? (totalActivitySeconds / denominatorSeconds) * 100 : 0;
  $: progressPercent = denominatorSeconds > 0 ? Math.min(100, (totalActivitySeconds / denominatorSeconds) * 100) : 0;
  $: worklogCreationBlocked = expectedSeconds > 0 && rawCoveragePercent >= 100;
  $: worklogBlockReason = worklogCreationBlocked
    ? `Copertura Jira gia al ${rawCoveragePercent.toFixed(1)}%: inserimento bloccato.`
    : '';
  $: completeButtonDisabled = !day || loading || expectedSeconds <= 0 || completing;
  $: segments = activities.map((item, idx) => {
    const seconds = activitySeconds(item);
    const widthPct = denominatorSeconds > 0 ? (seconds / denominatorSeconds) * 100 : 0;
    return {
      key: item.worklog_id ?? `${item.issue_key}-${item.started}-${idx}`,
      worklogId: String(item.worklog_id || ''),
      widthPct: Math.max(0, widthPct),
      color: `hsl(${(idx * 47) % 360} 72% 52%)`,
      issueKey: item.issue_key || '-',
      summary: item.issue_summary || '-',
      timeSpent: item.time_spent || `${formatHours(seconds)}h`,
      project: item.project_key || item.project_name || '-',
      author: item.author || '-',
      started: formatDateTime(item.started),
      comment: item.comment || ''
    };
  });

</script>

<section class="useractivity">
  <div class="head">
    <div class="title-group">
      <h3>Attivita utente</h3>
      {#if day}<span class="badge-day">{day}</span>{/if}
    </div>
    <span class="target-hours">Target: {expectedHours.toFixed(2)}h</span>
  </div>

  <div class="worklog-actions-row">
    <div class="worklog-card-col">
      <JiraWorklogCard
        {day}
        blocked={worklogCreationBlocked}
        blockedReason={worklogBlockReason}
        on:created={refreshAfterWorklogCreate}
      />
    </div>
    {#if !worklogBlockReason}
      <button
        type="button"
        class="complete-btn"
        on:click={completeWithAm1}
        disabled={completeButtonDisabled}
        title="Completa su AM-1 fino al target giornaliero"
      >
        {completing ? 'Completamento...' : 'Completa'}
      </button>
    {/if}
  </div>
  {#if completeActionError}
    <p class="state error">{completeActionError}</p>
  {/if}
  {#if completeActionSuccess}
    <p class="state success">{completeActionSuccess}</p>
  {/if}

  {#if !day}
    <p class="state">Seleziona un giorno nel calendario per vedere le attivita Jira.</p>
  {:else if loading}
    <p class="state">Caricamento attivita...</p>
  {:else if error}
    <p class="state error">{error}</p>
  {:else if activities.length === 0}
    <p class="state">Nessuna attivita trovata per il giorno selezionato.</p>
  {:else}
    {#if worklogActionError}
      <p class="state error">{worklogActionError}</p>
    {/if}
    <div class="progress-wrap">
      <div class="progress-meta">
        <span>Ore Jira: {formatHours(totalActivitySeconds)}h</span>
        <span>Copertura: {rawCoveragePercent.toFixed(1)}%</span>
      </div>

      <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={progressPercent}>
        {#each segments as segment (segment.key)}
          <div class="progress-segment" style={`width:${segment.widthPct}%;--segment-color:${segment.color};`} tabindex="0">
            <span class="segment-label">{segment.summary}</span>
            <div class="segment-tooltip">
              <div class="tooltip-head">
                <code>{segment.issueKey}</code>
                <div class="tooltip-head-right">
                  <span>{segment.timeSpent}</span>
                  <button
                    type="button"
                    class="delete-worklog-btn"
                    title="Rimuovi worklog"
                    aria-label="Rimuovi worklog"
                    disabled={!segment.worklogId || deletingWorklogId === segment.worklogId}
                    on:click|stopPropagation={() => askDeleteWorklog(segment.issueKey, segment.worklogId)}
                  >
                    <FontAwesomeIcon icon={faTrash} />
                  </button>
                </div>
              </div>
              <p class="tooltip-summary">{segment.summary}</p>
              <div class="tooltip-meta">
                <span>{segment.project}</span>
                <span>{segment.author}</span>
                <span>{segment.started || '-'}</span>
              </div>
              {#if segment.comment}
                <p class="tooltip-comment">{segment.comment}</p>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</section>

{#if deleteConfirmTarget}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    on:click={closeDeleteConfirm}
  >
    <div on:click|stopPropagation>
      <ConfirmCard
        title="Conferma eliminazione"
        message="Vuoi davvero eliminare questo worklog Jira?"
        confirmLabel={deletingWorklogId ? 'Eliminazione...' : 'Elimina'}
        onConfirm={() => void confirmDeleteWorklog()}
        onCancel={closeDeleteConfirm}
      />
    </div>
  </div>
{/if}

<style>
  .useractivity {
    margin-top: 1rem;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
    padding: 0.9rem;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    margin-bottom: 0.8rem;
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .head h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
  }

  .badge-day {
    font-size: 0.72rem;
    color: #475569;
    font-family: var(--font-mono);
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    padding: 2px 8px;
  }

  .target-hours {
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
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

  .worklog-actions-row {
    display: flex;
    align-items: flex-start;
    gap: 15px;
    margin-bottom: 0.45rem;
  }

  .worklog-card-col {
    flex: 0 0 auto;
    min-width: auto;
  }

  .worklog-actions-row :global(.jira-worklog) {
    width: auto;
  }

  .complete-btn {
    border: 1px solid #94a3b8;
    background: #f1f5f9;
    color: #334155;
    border-radius: 9px;
    padding: 0.35rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .complete-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .progress-wrap {
    margin-top: 0.25rem;
  }

  .progress-meta {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.45rem;
    font-size: 0.72rem;
    color: #475569;
    font-family: var(--font-mono);
  }

  .progress-track {
    position: relative;
    display: flex;
    width: 100%;
    min-height: 44px;
    border: 1px solid #dbe4ef;
    border-radius: 12px;
    background: #eef2f7;
  }

  .progress-segment {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--segment-color);
    border-right: 1px solid rgba(255, 255, 255, 0.35);
    outline: none;
    transition: filter 120ms ease;
    min-width: 22px;
    overflow: visible;
  }

  .progress-segment:hover,
  .progress-segment:focus {
    filter: brightness(1.06);
    z-index: 3;
  }

  .segment-label {
    max-width: 100%;
    padding: 0 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.64rem;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1px 1px rgba(0, 0, 0, 0.25);
    pointer-events: none;
  }

  .segment-tooltip {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 10px);
    transform: translateX(-50%) translateY(4px);
    width: min(320px, 80vw);
    border-radius: 10px;
    border: 1px solid #dbe4ef;
    background: #ffffff;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.15);
    padding: 0.55rem 0.6rem;
    opacity: 0;
    visibility: hidden;
    pointer-events: auto;
    transition: opacity 140ms ease, transform 140ms ease;
  }

  .progress-segment:hover .segment-tooltip,
  .progress-segment:focus .segment-tooltip,
  .segment-tooltip:hover,
  .segment-tooltip:focus-within {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(0);
  }

  .tooltip-head {
    display: flex;
    justify-content: space-between;
    gap: 0.4rem;
    margin-bottom: 0.2rem;
  }

  .tooltip-head code {
    font-size: 0.68rem;
    border: 1px solid #dbeafe;
    border-radius: 6px;
    background: #f8fafc;
    padding: 1px 6px;
    color: #334155;
  }

  .tooltip-head span {
    font-size: 0.7rem;
    color: #0f766e;
    font-weight: 700;
  }

  .tooltip-head-right {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .delete-worklog-btn {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 1px solid #fecaca;
    background: #fff;
    color: #b91c1c;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .delete-worklog-btn:hover {
    background: #fef2f2;
  }

  .delete-worklog-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .tooltip-summary {
    margin: 0;
    font-size: 0.78rem;
    line-height: 1.3;
    color: #0f172a;
  }

  .tooltip-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.3rem;
    font-size: 0.65rem;
    color: #64748b;
    font-family: var(--font-mono);
  }

  .tooltip-comment {
    margin: 0.35rem 0 0;
    font-size: 0.72rem;
    color: #334155;
    border-top: 1px dashed #dbe4ef;
    padding-top: 0.28rem;
    white-space: pre-wrap;
  }

  @media (max-width: 860px) {
    .head {
      align-items: flex-start;
      flex-direction: column;
    }

    .worklog-actions-row {
      flex-direction: column;
      align-items: stretch;
    }

    .complete-btn {
      width: fit-content;
    }

  }
</style>
