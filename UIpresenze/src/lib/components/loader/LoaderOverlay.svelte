<script lang="ts">
  import Loader from './Loader.svelte';

  export let show = false;     // accende/spegne overlay
  export let size = 1;
  export let duration = 2;
  export let message = '';

  let visible = false;
  let minTimer: ReturnType<typeof setTimeout> | null = null;
  let canHide = true;

  $: {
    if (show) {
      visible = true;
      canHide = false;
      if (minTimer) clearTimeout(minTimer);
      minTimer = setTimeout(() => {
        canHide = true;
        if (!show) visible = false;
      }, 1000);
    } else if (canHide) {
      visible = false;
    }
  }
</script>

{#if visible}
  <div class="overlay">
    <div class="loader-wrapper">
      <Loader {size} {duration} />
      {#if message}
        <p class="loader-message" aria-live="polite">
          {message}<span class="loading-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
        </p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 40; /* sotto l'header */
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(2px);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .loader-wrapper {
    pointer-events: none; /* evita click strani */
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .loader-message {
    margin: 1.1rem 0 0;
    color: #fff;
    font-family: var(--font-mono, monospace);
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.04em;
  }

  .loading-dots {
    display: inline-flex;
    width: 1.3em;
  }

  .loading-dots span {
    animation: dot-fade 1.2s ease-in-out infinite;
  }

  .loading-dots span:nth-child(2) {
    animation-delay: 0.2s;
  }

  .loading-dots span:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes dot-fade {
    0%, 80%, 100% { opacity: 0.2; }
    40% { opacity: 1; }
  }

  @media (prefers-reduced-motion: reduce) {
    .loading-dots span {
      animation: none;
      opacity: 1;
    }
  }
</style>
