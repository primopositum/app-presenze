<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Notification from './Notification.svelte';

  export let phrase1 = '';
  export let phrase2 = '';
  export let phrase3 = '';
  export let alwaysOpen = false;
  export let inlinePanel = false;

  let open = false;
  let rootEl: HTMLDivElement | null = null;
  $: isOpen = alwaysOpen || open;

  function toggle() {
    if (alwaysOpen) return;
    open = !open;
  }

  function handleDocumentClick(event: MouseEvent) {
    if (alwaysOpen || !isOpen || !rootEl) return;
    const target = event.target as Node | null;
    if (target && rootEl.contains(target)) return;
    open = false;
  }

  onMount(() => {
    document.addEventListener('click', handleDocumentClick);
  });

  onDestroy(() => {
    document.removeEventListener('click', handleDocumentClick);
  });
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</svelte:head>

<div bind:this={rootEl} class={`relative z-30 flex ${inlinePanel ? 'w-full max-w-none' : 'w-max max-w-none'} flex-col items-start gap-3 p-0`}>
  {#if !alwaysOpen}
    <button
      on:click={toggle}
      class="
        group relative inline-flex items-center gap-2.5
        px-6 py-3 rounded-2xl
        font-[Nunito,sans-serif] font-bold text-sm tracking-wide
        text-orange-500
        bg-white
        border border-sky-100
        shadow-sm
        overflow-hidden
        transition-all duration-300 ease-out
        hover:shadow-md hover:shadow-sky-100/70
        hover:border-orange-200
        hover:scale-[1.03]
        active:scale-[0.97]
        cursor-pointer
        outline-none focus-visible:ring-2 focus-visible:ring-orange-300
      "
      aria-expanded={isOpen}
    >
      <span
        class="
          absolute inset-0 -translate-x-full
          bg-gradient-to-r from-transparent via-orange-50 to-transparent
          opacity-0 group-hover:opacity-100 group-hover:translate-x-full
          transition-all duration-500 ease-in-out pointer-events-none
        "
      />

      <span
        class="
          absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100
          bg-gradient-to-br from-orange-50/60 to-sky-50/40
          transition-opacity duration-300 pointer-events-none
        "
      />

      <i
        class="
          fa-solid fa-hippo text-lg relative z-10
          transition-transform duration-300
          group-hover:rotate-[-8deg] group-hover:scale-110
        "
      />

      <span class="relative z-10 transition-transform duration-300 group-hover:translate-x-0.5">
        {isOpen ? 'Chiudi' : 'Mostra rapporto ore'}
      </span>

      <span
        class="
          relative z-10 w-1.5 h-1.5 rounded-full
          transition-all duration-300
          {isOpen ? 'bg-orange-400 scale-110' : 'bg-sky-300'}
        "
      />
    </button>
  {/if}

  <div
    class={`${
      inlinePanel
        ? 'relative w-full'
        : 'absolute left-0 top-full mt-2 w-max'
    } transition-all duration-300 ease-out ${isOpen ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 -translate-y-2 pointer-events-none'}`}
    style="transition: opacity 250ms ease, transform 250ms ease"
  >
    {#if isOpen}
      <Notification {phrase1} {phrase2} {phrase3} />
    {/if}
  </div>
</div>
