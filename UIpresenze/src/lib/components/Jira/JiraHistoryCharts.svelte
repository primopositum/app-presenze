<script lang="ts">
  import { arc, pie, scaleBand, scaleLinear, scaleOrdinal, schemeTableau10, sum, descending, type PieArcDatum } from 'd3';

  type JiraIssue = {
    key: string;
    fields?: {
      assignee?: { displayName?: string } | null;
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

  type ChartRow = {
    id: string;
    label: string;
    seconds: number;
    hours: number;
    percent: number;
    color: string;
  };

  export let issues: JiraIssue[] = [];
  export let selectedProjectKeys: string[] = [];

  const donutSize = 220;
  const outerRadius = 86;
  const innerRadius = 50;

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

  $: allProjects = [
    ...new Set(issues.map((issue) => issue.fields?.project?.key || 'N/D'))
  ];
  $: selectedSet = new Set(selectedProjectKeys);
  $: selectedIssues =
    selectedProjectKeys.length > 0
      ? issues.filter((issue) => selectedSet.has(issue.fields?.project?.key || 'N/D'))
      : issues;
  $: chartMode = selectedProjectKeys.length > 0 ? 'user' : 'project';
  $: grouped = selectedIssues.reduce<Record<string, { label: string; seconds: number }>>((acc, issue) => {
    const id =
      chartMode === 'user'
        ? issue.fields?.assignee?.displayName || 'Unassigned'
        : issue.fields?.project?.key || 'N/D';
    const label =
      chartMode === 'user'
        ? issue.fields?.assignee?.displayName || 'Unassigned'
        : issue.fields?.project?.name || issue.fields?.project?.key || 'Progetto non disponibile';
    if (!acc[id]) {
      acc[id] = { label, seconds: 0 };
    }
    acc[id].seconds += Math.max(0, Number(taskTotalSeconds(issue.fields) || 0));
    return acc;
  }, {});
  $: totalSeconds = sum(Object.values(grouped).map((v) => v.seconds));

  $: colorScale = scaleOrdinal<string, string>(schemeTableau10);

  $: chartRows = Object.entries(grouped)
    .map(([id, data]) => ({
      id,
      label: data.label,
      seconds: data.seconds,
      hours: data.seconds / 3600,
      percent: totalSeconds > 0 ? (data.seconds / totalSeconds) * 100 : 0,
      color: colorScale(id)
    }))
    .sort((a, b) => descending(a.seconds, b.seconds));

  $: pieLayout = pie<ChartRow>()
    .sort(null)
    .value((d) => d.seconds);

  $: arcs = pieLayout(chartRows);
  $: arcPath = arc<PieArcDatum<ChartRow>>().innerRadius(innerRadius).outerRadius(outerRadius);

  $: chartWidth = 390;
  $: chartHeight = Math.max(200, chartRows.length * 32 + 20);
  $: yScale = scaleBand<string>().domain(chartRows.map((d) => d.id)).range([0, chartHeight]).padding(0.2);
  $: xScale = scaleLinear().domain([0, Math.max(1, ...chartRows.map((d) => d.hours))]).range([0, 210]);
</script>

<section class="charts-shell">
  <h3>Grafici selezione</h3>

  <div class="metric-grid">
    <article class="metric-card">
      <span class="label">
        {selectedProjectKeys.length > 0 ? 'Utenti coinvolti (selezione)' : 'Progetti totali'}
      </span>
      <strong>{selectedProjectKeys.length > 0 ? chartRows.length : allProjects.length}</strong>
    </article>
    <article class="metric-card">
      <span class="label">Ore totali</span>
      <strong>{fmtHours(totalSeconds)}</strong>
    </article>
  </div>

  {#if allProjects.length > 0 && selectedProjectKeys.length === 0}
    <p class="hint">Nessun progetto selezionato: visualizzazione totale ore per progetto.</p>
  {/if}

  {#if chartRows.length === 0}
    <p class="empty">Nessun progetto disponibile per i grafici.</p>
  {:else}
    <article class="chart-card">
      <h4>{selectedProjectKeys.length > 0 ? 'Distribuzione ore per utente (%)' : 'Distribuzione ore per progetto (%)'}</h4>
      <div class="donut-wrap">
        <svg width={donutSize} height={donutSize} viewBox="0 0 220 220" role="img" aria-label={selectedProjectKeys.length > 0 ? 'Distribuzione ore per utente' : 'Distribuzione ore per progetto'}>
          <g transform="translate(110,110)">
            {#each arcs as slice (slice.data.id)}
              <path d={arcPath(slice) || ''} fill={slice.data.color} stroke="#fff" stroke-width="1.5"></path>
            {/each}
          </g>
        </svg>
        <ul class="legend">
          {#each chartRows as row (row.id)}
            <li>
              <span class="dot" style={`--dot:${row.color}`}></span>
              <span class="name">{row.id}</span>
              <span class="num">{row.percent.toFixed(1)}%</span>
            </li>
          {/each}
        </ul>
      </div>
    </article>

    <article class="chart-card">
      <h4>{selectedProjectKeys.length > 0 ? 'Ore per utente' : 'Ore per progetto'}</h4>
      <div class="bar-wrap">
        <svg width={chartWidth} height={chartHeight + 24} viewBox={`0 0 ${chartWidth} ${chartHeight + 24}`} role="img" aria-label={selectedProjectKeys.length > 0 ? 'Ore per utente' : 'Ore per progetto'}>
          <g transform="translate(150,10)">
            {#each chartRows as row (row.id)}
              <rect
                y={yScale(row.id) || 0}
                x="0"
                width={xScale(row.hours)}
                height={yScale.bandwidth()}
                rx="6"
                fill={row.color}
                opacity="0.88"
              ></rect>
              <text x="-10" y={(yScale(row.id) || 0) + yScale.bandwidth() / 2 + 4} text-anchor="end" class="axis-label">{row.id}</text>
              <text x={xScale(row.hours) + 8} y={(yScale(row.id) || 0) + yScale.bandwidth() / 2 + 4} class="axis-value">
                {fmtHours(row.seconds)}
              </text>
            {/each}
          </g>
        </svg>
      </div>
    </article>
  {/if}
</section>

<style>
  .charts-shell {
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    background: #ffffff;
    padding: 0.9rem;
    min-width: 0;
  }

  h3 {
    margin: 0 0 0.75rem;
    font-size: 0.92rem;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-family: var(--font-mono);
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 0.75rem;
  }

  .metric-card {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.55rem 0.65rem;
    background: #f8fafc;
  }

  .metric-card .label {
    display: block;
    font-size: 0.68rem;
    color: #64748b;
    font-family: var(--font-mono);
  }

  .metric-card strong {
    font-size: 1.05rem;
    color: #0f172a;
  }

  .empty {
    margin: 0;
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 0.8rem;
    font-size: 0.8rem;
    color: #475569;
    font-family: var(--font-mono);
  }
  .hint {
    margin: 0 0 0.7rem;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    background: #eff6ff;
    color: #1e3a8a;
    padding: 0.6rem 0.7rem;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }

  .chart-card {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem;
    background: #fff;
    margin-bottom: 0.7rem;
  }

  .chart-card:last-child {
    margin-bottom: 0;
  }

  .chart-card h4 {
    margin: 0 0 0.45rem;
    font-size: 0.78rem;
    color: #334155;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }

  .donut-wrap {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem;
    align-items: center;
  }

  .legend {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 5px;
    max-height: 190px;
    overflow: auto;
  }

  .legend li {
    display: grid;
    grid-template-columns: 12px 1fr auto;
    align-items: center;
    gap: 6px;
    font-size: 0.7rem;
    color: #334155;
    font-family: var(--font-mono);
  }

  .dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: var(--dot);
  }

  .num {
    color: #0f172a;
  }

  .bar-wrap {
    overflow: auto;
  }

  .axis-label,
  .axis-value {
    font-size: 10px;
    fill: #334155;
    font-family: var(--font-mono);
  }

  .axis-value {
    fill: #0f172a;
  }

  @media (max-width: 1200px) {
    .donut-wrap {
      grid-template-columns: 1fr;
      justify-items: center;
    }

    .legend {
      width: 100%;
    }
  }
</style>
