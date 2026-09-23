<script lang="ts">
  /**
   * Cornice di un grafico.
   *
   * Il fondo e' bianco e l'unica tinta e' un filo in testa: dentro il cubo una
   * card colorata pieno toglie contrasto proprio ai marchi che devono spiccare.
   *
   * Ogni card si puo' aprire a schermo intero. Il riquadro ingrandito va in
   * fondo al body: dentro il cubo la `perspective` farebbe da contenitore al
   * `position: fixed` e lo terrebbe chiuso nella faccia. Le classifiche tagliate
   * (`limit` sul grafico) partono da 30 voci e ne aggiungono altre scorrendo:
   * disegnarle tutte subito, con migliaia di issue, bloccherebbe la pagina.
   */
  import { tick, type Snippet } from 'svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faUpRightAndDownLeftFromCenter, faXmark } from '@fortawesome/free-solid-svg-icons';
  import { fmtInt } from '../format';
  import { EXPANDED_STEP, portal, provideCardExpansion } from './cardExpansion';

  type Props = {
    title: string;
    subtitle?: string;
    /** Colore del filo in testa: raggruppa le card per argomento. */
    accent?: string;
    /** Occupa tutta la larghezza della griglia. */
    wide?: boolean;
    /** Nota sotto al grafico: come si legge, o cosa resta fuori. */
    note?: string;
    /** Pulsante per aprire il grafico a schermo intero. */
    expandable?: boolean;
    children?: Snippet;
  };

  let {
    title,
    subtitle,
    accent = '#94a3b8',
    wide = false,
    note,
    expandable = true,
    children
  }: Props = $props();

  /** Soglia dal fondo, in px, oltre la quale si caricano altre voci. */
  const LOAD_MARGIN = 240;

  let expanded = $state(false);
  let limit = $state(EXPANDED_STEP);
  let total = $state(0);
  let placeholderHeight = $state(0);
  let cardElement: HTMLElement | undefined = $state();
  let bodyElement: HTMLElement | undefined = $state();
  let openButton: HTMLButtonElement | undefined = $state();
  let closeButton: HTMLButtonElement | undefined = $state();
  let previousOverflow = '';

  const shown = $derived(Math.min(limit, total));

  provideCardExpansion({
    get expanded() {
      return expanded;
    },
    get limit() {
      return limit;
    },
    reportTotal(next) {
      total = next;
    }
  });

  function lockPage(locked: boolean) {
    const { style } = document.documentElement;
    if (locked) {
      previousOverflow = style.overflow;
      style.overflow = 'hidden';
    } else {
      style.overflow = previousOverflow;
    }
  }

  async function open() {
    placeholderHeight = cardElement?.offsetHeight ?? 0;
    limit = EXPANDED_STEP;
    expanded = true;
    lockPage(true);
    await tick();
    closeButton?.focus();
  }

  async function close() {
    if (!expanded) return;
    expanded = false;
    lockPage(false);
    await tick();
    openButton?.focus();
  }

  function nearBottom() {
    if (!bodyElement) return false;
    const { scrollTop, clientHeight, scrollHeight } = bodyElement;
    return scrollTop + clientHeight >= scrollHeight - LOAD_MARGIN;
  }

  function loadMore() {
    if (limit < total) limit += EXPANDED_STEP;
  }

  /**
   * Se le voci non bastano a far scorrere il riquadro (schermo alto), si
   * aggiungono finche' non scorre: altrimenti lo scroll non partirebbe mai.
   */
  $effect(() => {
    if (!expanded || limit >= total) return;
    void tick().then(() => {
      if (expanded && nearBottom()) loadMore();
    });
  });

  $effect(() => () => {
    if (expanded) lockPage(false);
  });
</script>

<svelte:window
  onkeydown={(event) => {
    if (expanded && event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      void close();
    }
  }}
/>

{#snippet head(action: 'open' | 'close' | 'none')}
  <header>
    <h4>{title}</h4>
    <div class="head-side">
      {#if subtitle}<small>{subtitle}</small>{/if}
      {#if action === 'close'}
        <button
          type="button"
          class="card-action"
          bind:this={closeButton}
          aria-label="Riduci il grafico"
          title="Riduci (Esc)"
          onclick={() => close()}
        >
          <FontAwesomeIcon icon={faXmark} />
        </button>
      {:else if action === 'open' && expandable}
        <button
          type="button"
          class="card-action"
          bind:this={openButton}
          data-history-hover-exclude
          aria-label={`Apri a schermo intero: ${title}`}
          title="Schermo intero"
          onclick={() => open()}
        >
          <FontAwesomeIcon icon={faUpRightAndDownLeftFromCenter} />
        </button>
      {/if}
    </div>
  </header>
{/snippet}

{#if expanded}
  <!-- Al suo posto resta una sagoma della stessa altezza: la griglia non salta. -->
  <article
    class="chart-card placeholder"
    class:wide
    style:--accent={accent}
    style:min-height={`${placeholderHeight}px`}
  >
    {@render head('none')}
    <p class="placeholder-note">Aperto a schermo intero.</p>
  </article>

  <!-- Resta al suo posto nella griglia: e' il figlio a finire nel body (vedi `portal`). -->
  <div class="portal-anchor">
    <!-- Un clic sul velo chiude; da tastiera chiude Esc. -->
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
    <div
      class="card-overlay"
      use:portal
      role="dialog"
      aria-modal="true"
      aria-label={title}
      tabindex="-1"
      onclick={(event) => {
        if (event.target === event.currentTarget) void close();
      }}
    >
      <article
        class="chart-card expanded"
        style:--accent={accent}
        data-history-hover
      >
        {@render head('close')}
        <div
          class="chart-body scroll"
          bind:this={bodyElement}
          onscroll={() => {
            if (nearBottom()) loadMore();
          }}
        >
          {@render children?.()}
        </div>
        {#if note || total > 0}
          <footer>
            {#if note}<p class="note">{note}</p>{/if}
            {#if total > 0}
              <p class="count">
                {#if shown < total}
                  Mostrate {fmtInt(shown)} di {fmtInt(total)} voci · scorri per vederne altre
                  <button type="button" class="link" onclick={() => (limit = total)}>
                    mostra tutte
                  </button>
                {:else}
                  Tutte le {fmtInt(total)} voci
                {/if}
              </p>
            {/if}
          </footer>
        {/if}
      </article>
    </div>
  </div>
{:else}
  <article
    class="chart-card"
    class:wide
    style:--accent={accent}
    bind:this={cardElement}
    data-history-hover
  >
    {@render head('open')}
    <div class="chart-body">{@render children?.()}</div>
    {#if note}<p class="note">{note}</p>{/if}
  </article>
{/if}

<style>
  .chart-card {
    /* Riferimento per le misure dei grafici: dentro il cubo la finestra non dice nulla. */
    container-type: inline-size;
    display: grid;
    align-content: start;
    gap: 0.5rem;
    min-width: 0;
    box-sizing: border-box;
    border: 1px solid #e2e8f0;
    border-top: 3px solid var(--accent);
    border-radius: 10px;
    padding: 0.7rem 0.75rem 0.75rem;
    background: #ffffff;
  }

  .chart-card.wide {
    grid-column: 1 / -1;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }

  h4 {
    margin: 0;
    color: #0f172a;
    font-size: 0.74rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .head-side {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 0.5rem;
  }

  small {
    color: #64748b;
    font-size: 0.68rem;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }

  /* Discreto finche' non serve: stesso disegno dei pulsanti del cubo, in piccolo. */
  .card-action {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    padding: 0;
    background: #fff;
    color: #94a3b8;
    font-size: 0.62rem;
    line-height: 1;
    cursor: pointer;
    transition: color 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
  }

  .card-action:hover,
  .card-action:focus-visible {
    border-color: #94a3b8;
    color: #0f172a;
    transform: scale(1.06);
  }

  .chart-body {
    min-width: 0;
  }

  .note {
    margin: 0;
    color: #94a3b8;
    font-size: 0.64rem;
    font-family: var(--font-mono);
    line-height: 1.35;
  }

  .placeholder {
    align-content: start;
    border-style: dashed;
    border-top-style: solid;
    background: #f8fafc;
  }

  .placeholder-note {
    margin: 0;
    color: #94a3b8;
    font-size: 0.68rem;
    font-family: var(--font-mono);
  }

  .portal-anchor {
    display: contents;
  }

  /*
   * Stesso velo del cubo a schermo intero, un gradino sopra.
   * La riga della griglia e' fissata all'altezza del velo: con una riga
   * automatica la card crescerebbe col contenuto e uscirebbe dallo schermo
   * invece di scorrere al suo interno.
   */
  .card-overlay {
    position: fixed;
    z-index: 1250;
    inset: 0;
    display: grid;
    grid-template-rows: minmax(0, 1fr);
    overflow: hidden;
    padding: clamp(10px, 2.5vh, 28px) clamp(10px, 2.5vw, 36px);
    background: rgba(15, 23, 42, 0.82);
    backdrop-filter: blur(4px);
    overscroll-behavior: contain;
    animation: overlay-in 160ms ease-out;
  }

  @keyframes overlay-in {
    from {
      opacity: 0;
    }
  }

  .chart-card.expanded {
    grid-template-rows: auto minmax(0, 1fr) auto;
    align-content: stretch;
    gap: 0.75rem;
    width: min(1400px, 100%);
    height: 100%;
    min-height: 0;
    margin: 0 auto;
    padding: 1rem 1.1rem 0.9rem;
    border-radius: 14px;
    box-shadow: 0 24px 60px rgba(2, 6, 23, 0.45);
  }

  .chart-card.expanded h4 {
    font-size: 0.86rem;
  }

  .chart-card.expanded .card-action {
    width: 32px;
    height: 32px;
    border-color: #cbd5e1;
    color: #334155;
    font-size: 0.8rem;
  }

  .chart-body.scroll {
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }

  footer {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.4rem 1rem;
    border-top: 1px solid #eef2f6;
    padding-top: 0.6rem;
  }

  .count {
    margin: 0;
    color: #64748b;
    font-size: 0.66rem;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }

  .link {
    margin-left: 0.4rem;
    border: 0;
    padding: 0;
    background: none;
    color: #0f172a;
    font: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
    cursor: pointer;
  }

  @media (prefers-reduced-motion: reduce) {
    .card-overlay {
      animation: none;
    }
  }
</style>
