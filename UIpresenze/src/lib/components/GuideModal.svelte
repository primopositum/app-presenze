<script lang="ts">
  import { browser } from '$app/environment';
  import { onDestroy } from 'svelte';

  export let isOpen = false;
  export let onClose: () => void;
  export let pdfUrl: string;
  export let title = 'Guida';

  let previousBodyOverflow: string | null = null;
  let closing = false;
  let closeTimer: ReturnType<typeof setTimeout> | null = null;
  let hasLoaded = false;

  $: if (isOpen) hasLoaded = true;

  $: if (browser) {
    if (isOpen && previousBodyOverflow === null) {
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    } else if (!isOpen && previousBodyOverflow !== null) {
      document.body.style.overflow = previousBodyOverflow;
      previousBodyOverflow = null;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (isOpen && event.key === 'Escape') requestClose();
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) requestClose();
  }

  function requestClose() {
    if (closing) return;
    closing = true;
    closeTimer = setTimeout(() => {
      closing = false;
      closeTimer = null;
      onClose();
    }, 360);
  }

  onDestroy(() => {
    if (closeTimer) clearTimeout(closeTimer);
    if (browser && previousBodyOverflow !== null) {
      document.body.style.overflow = previousBodyOverflow;
    }
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if hasLoaded}
  <div
    class="guide-backdrop"
    class:closing
    class:cached-hidden={!isOpen && !closing}
    aria-hidden={!isOpen && !closing}
    role="presentation"
    on:click={handleBackdropClick}
    on:keydown={handleKeydown}
  >
    <div
      class="guide-sheet"
      role="dialog"
      tabindex="-1"
      aria-modal="true"
      aria-labelledby="guide-title"
    >
      <header class="guide-header">
        <h2 id="guide-title">{title}</h2>
        <div class="guide-actions">
          <a href={pdfUrl} target="_blank" rel="noreferrer" class="guide-open">Apri</a>
          <button type="button" class="guide-close" aria-label="Chiudi guida" on:click={requestClose}>×</button>
        </div>
      </header>

      <iframe src={pdfUrl} title={title} class="guide-viewer"></iframe>
    </div>
  </div>
{/if}

<style>
  .guide-backdrop {
    position: fixed;
    inset: 0;
    z-index: 3000;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    background: rgb(15 23 42 / 58%);
    backdrop-filter: blur(5px);
    animation: guide-backdrop-in 260ms ease-out;
  }

  .guide-backdrop.cached-hidden {
    display: none;
  }

  .guide-sheet {
    width: min(1100px, 100%);
    height: min(86vh, 900px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #fed7aa;
    border-bottom: 0;
    border-radius: 22px 22px 0 0;
    background: #fff;
    box-shadow: 0 -18px 55px rgb(15 23 42 / 28%);
    animation: guide-sheet-in 440ms cubic-bezier(0.32, 0.72, 0, 1);
  }

  .guide-header {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 1rem;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid #fed7aa;
    background: linear-gradient(180deg, #fff7ed, #fff);
  }

  .guide-header h2 {
    grid-column: 2;
    margin: 0;
    color: #9a3412;
    font-family: var(--font-infinity);
    font-size: 1.15rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .guide-actions {
    grid-column: 3;
    justify-self: end;
    display: flex;
    align-items: center;
    gap: 0.55rem;
  }

  .guide-open,
  .guide-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #fdba74;
    border-radius: 9px;
    background: #fff;
    color: #c2410c;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
  }

  .guide-open {
    min-height: 38px;
    padding: 0 0.8rem;
    font-size: 0.85rem;
  }

  .guide-close {
    width: 38px;
    height: 38px;
    font-size: 1.55rem;
    line-height: 1;
  }

  .guide-open:hover,
  .guide-close:hover {
    background: #ffedd5;
  }

  .guide-viewer {
    width: 100%;
    min-height: 0;
    flex: 1;
    border: 0;
    background: #f8fafc;
  }

  @keyframes guide-backdrop-in {
    from { opacity: 0; backdrop-filter: blur(0); }
    to { opacity: 1; backdrop-filter: blur(5px); }
  }

  @keyframes guide-sheet-in {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
  }

  .guide-backdrop.closing {
    animation: guide-backdrop-out 320ms ease-in forwards;
  }

  .guide-backdrop.closing .guide-sheet {
    animation: guide-sheet-out 360ms cubic-bezier(0.32, 0.72, 0, 1) forwards;
  }

  @keyframes guide-backdrop-out {
    from { opacity: 1; backdrop-filter: blur(5px); }
    to { opacity: 0; backdrop-filter: blur(0); }
  }

  @keyframes guide-sheet-out {
    from { transform: translateY(0); }
    to { transform: translateY(100%); }
  }

  @media (max-width: 640px) {
    .guide-sheet {
      height: 92vh;
      border-radius: 16px 16px 0 0;
    }
  }
</style>
