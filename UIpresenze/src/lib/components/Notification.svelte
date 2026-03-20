<script lang="ts">
  export let phrase1 = '';
  export let phrase2 = '';
  export let phrase3 = '';
</script>

<div class="notification-card" role="status" aria-live="polite">
  {#if phrase1}
    <p>{phrase1}</p>
  {/if}
  {#if phrase2}
    <p>{phrase2}</p>
  {/if}
  {#if phrase3}
    <p>{phrase3}</p>
  {/if}
</div>

<style>
  .notification-card {
    position: relative;
    overflow: hidden;
    width: max-content;
    min-width: 280px;
    max-width: none;
    border-radius: 14px;
    border: 1px solid #fed7aa;
    background: linear-gradient(180deg, #fffdf9 0%, #fff7ed 100%);
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    padding: 12px 14px;
    color: #0f172a;
    text-align: left;
  }

  .notification-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255, 237, 213, 0.45) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 237, 213, 0.45) 1px, transparent 1px);
    background-size: 12px 12px;
    opacity: 0.85;
    pointer-events: none;
  }

  .notification-card > * {
    position: relative;
    z-index: 1;
  }

  .notification-card p {
    margin: 0;
    line-height: 1.35;
    font-size: 0.92rem;
    white-space: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: thin;
  }

  .notification-card p + p {
    margin-top: 4px;
  }
</style>
