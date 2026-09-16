<script lang="ts">
  import { onDestroy } from 'svelte';
  import { fade, fly, type TransitionConfig } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { arc, pie, scaleBand, scaleLinear, scaleOrdinal, sum, descending, type PieArcDatum } from 'd3';

  type JiraIssue = {
    key: string;
    fields?: {
      summary?: string;
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
      worklog_authors?: { displayName?: string; timeSpentSeconds?: number }[];
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

  type ChartTooltip = {
    row: ChartRow;
    x: number;
    y: number;
  };

  type ChartSlide = {
    id: 'completed-issues' | 'users' | 'hours';
    kind: 'donut' | 'bar';
    title: string;
    tint: string;
    rows: ChartRow[];
    totalSeconds: number;
  };

  export let issues: JiraIssue[] = [];
  export let selectedProjectKeys: string[] = [];

  const donutSize = 286;
  const outerRadius = 112;
  const innerRadius = 65;
  const barValueColumnWidth = 80;
  const DONUT_COLORS = ['#2563eb', '#d97706', '#dc2626', '#16a34a', '#0f766e', '#7c2d12', '#4d7c0f', '#be123c', '#1d4ed8', '#a16207'];
  let chartTooltip: ChartTooltip | null = null;
  let barWrapWidth = 0;
  let chartSlides: ChartSlide[] = [];
  let cardElements: HTMLElement[] = [];

  let viewerOpen = false;
  let activeIndex = 0;
  let viewerOrigin: DOMRect | null = null;
  let viewerStage: HTMLElement | null = null;
  let viewerViewportWidth = 0;
  let viewerBarWidth = 0;
  let viewerDragging = false;
  let viewerDragOffset = 0;
  let dragPointerId: number | null = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragLastX = 0;
  let dragLastTime = 0;
  let dragVelocity = 0;
  let wheelDelta = 0;
  let wheelLocked = false;
  let wheelTimer: ReturnType<typeof setTimeout> | undefined;
  let pageScrollLocked = false;

  function showChartTooltip(event: MouseEvent, row: ChartRow) {
    if (viewerDragging) return;
    const tooltipWidth = 220;
    const tooltipHeight = 76;
    const gap = 12;
    const x = Math.min(event.clientX + gap, window.innerWidth - tooltipWidth - gap);
    const y = event.clientY + tooltipHeight + gap > window.innerHeight
      ? event.clientY - tooltipHeight - gap
      : event.clientY + gap;

    chartTooltip = {
      row,
      x: Math.max(gap, x),
      y: Math.max(gap, y)
    };
  }

  function hideChartTooltip() {
    chartTooltip = null;
  }

  function taskTotalSeconds(fields?: JiraIssue['fields']) {
    if (!fields) return 0;
    return (fields.worklog_authors || []).reduce(
      (total, author) => total + Math.max(0, Number(author?.timeSpentSeconds || 0)),
      0
    );
  }

  function addGroupedSeconds(
    acc: Record<string, { label: string; seconds: number }>,
    id: string,
    label: string,
    seconds: number
  ) {
    if (!acc[id]) {
      acc[id] = { label, seconds: 0 };
    }
    acc[id].seconds += Math.max(0, Number(seconds || 0));
  }

  function addIssueUserSeconds(acc: Record<string, { label: string; seconds: number }>, issue: JiraIssue) {
    const authors = (issue.fields?.worklog_authors || [])
      .map((author) => ({
        name: String(author?.displayName || '').trim() || 'Unassigned',
        seconds: Math.max(0, Number(author?.timeSpentSeconds || 0))
      }))
      .filter((author) => author.seconds > 0);

    if (authors.length > 0) {
      authors.forEach((author) => addGroupedSeconds(acc, author.name, author.name, author.seconds));
      return;
    }

    const assigneeName = issue.fields?.assignee?.displayName || 'Unassigned';
    addGroupedSeconds(acc, assigneeName, assigneeName, taskTotalSeconds(issue.fields));
  }

  function fmtHours(seconds: number) {
    const hours = seconds / 3600;
    const rounded = Math.round(hours * 10) / 10;
    return Number.isInteger(rounded)
      ? `${rounded.toFixed(0)}h`
      : `${rounded.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}h`;
  }

  function barLayout(rows: ChartRow[], availableWidth: number, large: boolean) {
    const rowHeight = large ? 42 : 32;
    const charWidth = large ? 8.6 : 7.2;
    const maxLabelLength = rows.reduce((acc, row) => Math.max(acc, row.label.length), 0);
    const labelWidth = Math.min(large ? 440 : 360, Math.max(150, Math.ceil(maxLabelLength * charWidth)));
    // Le barre occupano la larghezza disponibile (margine per evitare scroll subpixel).
    const areaWidth = Math.max(210, availableWidth - labelWidth - barValueColumnWidth - 4);
    const height = Math.max(200, rows.length * rowHeight + 20);
    return {
      labelWidth,
      width: labelWidth + areaWidth + barValueColumnWidth,
      height,
      y: scaleBand<string>().domain(rows.map((row) => row.id)).range([0, height]).padding(0.2),
      x: scaleLinear().domain([0, Math.max(1, ...rows.map((row) => row.hours))]).range([0, areaWidth])
    };
  }

  function prefersReducedMotion() {
    return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  // Rettangolo della card solo se visibile: altrimenti lo zoom partirebbe da fuori schermo.
  function visibleCardRect(index: number) {
    const rect = cardElements[index]?.getBoundingClientRect();
    if (!rect || rect.bottom <= 0 || rect.top >= window.innerHeight) return null;
    return rect;
  }

  function openViewer(index: number) {
    hideChartTooltip();
    activeIndex = index;
    viewerOrigin = visibleCardRect(index);
    viewerOpen = true;
  }

  function closeViewer() {
    if (!viewerOpen) return;
    hideChartTooltip();
    viewerOrigin = visibleCardRect(activeIndex);
    viewerOpen = false;
    cardElements[activeIndex]?.focus({ preventScroll: true });
  }

  function goToSlide(index: number) {
    hideChartTooltip();
    activeIndex = Math.min(chartSlides.length - 1, Math.max(0, index));
  }

  function handleCardKeydown(event: KeyboardEvent, index: number) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    openViewer(index);
  }

  function handleViewerKeydown(event: KeyboardEvent) {
    if (!viewerOpen) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeViewer();
    } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      goToSlide(activeIndex + (event.key === 'ArrowRight' ? 1 : -1));
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      goToSlide(event.key === 'Home' ? 0 : chartSlides.length - 1);
    } else if (event.key === 'Tab' && viewerStage) {
      // Mantiene il focus dentro il viewer.
      const focusable = Array.from(viewerStage.querySelectorAll<HTMLElement>('button:not([disabled])'));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === viewerStage)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  function handleViewerPointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target instanceof Element && event.target.closest('button')) return;
    dragPointerId = event.pointerId;
    dragStartX = dragLastX = event.clientX;
    dragStartY = event.clientY;
    dragLastTime = performance.now();
    dragVelocity = 0;
  }

  function handleViewerPointerMove(event: PointerEvent) {
    if (dragPointerId !== event.pointerId) return;
    const dx = event.clientX - dragStartX;
    const dy = event.clientY - dragStartY;

    if (!viewerDragging) {
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) {
        dragPointerId = null;
        return;
      }
      if (Math.abs(dx) < 8) return;
      viewerDragging = true;
      hideChartTooltip();
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    }

    const now = performance.now();
    dragVelocity = (event.clientX - dragLastX) / Math.max(1, now - dragLastTime);
    dragLastX = event.clientX;
    dragLastTime = now;

    // Resistenza elastica oltre il primo e l'ultimo grafico.
    const pastEdge = (dx > 0 && activeIndex === 0) || (dx < 0 && activeIndex === chartSlides.length - 1);
    viewerDragOffset = pastEdge ? dx * 0.28 : dx;
  }

  function handleViewerPointerEnd(event: PointerEvent) {
    if (dragPointerId !== event.pointerId) return;
    dragPointerId = null;
    if (!viewerDragging) return;

    const offset = viewerDragOffset;
    const swiped = Math.abs(offset) > viewerViewportWidth * 0.18 || (Math.abs(dragVelocity) > 0.45 && Math.abs(offset) > 24);
    viewerDragging = false;
    viewerDragOffset = 0;
    if (swiped) goToSlide(activeIndex + (offset < 0 ? 1 : -1));
  }

  function canScrollWithin(target: EventTarget | null, boundary: HTMLElement, vertical: boolean, delta: number) {
    let element = target instanceof Element ? target : null;
    while (element && element !== boundary) {
      if (element instanceof HTMLElement) {
        const overflow = getComputedStyle(element)[vertical ? 'overflowY' : 'overflowX'];
        if (overflow === 'auto' || overflow === 'scroll') {
          const position = vertical ? element.scrollTop : element.scrollLeft;
          const max = vertical
            ? element.scrollHeight - element.clientHeight
            : element.scrollWidth - element.clientWidth;
          if (delta < 0 ? position > 0 : position < max - 1) return true;
        }
      }
      element = element.parentElement;
    }
    return false;
  }

  function handleViewerWheel(event: WheelEvent) {
    if (event.ctrlKey) return;
    const vertical = Math.abs(event.deltaY) >= Math.abs(event.deltaX);
    const delta = vertical ? event.deltaY : event.deltaX;
    if (!delta) return;

    // Un gesto (anche con inerzia) cambia al massimo un grafico: si sblocca dopo una pausa.
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => {
      wheelDelta = 0;
      wheelLocked = false;
    }, 200);

    // Legende e barre lunghe scorrono prima di passare al grafico successivo.
    if (canScrollWithin(event.target, event.currentTarget as HTMLElement, vertical, delta)) {
      wheelLocked = true;
      return;
    }

    event.preventDefault();
    if (wheelLocked) return;
    wheelDelta += delta;
    if (Math.abs(wheelDelta) < 40) return;
    wheelLocked = true;
    goToSlide(activeIndex + Math.sign(wheelDelta));
  }

  function setPageScrollLock(locked: boolean) {
    if (typeof document === 'undefined' || locked === pageScrollLocked) return;
    pageScrollLocked = locked;
    if (locked) {
      // Compensa la scrollbar che sparisce, cosi' la pagina sotto non si sposta.
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
      document.body.style.overflow = 'hidden';
      if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`;
    } else {
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    }
  }

  // Portal: il viewer esce dal root hover di JiraHistory e da eventuali stacking context.
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

  function focusOnMount(node: HTMLElement) {
    node.focus({ preventScroll: true });
  }

  // Zoom del viewer dalla card cliccata (e verso la card attiva in chiusura).
  function zoomFromCard(node: Element, { origin }: { origin: DOMRect | null }): TransitionConfig {
    if (prefersReducedMotion()) return { duration: 0 };

    const target = node.getBoundingClientRect();
    if (!origin || target.width === 0 || target.height === 0) {
      return {
        duration: 280,
        easing: cubicOut,
        css: (t) => `opacity: ${t}; transform: scale(${0.96 + 0.04 * t});`
      };
    }

    // Scala uniforme: il contenuto non si deforma durante lo zoom.
    const scale = Math.sqrt((origin.width / target.width) * (origin.height / target.height));
    const dx = origin.left + origin.width / 2 - (target.left + target.width / 2);
    const dy = origin.top + origin.height / 2 - (target.top + target.height / 2);
    return {
      duration: 480,
      easing: cubicOut,
      css: (t, u) =>
        `opacity: ${Math.min(1, t * 1.8)}; transform: translate3d(${dx * u}px, ${dy * u}px, 0) scale(${scale + (1 - scale) * t});`
    };
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
    if (chartMode === 'user') {
      addIssueUserSeconds(acc, issue);
      return acc;
    }

    const projectKey = issue.fields?.project?.key || 'N/D';
    const projectName = issue.fields?.project?.name || issue.fields?.project?.key || 'Progetto non disponibile';
    addGroupedSeconds(acc, projectKey, projectName, taskTotalSeconds(issue.fields));
    return acc;
  }, {});
  $: totalSeconds = sum(Object.values(grouped).map((v) => v.seconds));

  $: colorScale = scaleOrdinal<string, string>(DONUT_COLORS);

  $: chartRows = Object.entries(grouped)
    .map(([id, data]) => ({
      id,
      label: data.label,
      seconds: data.seconds,
      hours: data.seconds / 3600,
      percent: totalSeconds > 0 ? (data.seconds / totalSeconds) * 100 : 0,
      color: colorScale(id)
    }))
    .filter((row) => !(row.id === 'Unassigned' && row.seconds <= 0))
    .sort((a, b) => descending(a.seconds, b.seconds));

  $: completedIssueGrouped = selectedIssues.reduce<Record<string, { label: string; seconds: number }>>(
    (acc, issue) => {
      addGroupedSeconds(
        acc,
        issue.key,
        String(issue.fields?.summary || '').trim() || issue.key,
        taskTotalSeconds(issue.fields)
      );
      return acc;
    },
    {}
  );
  $: completedIssuesTotalSeconds = sum(Object.values(completedIssueGrouped).map((value) => value.seconds));
  $: completedIssueColorScale = scaleOrdinal<string, string>(DONUT_COLORS);
  $: completedIssueRows = Object.entries(completedIssueGrouped)
    .map(([id, data]) => ({
      id,
      label: data.label,
      seconds: data.seconds,
      hours: data.seconds / 3600,
      percent: completedIssuesTotalSeconds > 0 ? (data.seconds / completedIssuesTotalSeconds) * 100 : 0,
      color: completedIssueColorScale(id)
    }))
    .filter((row) => row.seconds > 0)
    .sort((a, b) => descending(a.seconds, b.seconds));

  $: pieLayout = pie<ChartRow>()
    .sort(null)
    .value((d: ChartRow) => d.seconds);
  $: arcPath = arc<PieArcDatum<ChartRow>>().innerRadius(innerRadius).outerRadius(outerRadius);

  $: {
    const hasSelection = selectedProjectKeys.length > 0;
    const slides: ChartSlide[] = [];
    if (hasSelection && completedIssueRows.length > 0) {
      slides.push({
        id: 'completed-issues',
        kind: 'donut',
        title: 'Distribuzione ore per issue completata (%)',
        tint: '#f2d9ec',
        rows: completedIssueRows,
        totalSeconds: completedIssuesTotalSeconds
      });
    }
    slides.push(
      {
        id: 'users',
        kind: 'donut',
        title: hasSelection ? 'Distribuzione ore per utente (%)' : 'Distribuzione ore per progetto (%)',
        tint: '#c9ccf8',
        rows: chartRows,
        totalSeconds
      },
      {
        id: 'hours',
        kind: 'bar',
        title: hasSelection ? 'Ore per utente' : 'Ore per progetto',
        tint: '#cfedef',
        rows: chartRows,
        totalSeconds
      }
    );
    chartSlides = slides;
  }

  $: if (activeIndex > 0 && activeIndex >= chartSlides.length) activeIndex = chartSlides.length - 1;
  $: if (viewerOpen && chartRows.length === 0) {
    viewerOrigin = null;
    viewerOpen = false;
  }
  $: activeSlide = chartSlides[activeIndex] ?? null;
  $: setPageScrollLock(viewerOpen);

  onDestroy(() => {
    clearTimeout(wheelTimer);
    setPageScrollLock(false);
  });
</script>

<svelte:window on:keydown={handleViewerKeydown} />

{#snippet donutChart(slide: ChartSlide)}
  <svg
    class="donut-svg"
    width={donutSize}
    height={donutSize}
    viewBox={`0 0 ${donutSize} ${donutSize}`}
    role="img"
    aria-label={slide.title}
  >
    <g transform={`translate(${donutSize / 2},${donutSize / 2})`}>
      {#each pieLayout(slide.rows) as slice (slice.data.id)}
        <path
          class="chart-segment"
          data-history-hover-exclude
          d={arcPath(slice) || ''}
          fill={slice.data.color}
          stroke="#fff"
          stroke-width="1.5"
          on:mouseenter={(event) => showChartTooltip(event, slice.data)}
          on:mousemove={(event) => showChartTooltip(event, slice.data)}
          on:mouseleave={hideChartTooltip}
        ></path>
      {/each}
    </g>
  </svg>
{/snippet}

{#snippet barChart(slide: ChartSlide, availableWidth: number, large: boolean)}
  {@const layout = barLayout(slide.rows, availableWidth, large)}
  <svg
    class="bar-svg"
    class:large
    width={layout.width}
    height={layout.height + 24}
    viewBox={`0 0 ${layout.width} ${layout.height + 24}`}
    role="img"
    aria-label={slide.title}
  >
    <g transform={`translate(${layout.labelWidth},10)`}>
      {#each slide.rows as row, index (row.id)}
        <rect
          class="chart-bar"
          data-history-hover-exclude
          style:--i={index}
          y={layout.y(row.id) || 0}
          x="0"
          width={layout.x(row.hours)}
          height={layout.y.bandwidth()}
          rx="6"
          fill={row.color}
          opacity="0.88"
          on:mouseenter={(event) => showChartTooltip(event, row)}
          on:mousemove={(event) => showChartTooltip(event, row)}
          on:mouseleave={hideChartTooltip}
        ></rect>
        <text x="-10" y={(layout.y(row.id) || 0) + layout.y.bandwidth() / 2 + 4} text-anchor="end" class="axis-label">{row.label}</text>
        <text x={layout.x(row.hours) + 8} y={(layout.y(row.id) || 0) + layout.y.bandwidth() / 2 + 4} class="axis-value" style:--i={index}>
          {fmtHours(row.seconds)}
        </text>
      {/each}
    </g>
  </svg>
{/snippet}

<section class="charts-shell" data-history-hover>
  <h3>Grafici selezione</h3>

  <div class="metric-grid">
    <article class="metric-card" data-history-hover>
      <span class="label">
        {selectedProjectKeys.length > 0 ? 'Utenti coinvolti (selezione)' : 'Progetti totali'}
      </span>
      <strong>{selectedProjectKeys.length > 0 ? chartRows.length : allProjects.length}</strong>
    </article>
    <article class="metric-card" data-history-hover>
      <span class="label">Ore totali</span>
      <strong>{fmtHours(totalSeconds)}</strong>
    </article>
  </div>

  {#if allProjects.length > 0 && selectedProjectKeys.length === 0}
    <p class="hint" data-history-hover-exclude>Nessun progetto selezionato: visualizzazione totale ore per progetto.</p>
  {/if}

  {#if chartRows.length === 0}
    <p class="empty" data-history-hover>Nessun progetto disponibile per i grafici.</p>
  {:else}
    <div class="charts-grid" style:--chart-body-height={`${donutSize}px`}>
      {#each chartSlides as slide, index (slide.id)}
        <div
          bind:this={cardElements[index]}
          class="chart-card"
          class:span-full={slide.kind === 'bar' && chartSlides.length > 2}
          style:--tint={slide.tint}
          data-history-hover
          role="button"
          tabindex="0"
          aria-label={`Apri "${slide.title}" a schermo intero`}
          on:click={() => openViewer(index)}
          on:keydown={(event) => handleCardKeydown(event, index)}
        >
          <header class="chart-card-head">
            <h4>{slide.title}</h4>
            <span class="expand-hint" aria-hidden="true">⤢</span>
          </header>

          {#if slide.kind === 'donut'}
            <div class="donut-wrap">
              {@render donutChart(slide)}
              <ul class="legend">
                {#each slide.rows as row (row.id)}
                  <li data-history-hover>
                    <span class="dot" data-history-hover-exclude style:--dot={row.color}></span>
                    <span class="name">{row.label}</span>
                    <span class="num">{row.percent.toFixed(1)}%</span>
                  </li>
                {/each}
              </ul>
            </div>
          {:else}
            <div class="bar-wrap" bind:clientWidth={barWrapWidth}>
              {@render barChart(slide, barWrapWidth, false)}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}

  {#if chartTooltip}
    <div
      class="chart-tooltip"
      style={`left:${chartTooltip.x}px; top:${chartTooltip.y}px;`}
      role="tooltip"
    >
      <strong>{chartTooltip.row.label}</strong>
      <span>{chartTooltip.row.percent.toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% del totale</span>
      <small>{fmtHours(chartTooltip.row.seconds)}</small>
    </div>
  {/if}
</section>

{#if viewerOpen && activeSlide}
  <div class="chart-viewer" use:portalToBody>
    <button
      type="button"
      class="viewer-backdrop"
      tabindex="-1"
      aria-label="Chiudi grafici"
      on:click={closeViewer}
      transition:fade={{ duration: prefersReducedMotion() ? 0 : 300 }}
    ></button>

    <div
      bind:this={viewerStage}
      class="viewer-stage"
      role="dialog"
      aria-modal="true"
      aria-labelledby="chart-viewer-title"
      tabindex="-1"
      use:focusOnMount
      in:zoomFromCard={{ origin: viewerOrigin }}
      out:zoomFromCard={{ origin: viewerOrigin }}
    >
      <header class="viewer-head">
        <div class="viewer-heading">
          <span class="viewer-counter">Grafico {activeIndex + 1} di {chartSlides.length}</span>
          {#key activeSlide.id}
            <h4 id="chart-viewer-title" in:fly={{ y: 12, duration: prefersReducedMotion() ? 0 : 420, easing: cubicOut }}>
              {activeSlide.title}
            </h4>
            <small in:fly={{ y: 12, duration: prefersReducedMotion() ? 0 : 420, delay: 60, easing: cubicOut }}>
              {activeSlide.rows.length} voci · {fmtHours(activeSlide.totalSeconds)}
            </small>
          {/key}
        </div>
        <button type="button" class="viewer-close" aria-label="Chiudi grafici" on:click={closeViewer}>×</button>
      </header>

      <div
        class="viewer-viewport"
        role="region"
        aria-roledescription="carosello"
        aria-label="Grafici"
        bind:clientWidth={viewerViewportWidth}
        on:pointerdown={handleViewerPointerDown}
        on:pointermove={handleViewerPointerMove}
        on:pointerup={handleViewerPointerEnd}
        on:pointercancel={handleViewerPointerEnd}
        on:wheel|nonpassive={handleViewerWheel}
      >
        <div
          class="viewer-track"
          class:dragging={viewerDragging}
          style:transform={`translate3d(calc(${-activeIndex * 100}% + ${viewerDragOffset}px), 0, 0)`}
        >
          {#each chartSlides as slide, index (slide.id)}
            <section class="viewer-slide" class:active={index === activeIndex} style:--tint={slide.tint} inert={index !== activeIndex}>
              <div class="viewer-slide-card" class:is-bar={slide.kind === 'bar'}>
                {#if slide.kind === 'donut'}
                  <div class="viewer-donut">
                    {@render donutChart(slide)}
                  </div>
                  <ul class="viewer-legend">
                    {#each slide.rows as row, rowIndex (row.id)}
                      <li style:--i={rowIndex}>
                        <span class="dot" style:--dot={row.color}></span>
                        <span class="name">{row.label}</span>
                        <span class="hours">{fmtHours(row.seconds)}</span>
                        <span class="num">{row.percent.toFixed(1)}%</span>
                        <span class="share" style:--dot={row.color} style:--share={`${row.percent}%`}></span>
                      </li>
                    {/each}
                  </ul>
                {:else}
                  <div class="viewer-bars" bind:clientWidth={viewerBarWidth}>
                    {@render barChart(slide, viewerBarWidth, true)}
                  </div>
                {/if}
              </div>
            </section>
          {/each}
        </div>

        <button
          type="button"
          class="viewer-nav prev"
          aria-label="Grafico precedente"
          disabled={activeIndex === 0}
          on:click={() => goToSlide(activeIndex - 1)}
        >‹</button>
        <button
          type="button"
          class="viewer-nav next"
          aria-label="Grafico successivo"
          disabled={activeIndex === chartSlides.length - 1}
          on:click={() => goToSlide(activeIndex + 1)}
        >›</button>
      </div>

      <footer class="viewer-foot">
        <div class="viewer-tabs">
          {#each chartSlides as slide, index (slide.id)}
            <button
              type="button"
              class="viewer-tab"
              class:active={index === activeIndex}
              style:--tint={slide.tint}
              aria-current={index === activeIndex ? 'true' : undefined}
              on:click={() => goToSlide(index)}
            >
              <span class="tab-swatch"></span>
              {slide.title}
            </button>
          {/each}
        </div>
        <span class="viewer-hint">← → · rotella · trascina · Esc per chiudere</span>
      </footer>
    </div>
  </div>
{/if}

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

  /* Due colonne a tutta larghezza: con due torte, il grafico a barre va sulla riga sotto. */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.7rem;
  }

  .chart-card {
    min-width: 0;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem;
    background: var(--tint, #fff);
    cursor: zoom-in;
    transition: background-color 0.15s ease, box-shadow 0.2s ease;
  }

  .chart-card:hover {
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  }

  .chart-card:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .chart-card.span-full {
    grid-column: 1 / -1;
  }

  .chart-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.45rem;
  }

  .chart-card h4 {
    margin: 0;
    font-size: 0.78rem;
    color: #334155;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }

  .expand-hint {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 26px;
    height: 26px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.75);
    color: #334155;
    font-size: 0.9rem;
    opacity: 0;
    transform: scale(0.85);
    transition: opacity 0.18s ease, transform 0.18s ease;
  }

  .chart-card:hover .expand-hint,
  .chart-card:focus-visible .expand-hint {
    opacity: 1;
    transform: none;
  }

  .donut-wrap {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem;
    align-items: center;
  }

  .donut-wrap .donut-svg {
    max-width: 100%;
    height: auto;
  }

  .legend {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 5px;
    max-height: var(--chart-body-height);
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

  /* Altezza massima pari al donut: con molte righe le barre scorrono invece di allungare la card. */
  .bar-wrap {
    max-height: var(--chart-body-height);
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

  .bar-svg.large .axis-label,
  .bar-svg.large .axis-value {
    font-size: 12px;
  }

  .chart-segment,
  .chart-bar {
    cursor: pointer;
    transition: opacity 140ms ease;
  }

  .chart-segment:hover,
  .chart-bar:hover {
    opacity: 0.72;
  }

  .chart-tooltip {
    position: fixed;
    z-index: 1300;
    display: grid;
    gap: 2px;
    width: max-content;
    max-width: 220px;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #ffffff;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.18);
    color: #0f172a;
    font-family: var(--font-mono);
    pointer-events: none;
  }

  .chart-tooltip strong {
    overflow: hidden;
    font-size: 0.72rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chart-tooltip span {
    font-size: 0.72rem;
    font-weight: 700;
  }


  .chart-tooltip small {
    color: #475569;
    font-size: 0.66rem;
  }

  /* Viewer a schermo quasi intero */
  .chart-viewer {
    --viewer-ease: cubic-bezier(0.22, 1, 0.36, 1);
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: clamp(10px, 3vh, 36px) clamp(10px, 3vw, 44px);
  }

  .viewer-backdrop {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    padding: 0;
    border: 0;
    background: rgba(15, 23, 42, 0.72);
    backdrop-filter: blur(4px);
    cursor: zoom-out;
  }

  .viewer-stage {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    width: min(100%, 1480px);
    height: min(100%, 980px);
    border: 1px solid #cbd5e1;
    border-radius: 18px;
    background: #f8fafc;
    box-shadow: 0 30px 80px rgba(15, 23, 42, 0.45);
    overflow: hidden;
    outline: none;
    overscroll-behavior: contain;
  }

  .viewer-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.25rem 0.7rem;
  }

  .viewer-heading {
    display: grid;
    gap: 0.2rem;
    min-width: 0;
  }

  .viewer-counter {
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .viewer-heading h4 {
    margin: 0;
    color: #0f172a;
    font-size: 1.05rem;
    font-family: var(--font-mono);
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  .viewer-heading small {
    color: #475569;
    font-size: 0.74rem;
    font-family: var(--font-mono);
  }

  .viewer-close {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 38px;
    height: 38px;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: #fff;
    color: #334155;
    font-size: 1.4rem;
    line-height: 1;
    cursor: pointer;
    transition: background-color 0.18s ease, transform 0.18s ease;
  }

  .viewer-close:hover {
    background: #f1f5f9;
    transform: rotate(90deg);
  }

  .viewer-viewport {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
    touch-action: pan-y;
  }

  .viewer-track {
    display: flex;
    height: 100%;
    transition: transform 640ms var(--viewer-ease);
    will-change: transform;
  }

  .viewer-track.dragging {
    transition: none;
    cursor: grabbing;
  }

  /* border-box esplicito: lo scorrimento del carosello assume slide larghe esattamente il 100%. */
  .viewer-stage,
  .viewer-slide,
  .viewer-slide-card {
    box-sizing: border-box;
  }

  .viewer-slide {
    flex: 0 0 100%;
    min-width: 0;
    height: 100%;
    padding: 0.2rem clamp(2.9rem, 5vw, 4.75rem) 0.9rem;
    opacity: 0.3;
    transform: scale(0.92);
    transition: opacity 640ms var(--viewer-ease), transform 640ms var(--viewer-ease);
    -webkit-user-select: none;
    user-select: none;
  }

  .viewer-slide.active {
    opacity: 1;
    transform: none;
  }

  .viewer-slide-card {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(300px, 1fr);
    grid-template-rows: minmax(0, 1fr);
    gap: clamp(1rem, 3vw, 2.5rem);
    height: 100%;
    padding: clamp(1rem, 2.5vw, 2rem);
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    background: linear-gradient(155deg, var(--tint), #ffffff 78%);
  }

  .viewer-slide-card.is-bar {
    display: block;
  }

  .viewer-donut {
    display: grid;
    place-items: center;
    min-height: 0;
  }

  .viewer-donut .donut-svg {
    width: 100%;
    height: 100%;
    max-width: 640px;
  }

  .viewer-legend {
    display: grid;
    align-content: start;
    align-self: center;
    gap: 0.45rem;
    max-height: 100%;
    margin: 0;
    padding: 0 0.35rem 0 0;
    list-style: none;
    overflow-y: auto;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }

  .viewer-legend li {
    display: grid;
    grid-template-columns: 12px minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 0.35rem 0.65rem;
    padding: 0.5rem 0.7rem;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.78);
    color: #334155;
    font-size: 0.8rem;
    font-family: var(--font-mono);
  }

  .viewer-legend .dot {
    width: 11px;
    height: 11px;
  }

  .viewer-legend .name {
    overflow: hidden;
    color: #0f172a;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .viewer-legend .hours {
    color: #475569;
  }

  .viewer-legend .num {
    min-width: 5ch;
    font-weight: 700;
    text-align: right;
  }

  .viewer-legend .share {
    grid-column: 2 / -1;
    height: 4px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--dot) var(--share), rgba(15, 23, 42, 0.08) var(--share));
  }

  /* Margini auto: centra i grafici corti senza rendere irraggiungibile la parte alta di quelli lunghi. */
  .viewer-bars {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: auto;
    overscroll-behavior: contain;
  }

  .viewer-bars .bar-svg {
    flex: 0 0 auto;
    align-self: flex-start;
    margin-block: auto;
  }

  /* Ingresso del grafico attivo: parte in coda allo scorrimento del carosello. */
  .viewer-slide.active .donut-svg {
    animation: viewer-donut-in 780ms var(--viewer-ease) 60ms both;
  }

  .viewer-slide.active .viewer-legend li {
    animation: viewer-rise-in 480ms var(--viewer-ease) both;
    animation-delay: calc(min(var(--i), 14) * 28ms + 160ms);
  }

  .viewer-slide.active .chart-bar {
    transform-box: fill-box;
    transform-origin: left center;
    animation: viewer-bar-grow 720ms var(--viewer-ease) both;
    animation-delay: calc(min(var(--i), 20) * 26ms + 140ms);
  }

  .viewer-slide.active .axis-value {
    animation: viewer-fade-in 360ms ease both;
    animation-delay: calc(min(var(--i), 20) * 26ms + 480ms);
  }

  .viewer-nav {
    position: absolute;
    top: 50%;
    z-index: 2;
    display: grid;
    place-items: center;
    width: 46px;
    height: 46px;
    margin-top: -23px;
    padding: 0 0 3px;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.16);
    color: #0f172a;
    font-size: 1.7rem;
    line-height: 1;
    cursor: pointer;
    transition: opacity 0.25s ease, transform 0.25s var(--viewer-ease), background-color 0.18s ease;
  }

  .viewer-nav.prev {
    left: 0.7rem;
  }

  .viewer-nav.next {
    right: 0.7rem;
  }

  .viewer-nav:hover:not(:disabled) {
    background: #fff;
    transform: scale(1.08);
  }

  .viewer-nav:disabled {
    opacity: 0;
    pointer-events: none;
    transform: scale(0.8);
  }

  .viewer-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.7rem 1.25rem 0.95rem;
    border-top: 1px solid #e2e8f0;
    background: #fff;
  }

  .viewer-tabs {
    display: flex;
    gap: 0.4rem;
    min-width: 0;
    overflow-x: auto;
  }

  .viewer-tab {
    display: inline-flex;
    align-items: center;
    flex: 0 0 auto;
    gap: 0.45rem;
    padding: 0.42rem 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    background: #f8fafc;
    color: #64748b;
    font-size: 0.68rem;
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    cursor: pointer;
    transition: background-color 0.32s var(--viewer-ease), border-color 0.32s var(--viewer-ease),
      color 0.32s var(--viewer-ease), box-shadow 0.32s var(--viewer-ease);
  }

  .viewer-tab:hover {
    color: #0f172a;
  }

  .viewer-tab.active {
    border-color: #94a3b8;
    background: var(--tint);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    color: #0f172a;
  }

  .tab-swatch {
    width: 10px;
    height: 10px;
    border: 1px solid rgba(15, 23, 42, 0.2);
    border-radius: 999px;
    background: var(--tint);
  }

  .viewer-hint {
    color: #94a3b8;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    white-space: nowrap;
  }

  @keyframes viewer-donut-in {
    from {
      opacity: 0;
      transform: rotate(-70deg) scale(0.86);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @keyframes viewer-rise-in {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  @keyframes viewer-bar-grow {
    from {
      transform: scaleX(0);
    }
    to {
      transform: scaleX(1);
    }
  }

  @keyframes viewer-fade-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @media (max-width: 1000px) {
    .charts-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 760px) {
    .viewer-slide {
      padding-inline: 0.75rem;
    }

    .viewer-slide-card {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(0, 0.9fr) minmax(0, 1fr);
    }

    .viewer-legend {
      align-self: stretch;
    }

    .viewer-nav,
    .viewer-hint {
      display: none;
    }
  }

  @media (max-width: 560px) {
    .donut-wrap {
      grid-template-columns: 1fr;
      justify-items: center;
    }

    .legend {
      width: 100%;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .viewer-track,
    .viewer-slide,
    .viewer-tab,
    .viewer-nav,
    .viewer-close {
      transition: none;
    }

    .viewer-slide.active .donut-svg,
    .viewer-slide.active .viewer-legend li,
    .viewer-slide.active .chart-bar,
    .viewer-slide.active .axis-value {
      animation: none;
    }
  }
</style>
