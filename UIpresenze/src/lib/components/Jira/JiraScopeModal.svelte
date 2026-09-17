<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { JiraScopeType } from '$lib/services/jira';

  export let open = false;
  export let loading = false;
  export let defaultType: JiraScopeType = 'filter';
  export let defaultValue = '';

  let scopeType: JiraScopeType = 'filter';
  let scopeValue = '';
  let localError = '';

  const dispatch = createEventDispatcher<{
    close: void;
    submit: { type: JiraScopeType; value: string };
  }>();

  $: if (open) {
    scopeType = defaultType;
    scopeValue = defaultValue;
    localError = '';
  }

  function closeModal() {
    if (loading) return;
    dispatch('close');
  }

  function onOverlayClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeModal();
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (!open) return;
    if (event.key === 'Escape') {
      closeModal();
    }
  }

  function submitModal() {
    const value = String(scopeValue || '').trim();
    if (!value) {
      localError = 'Inserisci un valore.';
      return;
    }
    localError = '';
    dispatch('submit', { type: scopeType, value });
  }
</script>

<svelte:window on:keydown={onKeydown} />

{#if open}
  <div
    class="fixed inset-0 bg-slate-900/35 backdrop-blur-[1px] flex items-center justify-center z-50"
    role="dialog"
    aria-modal="true"
    on:click={onOverlayClick}
  >
    <form
      class="bg-white rounded-xl border-2 border-orange-500 p-6 w-full max-w-md shadow-lg"
      on:submit|preventDefault={submitModal}
    >
      <h3 class="text-lg font-semibold mb-4 text-gray-800">Aggiungi Scope Jira</h3>

      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1" for="scope-type">Tipo</label>
        <select
          id="scope-type"
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          bind:value={scopeType}
          disabled={loading}
        >
          <option value="project">Progetto</option>
          <option value="filter">Filtro</option>
          <option value="labels">Label</option>
        </select>
      </div>

      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1" for="scope-value">Nome / ID</label>
        <input
          id="scope-value"
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          bind:value={scopeValue}
          disabled={loading}
          type="text"
          placeholder={
            scopeType === 'project'
              ? 'Es. A00'
              : scopeType === 'labels'
                ? 'Es. Commerciale'
                : 'Es. Progettie3 o 12345'
          }
        />
      </div>

      {#if localError}
        <div class="text-sm text-red-600 mb-2">{localError}</div>
      {/if}

      <div class="flex gap-2">
        <button
          type="button"
          class="flex-1 border border-gray-300 rounded-lg p-2 text-sm hover:bg-gray-50 transition"
          on:click={closeModal}
          disabled={loading}
        >
          Annulla
        </button>
        <button
          type="submit"
          class="flex-1 bg-gray-900 text-white rounded-lg p-2 text-sm hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          disabled={loading}
        >
          {loading ? 'Salvataggio...' : 'Salva'}
        </button>
      </div>
    </form>
  </div>
{/if}
