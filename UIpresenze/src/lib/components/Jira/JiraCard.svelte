<script lang="ts">
  import JiraWorklogCard from '$lib/components/Jira/JiraWorklogCard.svelte';
  import HoverCommentDiv from '$lib/components/Jira/HoverCommentDiv.svelte';

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
      comment?: {
        comments?: Array<{
          body?: unknown;
          renderedBody?: string;
          author?: { displayName?: string };
        }>;
      } | null;
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

  export let issue: JiraIssue;
  export let domain = (import.meta.env.PUBLIC_JIRA_DOMAIN ?? 'primopositum.atlassian.net').trim();
  export let showWorklog = true;
  export let tone: 'default' | 'completed' = 'default';
  export let openOnClick = true;

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
    Highest: { accent: '#DC2626', soft: '#FEE2E2', ink: '#7F1D1D', badgeText: '#FFFFFF' },
    High: { accent: '#EA580C', soft: '#FFEDD5', ink: '#9A3412', badgeText: '#FFFFFF' },
    Medium: { accent: '#CA8A04', soft: '#FEF9C3', ink: '#713F12', badgeText: '#111827' },
    Low: { accent: '#0891B2', soft: '#CFFAFE', ink: '#164E63', badgeText: '#FFFFFF' },
    Lowest: { accent: '#4F46E5', soft: '#E0E7FF', ink: '#312E81', badgeText: '#FFFFFF' }
  };
  const COMPLETED_THEME = {
    accent: '#16a34a',
    soft: '#dcfce7',
    ink: '#14532d',
    badgeText: '#ffffff'
  };

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

  function stripHtml(input: string) {
    return input.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function adfToText(node: unknown): string {
    if (!node || typeof node !== 'object') return '';
    const n = node as { type?: string; text?: string; content?: unknown[] };
    if (typeof n.text === 'string') return n.text;
    if (!Array.isArray(n.content)) return '';
    const joined = n.content
      .map((child) => adfToText(child))
      .filter(Boolean)
      .join(n.type === 'paragraph' ? ' ' : '\n');
    return joined.trim();
  }

  function issueComments(fields?: JiraIssue['fields']) {
    const comments = fields?.comment?.comments || [];
    return comments
      .map((c) => {
        const fromBody =
          typeof c.body === 'string' ? c.body.trim() : adfToText(c.body);
        const fromRendered = c.renderedBody ? stripHtml(c.renderedBody) : '';
        const body = fromBody || fromRendered;
        if (!body) return '';
        const author = c.author?.displayName ? `${c.author.displayName}: ` : '';
        return `${author}${body}`;
      })
      .filter(Boolean);
  }

  function priorityTheme(name?: string) {
    if (!name) return PRIORITY_THEME.Medium;
    return PRIORITY_THEME[name] || PRIORITY_THEME.Medium;
  }

  function openIssue(key: string) {
    window.open(`https://${domain}/browse/${key}`, '_blank', 'noopener,noreferrer');
  }

  $: f = issue.fields || {};
  $: status = f.status?.name || 'Unknown';
  $: priority = f.priority?.name || 'Medium';
  $: totalSeconds = taskTotalSeconds(f);
  $: meta = statusMeta(status);
  $: pmeta = tone === 'completed' ? COMPLETED_THEME : priorityTheme(priority);
  $: hoverComments = issueComments(f);
</script>

<article
  class="card"
  class:completed={tone === 'completed'}
  class:static-card={!openOnClick}
  style={`--card-text: ${meta.text}; --priority-accent: ${pmeta.accent}; --priority-soft: ${pmeta.soft}; --priority-ink: ${pmeta.ink}; --priority-badge-text: ${pmeta.badgeText};`}
  role={openOnClick ? 'button' : undefined}
  tabindex={openOnClick ? 0 : undefined}
  on:click={() => (openOnClick ? openIssue(issue.key) : undefined)}
  on:keydown={(e) => (openOnClick && (e.key === 'Enter' || e.key === ' ') ? openIssue(issue.key) : undefined)}
>
  <div class="card-top">
    <code class="issue-key">{f.project?.name || '-'}</code>
    <span class="priority" title={priority}>
      <span class="priority-icon">{PRIORITY_ICON[priority] || 'o'}</span>
      <span class="priority-label">{priority}</span>
    </span>
  </div>
  <p class="summary">{f.summary || '-'}</p>
  {#if showWorklog}
    <div class="worklog-slot worklog-row">
      <div class="worklog-main">
        <JiraWorklogCard
          issueKey={issue.key}
          projectCode={f.project?.key || issue.key.split('-')[0] || ''}
          issueSummary={f.summary || ''}
        />
      </div>
      <div class="worklog-comments">
        <HoverCommentDiv comments={hoverComments} label="Commenti rapidi" />
      </div>
    </div>
  {/if}
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

<style>
  .card {
    container-type: inline-size;
    position: relative;
    z-index: 1;
    overflow: visible;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid var(--priority-accent, #d1a900);
    border-radius: 12px;
    padding: 1.1rem;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  }
  .card.static-card {
    cursor: default;
  }
  .card:hover {
    z-index: 70;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  }
  .card:focus-within {
    z-index: 70;
  }
  .card.completed {
    border-color: #bbf7d0;
    box-shadow: 0 2px 10px rgba(22, 163, 74, 0.12);
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
  .priority-icon {
    display: inline-block;
    min-width: 1.2ch;
    text-align: center;
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
  .worklog-slot {
    margin: 0 0 0.55rem;
  }
  .worklog-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
  }
  .worklog-main {
    min-width: 0;
    flex: 1;
  }
  .worklog-comments {
    margin-left: auto;
    padding-top: 1px;
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
  .card.completed .status-pill {
    color: #166534;
    background: #dcfce7;
    border-color: #86efac;
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
  .card.completed .task-hours {
    color: #14532d;
    background: #f0fdf4;
    border-color: #86efac;
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
  .card.completed .avatar {
    background: #ecfdf5;
    border-color: #86efac;
    color: #166534;
  }
  .date {
    font-size: 11px;
    color: #64748b;
    font-family: var(--font-mono);
  }

  @media (max-width: 700px) {
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
    .worklog-row {
      flex-wrap: wrap;
      gap: 6px;
    }
    .worklog-comments {
      width: 100%;
      display: flex;
      justify-content: flex-end;
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
  }

  @container (max-width: 310px) {
    .priority-label {
      display: none;
    }
    .status-pill {
      display: none;
    }
    .priority {
      padding-inline: 6px;
    }
  }

  @media (max-width: 480px) {
    .summary {
      font-size: 12px;
    }
    .card {
      border-radius: 10px;
    }
  }
</style>
