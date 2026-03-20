<script lang="ts">
  import Loader from './Loader.svelte';

  export let show = false;     // accende/spegne overlay
  export let size = 1;
  export let duration = 2;

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
  }
</style>
