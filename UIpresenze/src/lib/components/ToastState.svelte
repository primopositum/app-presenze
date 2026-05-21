<script lang="ts">
  import { onDestroy } from 'svelte';

  export let open = false;
  export let success = true;
  export let message = '';
  export let duration = 2600;

  let timer: ReturnType<typeof setTimeout> | null = null;

  function clearTimer() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  $: {
    clearTimer();
    if (open && message) {
      timer = setTimeout(() => {
        open = false;
      }, Math.max(800, Number(duration || 2600)));
    }
  }

  onDestroy(() => {
    clearTimer();
  });
</script>

{#if open && message}
  <div class="toast" class:ok={success} class:ko={!success} role="status" aria-live="polite">
    <span class="dot" aria-hidden="true"></span>
    <span class="txt">{message}</span>
    <button
      type="button"
      class="close"
      aria-label="Chiudi notifica"
      on:click={() => (open = false)}
    >
      &times;
    </button>
  </div>
{/if}

<style>
  .toast {
    position: fixed;
    right: 14px;
    top: 14px;
    z-index: 2200;
    min-width: min(420px, calc(100vw - 28px));
    max-width: min(520px, calc(100vw - 28px));
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: start;
    gap: 8px;
    border-radius: 12px;
    padding: 10px 10px 10px 12px;
    box-shadow: 0 12px 26px rgba(15, 23, 42, 0.18);
    border: 1px solid transparent;
    animation: toast-in 170ms ease-out;
    font-family: var(--font-mono);
  }
  .toast.ok {
    background: #f0fdf4;
    border-color: #86efac;
    color: #166534;
  }
  .toast.ko {
    background: #fef2f2;
    border-color: #fecaca;
    color: #b91c1c;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    margin-top: 4px;
    background: currentColor;
    opacity: 0.9;
  }
  .txt {
    font-size: 12px;
    line-height: 1.35;
    word-break: break-word;
  }
  .close {
    border: 0;
    background: transparent;
    color: currentColor;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    opacity: 0.75;
  }
  .close:hover {
    background: rgba(15, 23, 42, 0.08);
    opacity: 1;
  }
  @keyframes toast-in {
    from {
      opacity: 0;
      transform: translateY(-7px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 640px) {
    .toast {
      left: 10px;
      right: 10px;
      max-width: none;
      min-width: 0;
    }
  }
</style>

