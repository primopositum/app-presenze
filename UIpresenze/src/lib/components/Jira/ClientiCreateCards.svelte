<script lang="ts">
  import CreateClienteFlipCard from '$lib/components/Jira/CreateClienteFlipCard.svelte';
  import CreateContrattoFlipCard from '$lib/components/Jira/CreateContrattoFlipCard.svelte';
  import type { Cliente } from '$lib/services/clienti';

  export let clienti: Cliente[] = [];
  export let onCreated: (() => Promise<void> | void) | undefined = undefined;
  export let onOpen: (() => void) | undefined = undefined;
  export let onClosed: (() => void) | undefined = undefined;
  export let onNotify: ((message: string, success: boolean) => void) | undefined = undefined;

  let open = false;
  let selected: 'cliente' | 'contratto' | null = null;

  function closeOverlay() {
    selected = null;
    open = false;
    onClosed?.();
  }

  function showChoices() {
    selected = null;
  }
</script>

<div class="create-cards">
  <button class="open-create" type="button" on:click={() => { open = true; onOpen?.(); }} aria-haspopup="dialog">
    <span>+</span>
    Crea nuovo
  </button>

  {#if open}
    <div class="create-overlay" role="dialog" aria-modal="true" aria-label="Crea cliente o contratto">
      <button class="overlay-backdrop" type="button" data-history-hover-exclude aria-label="Chiudi creazione" on:click={closeOverlay}></button>
      <div class="cards-grid" class:has-selection={selected !== null}>
        <div class="card-option" class:active={selected === 'cliente'}>
          <CreateClienteFlipCard
            active={selected === 'cliente'}
            onSelect={() => (selected = 'cliente')}
            onClose={showChoices}
            {onNotify}
            {onCreated}
          />
        </div>
        <div class="card-option" class:active={selected === 'contratto'}>
          <CreateContrattoFlipCard
            {clienti}
            active={selected === 'contratto'}
            onSelect={() => (selected = 'contratto')}
            onClose={showChoices}
            {onNotify}
            {onCreated}
          />
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .create-cards { margin-bottom: 1rem; } .open-create { display: inline-flex; align-items: center; max-width: 100%; gap: .45rem; border: 0; border-radius: 8px; padding: .5rem .75rem; color: white; background: #0f766e; cursor: pointer; font: inherit; font-size: .82rem; overflow-wrap: anywhere; } .open-create span { flex: 0 0 auto; font-size: 1.2rem; line-height: .8; }
  .create-overlay { position: fixed; inset: 0; z-index: 70; display: grid; place-items: center; padding: 1rem; } .overlay-backdrop { position: absolute; inset: 0; border: 0; background: rgb(15 23 42 / .72); cursor: default; }
  .cards-grid { position: relative; z-index: 1; display: grid; width: min(100%, 800px); grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; transition: width .35s ease; } .card-option { min-width: 0; transition: opacity .28s ease, transform .35s ease; } .cards-grid.has-selection { width: min(100%, 400px); grid-template-columns: 1fr; } .cards-grid.has-selection .card-option:not(.active) { display: none; } .cards-grid.has-selection .card-option.active { animation: center-card .4s ease; }
  @keyframes center-card { from { opacity: .45; transform: scale(.88); } to { opacity: 1; transform: scale(1); } } @media (max-width: 680px) { .cards-grid { grid-template-columns: 1fr; width: min(100%, 400px); } }
</style>
