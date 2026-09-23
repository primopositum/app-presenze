<script lang="ts">
  /**
   * Cubo 3D riutilizzabile: riceve le schermate come figli (`<CubeFace>`) oppure
   * come array di descrittori, e gestisce indice, loop, pulsanti e animazione.
   * Le schermate non sanno di stare dentro un cubo: contengono solo il contenuto.
   */
  import { onDestroy, setContext, tick, type Snippet } from 'svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import {
    faChevronLeft,
    faChevronRight,
    faFilter,
    faUpRightAndDownLeftFromCenter,
    faXmark
  } from '@fortawesome/free-solid-svg-icons';
  import {
    CUBE_CONTEXT_KEY,
    activeFace,
    canStep,
    cubeRotation,
    faceAngle,
    faceDepth,
    stepForIndex,
    type CubeContext,
    type CubeFaceDescriptor
  } from './cube';
  import CubeFace from './CubeFace.svelte';
  import ChartFilterPanel from '../filters/ChartFilterPanel.svelte';
  import { activeCount, chartFilters } from '../filters/core/filterState';
  import { getFilterScreen } from '../filters/registry';

  type Props = {
    /** Schermate passate come array; in alternativa si usano i figli `<CubeFace>`. */
    faces?: CubeFaceDescriptor[];
    children?: Snippet;
    /** Faccia visibile: bindabile per pilotare il cubo dall'esterno. */
    index?: number;
    /** Dall'ultima schermata si torna alla prima. */
    loop?: boolean;
    /** Altezza della scena: le facce di un cubo devono avere la stessa altezza. */
    height?: string;
    /**
     * 'all' tiene montate tutte le facce (cubo vero).
     * 'active' monta solo la faccia corrente e quelle adiacenti (cubo "finto", piu' leggero).
     */
    mount?: 'all' | 'active';
    /** Durata della rotazione in ms. */
    duration?: number;
    controls?: boolean;
    tabs?: boolean;
    keyboard?: boolean;
    draggable?: boolean;
    /** Pulsante per ingrandire il cubo a schermo intero. */
    expandable?: boolean;
    /** Pulsante filtri: compare sulle facce che dichiarano `filters`. */
    filterable?: boolean;
    label?: string;
    /** Notifica a rotazione finita: utile per i grafici che devono rimisurarsi. */
    onsettle?: (index: number) => void;
    /** Un `resize` sul window a fine transizione sveglia le librerie di grafici. */
    dispatchResizeOnSettle?: boolean;
  };

  let {
    faces = [],
    children,
    index = $bindable(0),
    loop = true,
    height = 'clamp(598px, 88vh, 988px)',
    mount = 'all',
    duration = 700,
    controls = true,
    tabs = true,
    keyboard = true,
    draggable = true,
    expandable = false,
    filterable = true,
    label = 'Schermate',
    onsettle,
    dispatchResizeOnSettle = true
  }: Props = $props();

  type Registration = {
    id: symbol;
    label?: () => string | undefined;
    tint?: () => string | undefined;
    filters?: () => string | undefined;
  };

  let registered = $state<Registration[]>([]);
  // Cresce all'infinito: il modulo decide la faccia, cosi' il salto ultima -> prima
  // non fa girare il cubo all'indietro di 270 gradi.
  let step = $state(0);
  let sceneWidth = $state(0);
  let dragOffset = $state(0);
  let dragging = $state(false);
  let expanded = $state(false);
  let filtersOpen = $state(false);
  let reducedMotion = $state(false);
  // A rotazione finita il cubo torna piatto: vedi `settled` in cube.ts.
  let settled = $state(true);
  // Sospende la transizione per il frame in cui si entra o si esce dal 3D.
  let instant = $state(false);
  let settleTimer: ReturnType<typeof setTimeout> | null = null;
  // Altezza che il cubo lascia in pagina mentre e' ingrandito: senza, il documento
  // si accorcia e il browser riporta la pagina in cima.
  let placeholderHeight = $state(0);
  let rootElement: HTMLElement | undefined = $state();
  let restoreScrollY = 0;
  let dragPointerId: number | null = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let scrollLocked = false;

  const usesArray = $derived(faces.length > 0);
  const count = $derived(usesArray ? faces.length : registered.length);
  const activeIndex = $derived(activeFace(step, count));
  const angle = $derived(faceAngle(count));
  const depth = $derived(faceDepth(sceneWidth, count));
  const rotation = $derived(
    cubeRotation(step, count) + (sceneWidth > 0 ? (dragOffset / sceneWidth) * angle : 0)
  );
  const navLabels = $derived(
    usesArray
      ? faces.map((face, position) => face.label || `Schermata ${position + 1}`)
      : registered.map((face, position) => face.label?.() || `Schermata ${position + 1}`)
  );
  const filterScreen = $derived(
    filterable
      ? getFilterScreen(
          usesArray ? faces[activeIndex]?.filters : registered[activeIndex]?.filters?.()
        )
      : undefined
  );
  const filterCount = $derived(
    filterScreen ? activeCount(filterScreen, $chartFilters[filterScreen.id]) : 0
  );
  const canPrev = $derived(canStep(step, count, -1, loop));
  const canNext = $derived(canStep(step, count, 1, loop));

  const context: CubeContext = {
    register(id, faceLabel, tint, filters) {
      registered.push({ id, label: faceLabel, tint, filters });
    },
    unregister(id) {
      const position = registered.findIndex((face) => face.id === id);
      if (position >= 0) registered.splice(position, 1);
    },
    indexOf(id) {
      return registered.findIndex((face) => face.id === id);
    },
    isMounted(faceIndex) {
      if (mount === 'all') return true;
      // Faccia corrente + adiacenti: quella in arrivo e' gia' montata quando entra in scena.
      const distance = Math.abs(faceIndex - activeIndex);
      return Math.min(distance, count - distance) <= 1;
    },
    isActive(faceIndex) {
      return faceIndex === activeIndex;
    },
    get count() {
      return count;
    },
    get activeIndex() {
      return activeIndex;
    },
    get angle() {
      return angle;
    },
    get depth() {
      return depth;
    },
    get reducedMotion() {
      return reducedMotion;
    },
    get settled() {
      return settled;
    }
  };

  setContext(CUBE_CONTEXT_KEY, context);

  $effect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotion = query.matches;
    const onChange = (event: MediaQueryListEvent) => (reducedMotion = event.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  });

  // L'indice bindabile e la faccia attiva restano allineati in entrambe le direzioni.
  $effect(() => {
    if (count > 0 && index !== activeIndex) {
      const target = index;
      turn(() => (step = stepForIndex(step, count, target, loop)));
    }
  });

  /**
   * Blocca la pagina dietro il cubo ingrandito.
   * `overflow: hidden` da solo non basta: Chrome sposta la finestra quando lo mette,
   * quindi si fissa il body all'offset corrente e lo si rimette com'era alla chiusura.
   */
  function setScrollLock(locked: boolean) {
    if (typeof document === 'undefined' || locked === scrollLocked) return;
    scrollLocked = locked;
    const { style } = document.body;

    if (locked) {
      // Compensa la scrollbar che sparisce, cosi' la pagina sotto non si sposta di lato.
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
      style.position = 'fixed';
      style.top = `-${restoreScrollY}px`;
      style.left = '0';
      style.width = '100%';
      if (scrollbarWidth > 0) style.paddingRight = `${scrollbarWidth}px`;
      return;
    }

    style.position = '';
    style.top = '';
    style.left = '';
    style.width = '';
    style.paddingRight = '';
  }

  function expand() {
    if (expanded) return;
    // Il cubo esce dal flusso: tengo il suo posto in pagina e dov'era lo scroll.
    placeholderHeight = rootElement?.getBoundingClientRect().height ?? 0;
    restoreScrollY = window.scrollY;
    expanded = true;
    setScrollLock(true);
  }

  async function collapse() {
    if (!expanded) return;
    expanded = false;
    setScrollLock(false);
    await tick();
    // Il ripristino va nel frame successivo, quando il browser ha ricalcolato l'altezza
    // del documento, ma prima del disegno: cosi' non si vede nessun salto.
    requestAnimationFrame(() => {
      window.scrollTo({ top: restoreScrollY, behavior: 'auto' });
      placeholderHeight = 0;
    });
  }

  function clearSettleTimer() {
    if (settleTimer === null) return;
    clearTimeout(settleTimer);
    settleTimer = null;
  }

  /**
   * Rete di sicurezza: `transitionend` non arriva se la durata e' zero (movimento
   * ridotto) o se la rotazione viene interrotta. Senza, il cubo resterebbe in 3D.
   */
  function scheduleSettle() {
    clearSettleTimer();
    settleTimer = setTimeout(settle, (reducedMotion ? 0 : duration) + 80);
  }

  /** Fine rotazione: si esce dal 3D senza animare, il risultato a schermo e' identico. */
  function settle() {
    clearSettleTimer();
    if (settled) return;
    instant = true;
    settled = true;
    onsettle?.(activeIndex);
    // I grafici misurano il contenitore: a fine rotazione conviene farli rimisurare.
    if (dispatchResizeOnSettle && typeof window !== 'undefined') {
      window.dispatchEvent(new Event('resize'));
    }
    releaseInstant();
  }

  function releaseInstant() {
    requestAnimationFrame(() => requestAnimationFrame(() => (instant = false)));
  }

  /**
   * Rientra nello spazio 3D e poi fa partire la rotazione.
   * I due passaggi stanno su frame diversi: insieme, il browser fonderebbe il
   * ritorno al 3D con la rotazione in un'unica transizione e la faccia di
   * partenza non si vedrebbe.
   */
  function turn(apply: () => void) {
    if (!settled) {
      apply();
      scheduleSettle();
      return;
    }

    instant = true;
    settled = false;
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        instant = false;
        apply();
        scheduleSettle();
      })
    );
  }

  function go(direction: 1 | -1) {
    if (!canStep(step, count, direction, loop)) return;
    turn(() => {
      step += direction;
      index = activeFace(step, count);
    });
  }

  export function next() {
    go(1);
  }

  export function prev() {
    go(-1);
  }

  export function goTo(target: number) {
    if (activeFace(step, count) === target) return;
    turn(() => {
      step = stepForIndex(step, count, target, loop);
      index = activeFace(step, count);
    });
  }

  function handleTransitionEnd(event: TransitionEvent) {
    if (event.propertyName !== 'transform' || event.target !== event.currentTarget) return;
    settle();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && filtersOpen) {
      event.preventDefault();
      filtersOpen = false;
      return;
    }
    if (event.key === 'Escape' && expanded) {
      event.preventDefault();
      void collapse();
      return;
    }
    if (!keyboard) return;
    // Le frecce dentro un campo spostano il cursore, non il cubo.
    if (event.target instanceof Element && event.target.closest('input, select, textarea')) return;
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      go(1);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      go(-1);
    }
  }

  /**
   * True se il gesto sta scorrendo un contenitore interno (un grafico piu' largo
   * della card, una legenda lunga): in quel caso il cubo non deve ruotare.
   */
  function scrollsInside(target: EventTarget | null, boundary: HTMLElement, deltaX: number) {
    let element = target instanceof Element ? target : null;

    while (element && element !== boundary) {
      if (element instanceof HTMLElement) {
        const { overflowX } = getComputedStyle(element);
        if (overflowX === 'auto' || overflowX === 'scroll') {
          const maxScroll = element.scrollWidth - element.clientWidth;
          const canScroll =
            deltaX > 0 ? element.scrollLeft > 0 : element.scrollLeft < maxScroll - 1;
          if (maxScroll > 1 && canScroll) return true;
        }
      }
      element = element.parentElement;
    }

    return false;
  }

  function handlePointerDown(event: PointerEvent) {
    if (!draggable || count < 2) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (
      event.target instanceof Element &&
      event.target.closest('button, a, input, select, textarea, [data-cube-no-drag]')
    )
      return;
    dragPointerId = event.pointerId;
    dragStartX = event.clientX;
    dragStartY = event.clientY;
  }

  function handlePointerMove(event: PointerEvent) {
    if (dragPointerId !== event.pointerId) return;
    const dx = event.clientX - dragStartX;
    const dy = event.clientY - dragStartY;

    if (!dragging) {
      // Scroll verticale dentro una faccia: il cubo non deve rubare il gesto.
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) {
        dragPointerId = null;
        return;
      }
      if (Math.abs(dx) < 10) return;
      if (scrollsInside(event.target, event.currentTarget as HTMLElement, dx)) {
        dragPointerId = null;
        return;
      }
      dragging = true;
      // Il trascinamento muove il cubo nello spazio: serve il 3D da subito.
      // La classe `dragging` toglie la transizione, quindi il rientro non si vede.
      settled = false;
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    }

    const blocked = (dx > 0 && !canPrev) || (dx < 0 && !canNext);
    dragOffset = blocked ? dx * 0.25 : dx;
  }

  function handlePointerEnd(event: PointerEvent) {
    if (dragPointerId !== event.pointerId) return;
    dragPointerId = null;
    if (!dragging) return;

    const offset = dragOffset;
    dragging = false;
    dragOffset = 0;
    if (Math.abs(offset) > Math.max(60, sceneWidth * 0.18)) go(offset < 0 ? 1 : -1);
    // Anche quando il gesto non cambia faccia il cubo deve tornare piatto.
    else scheduleSettle();
  }

  onDestroy(() => {
    clearSettleTimer();
    setScrollLock(false);
  });
</script>

<!-- La rotazione con le frecce parte da qualsiasi punto del cubo: il listener sta sul contenitore. -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<section
  class="cube-switcher"
  class:expanded
  bind:this={rootElement}
  style:--cube-height={expanded ? '100%' : height}
  style:--cube-duration={`${reducedMotion ? 0 : duration}ms`}
  style:--cube-placeholder={placeholderHeight ? `${placeholderHeight}px` : 'auto'}
  aria-roledescription="carosello"
  aria-label={label}
  onkeydown={handleKeydown}
>
  <div class="cube-shell">
    <div class="cube-stage">
      {#if controls && count > 1}
        <button
          type="button"
          class="cube-nav"
          data-history-hover-exclude
          aria-label="Schermata precedente"
          disabled={!canPrev}
          onclick={() => go(-1)}
        >
          <FontAwesomeIcon icon={faChevronLeft} />
        </button>
      {/if}

      <div
        class="scene"
        role="group"
        bind:clientWidth={sceneWidth}
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={handlePointerEnd}
        onpointercancel={handlePointerEnd}
      >
        <div
          class="cube"
          class:dragging
          class:instant
          style:transform={settled ? 'none' : `translateZ(${-depth}px) rotateY(${rotation}deg)`}
          style:transform-style={settled ? 'flat' : 'preserve-3d'}
          ontransitionend={handleTransitionEnd}
        >
          {#if usesArray}
            {#each faces as face, faceIndex (face.id ?? faceIndex)}
              <CubeFace label={face.label} tint={face.tint}>
                {#if face.component}
                  {@const Screen = face.component}
                  <Screen {...face.props ?? {}} />
                {/if}
              </CubeFace>
            {/each}
          {:else}
            {@render children?.()}
          {/if}
        </div>

        {#if expandable}
          <button
            type="button"
            class="cube-expand"
            data-history-hover-exclude
            aria-pressed={expanded}
            aria-label={expanded ? 'Riduci i grafici' : 'Ingrandisci i grafici'}
            title={expanded ? 'Riduci (Esc)' : 'Ingrandisci'}
            onclick={() => (expanded ? collapse() : expand())}
          >
            <!-- Due rami con l'icona fissa: passare l'icona come espressione reattiva
                 rompe FontAwesomeIcon, che non e' un componente in modalita' runes. -->
            {#if expanded}
              <FontAwesomeIcon icon={faXmark} />
            {:else}
              <FontAwesomeIcon icon={faUpRightAndDownLeftFromCenter} />
            {/if}
          </button>
        {/if}

        {#if filterScreen}
          <button
            type="button"
            class="cube-filter"
            class:with-expand={expandable}
            class:on={filtersOpen}
            data-history-hover-exclude
            aria-expanded={filtersOpen}
            aria-label={filterCount > 0
              ? `Filtri di ${filterScreen.title}: ${filterCount} attivi`
              : `Filtri di ${filterScreen.title}`}
            title="Filtri"
            onclick={() => (filtersOpen = !filtersOpen)}
          >
            <FontAwesomeIcon icon={faFilter} />
            {#if filterCount > 0}<span class="filter-count">{filterCount}</span>{/if}
          </button>

          {#if filtersOpen}
            <!-- Velo sui grafici: il pannello bianco non si confonde con le card sotto.
                 Un clic sul velo chiude, come fuori da un menu; da tastiera chiude Esc. -->
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <div
              class="filter-scrim"
              data-cube-no-drag
              data-history-hover-exclude
              aria-hidden="true"
              onclick={() => (filtersOpen = false)}
            ></div>
            <ChartFilterPanel screen={filterScreen} onclose={() => (filtersOpen = false)} />
          {/if}
        {/if}
      </div>

      {#if controls && count > 1}
        <button
          type="button"
          class="cube-nav"
          data-history-hover-exclude
          aria-label="Schermata successiva"
          disabled={!canNext}
          onclick={() => go(1)}
        >
          <FontAwesomeIcon icon={faChevronRight} />
        </button>
      {/if}
    </div>

    {#if tabs && count > 1}
      <nav class="cube-tabs" aria-label="Naviga tra le schermate">
        {#each navLabels as navLabel, faceIndex (navLabel + faceIndex)}
          <button
            type="button"
            class="cube-tab"
            class:active={faceIndex === activeIndex}
            data-history-hover-exclude
            aria-current={faceIndex === activeIndex ? 'true' : undefined}
            onclick={() => goTo(faceIndex)}
          >
            <span class="tab-dot"></span>
            {navLabel}
          </button>
        {/each}
      </nav>
    {/if}
  </div>
</section>

<style>
  .cube-switcher {
    min-width: 0;
  }

  /* Mentre il cubo e' a schermo intero la sezione tiene il suo posto in pagina. */
  .cube-switcher.expanded {
    min-height: var(--cube-placeholder);
  }

  .cube-shell {
    display: grid;
    gap: 0.6rem;
    min-width: 0;
  }

  .cube-switcher.expanded .cube-shell {
    position: fixed;
    inset: 0;
    z-index: 1200;
    grid-template-rows: minmax(0, 1fr) auto;
    padding: clamp(10px, 2.5vh, 28px) clamp(10px, 2.5vw, 36px);
    background: rgba(15, 23, 42, 0.82);
    backdrop-filter: blur(4px);
  }

  /* Le frecce stanno ai lati del cubo, non sopra i grafici. */
  .cube-stage {
    display: flex;
    align-items: center;
    gap: clamp(4px, 1vw, 14px);
    min-height: 0;
    min-width: 0;
  }

  .scene {
    position: relative;
    flex: 1 1 auto;
    height: var(--cube-height);
    min-height: 0;
    min-width: 0;
    perspective: 1600px;
    perspective-origin: 50% 50%;
  }

  .cube {
    position: relative;
    width: 100%;
    height: 100%;
    transition: transform var(--cube-duration) cubic-bezier(0.22, 1, 0.36, 1);
  }

  .cube.dragging,
  .cube.instant {
    transition: none;
  }

  .cube-nav,
  .cube-expand,
  .cube-filter {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.92);
    color: #334155;
    font-size: 0.9rem;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
    transition: background-color 0.15s ease, transform 0.15s ease, opacity 0.15s ease;
  }

  .cube-nav:hover:not(:disabled),
  .cube-expand:hover,
  .cube-filter:hover {
    background: #fff;
    color: #0f172a;
    transform: scale(1.06);
  }

  .cube-nav {
    flex: 0 0 auto;
  }

  .cube-nav:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .cube-expand {
    position: absolute;
    z-index: 2;
    top: 8px;
    right: 8px;
    font-size: 0.82rem;
  }

  /* Accanto al pulsante di ingrandimento, a sinistra: 38px + 8px di stacco. */
  .cube-filter {
    position: absolute;
    z-index: 2;
    top: 8px;
    right: 8px;
    font-size: 0.78rem;
  }

  .cube-filter.with-expand {
    right: 54px;
  }

  /* Sopra il velo, cosi' resta il pulsante che chiude il pannello. */
  .cube-filter.on {
    z-index: 5;
  }

  .filter-scrim {
    position: absolute;
    z-index: 3;
    inset: 0;
    border-radius: 14px;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(2px);
    animation: scrim-in 160ms ease-out;
  }

  @keyframes scrim-in {
    from {
      opacity: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .filter-scrim {
      animation: none;
    }
  }

  .cube-filter.on {
    border-color: #0f172a;
    background: #0f172a;
    color: #fff;
  }

  .cube-filter.on:hover {
    background: #1e293b;
    color: #fff;
  }

  .filter-count {
    position: absolute;
    top: -4px;
    right: -4px;
    display: grid;
    place-items: center;
    min-width: 16px;
    height: 16px;
    box-sizing: border-box;
    border: 2px solid #fff;
    border-radius: 999px;
    padding: 0 3px;
    background: #f97316;
    color: #fff;
    font-size: 0.56rem;
    font-family: var(--font-mono);
    font-weight: 700;
    line-height: 1;
  }

  .cube-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .cube-tab {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: #fff;
    color: #475569;
    font-size: 0.7rem;
    font-family: var(--font-mono);
    padding: 0.3rem 0.7rem;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease, background-color 0.15s ease;
  }

  .cube-tab .tab-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #cbd5e1;
    transition: background-color 0.15s ease;
  }

  .cube-tab.active {
    border-color: #0f172a;
    color: #0f172a;
  }

  .cube-tab.active .tab-dot {
    background: #f97316;
  }

  .cube-tab:hover {
    border-color: #94a3b8;
    color: #0f172a;
  }

  @media (max-width: 640px) {
    .cube-nav,
    .cube-expand,
    .cube-filter {
      width: 32px;
      height: 32px;
    }

    .cube-filter.with-expand {
      right: 46px;
    }
  }
</style>
