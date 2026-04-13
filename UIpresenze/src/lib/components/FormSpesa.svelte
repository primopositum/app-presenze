<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { SpesaCreate } from '$lib/services/trasferte';

  export let saving = false;
  export let error: string | null = null;
  export let submitLabel = 'Aggiungi spesa';
  export let coefficienteAuto: number | null = null;
  export let hasAutomobile = false;

  type SpesaFormSubmit = SpesaCreate & {
    kmPercorsi?: number;
    coefficiente?: number;
    coefficienteChanged?: boolean;
    tragittoSegments?: string[];
  };

  const dispatch = createEventDispatcher<{
    submit: SpesaFormSubmit;
    cancel: void;
  }>();

  const types: Array<{ value: number; label: string }> = [
    { value: 1, label: 'Pedaggi' },
    { value: 2, label: 'Rimborso km' },
    { value: 3, label: 'Ristoranti' },
    { value: 4, label: 'Albergo' },
    { value: 5, label: 'Parcheggi' },
    { value: 6, label: 'Aerei/treni' },
    { value: 7, label: 'Altro' }
  ];

  let type = 1;
  let importo = '';
  let kmPercorsi = '';
  let coefficiente = '';
  let tragitto = '';
  let coefficienteIniziale = '';
  let localError: string | null = null;
  $: if (type === 2) {
    const current = coefficienteIniziale;
    const next = coefficienteAuto !== null && Number.isFinite(coefficienteAuto) ? String(coefficienteAuto) : '';
    if (!current || current !== next) {
      coefficienteIniziale = next;
      if (!coefficiente || coefficiente === current) {
        coefficiente = next;
      }
    }
  }

  function close() {
    dispatch('cancel');
  }

  function onOverlayClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      close();
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      close();
    }
  }

  function onSubmit() {
    localError = null;

    if (type === 2) {
      if (!hasAutomobile) {
        localError = 'Seleziona prima una automobile per usare Rimborso km.';
        return;
      }

      const parsedKm = Number(String(kmPercorsi).replace(',', '.'));
      if (!Number.isFinite(parsedKm) || parsedKm < 0) {
        localError = 'Km percorsi non valido.';
        return;
      }

      const parsedCoeff = Number(String(coefficiente).replace(',', '.'));
      if (!Number.isFinite(parsedCoeff) || parsedCoeff < 0) {
        localError = 'Coefficiente non valido.';
        return;
      }

      const tragittoSegments = tragitto
        .split('/')
        .map((part) => part.trim())
        .filter((part) => part.length > 0);
      if (tragittoSegments.length === 0) {
        localError = 'Inserisci il tragitto (separa le tappe con /).';
        return;
      }

      const parsedImporto = Number((parsedKm * parsedCoeff).toFixed(2));
      dispatch('submit', {
        type,
        importo: parsedImporto,
        kmPercorsi: parsedKm,
        coefficiente: parsedCoeff,
        coefficienteChanged: parsedCoeff !== Number(coefficienteIniziale || 0),
        tragittoSegments
      });
      return;
    }

    const parsedImporto = Number(importo);
    if (!Number.isFinite(parsedImporto) || parsedImporto < 0) {
      localError = 'Importo non valido.';
      return;
    }
    dispatch('submit', { type, importo: parsedImporto });
  }
</script>

<svelte:window on:keydown={onKeydown} />

<div
  class="fixed inset-0 bg-slate-900/35 backdrop-blur-[1px] flex items-center justify-center z-50"
  on:click={onOverlayClick}
>
  <form
    class="bg-white rounded-xl border-2 border-orange-500 p-6 w-full max-w-md shadow-lg"
    on:submit|preventDefault={onSubmit}
  >
    <h2 class="text-lg font-semibold mb-4 text-gray-800">
      {submitLabel}
    </h2>

    <!-- Tipo -->
    <div class="mb-4">
      <label class="block text-sm text-gray-700 mb-1">Tipo</label>
      <select
        class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
        bind:value={type}
        on:change={(e) => (type = Number((e.currentTarget as HTMLSelectElement).value))}
        disabled={saving}
      >
        {#each types as t}
          <option value={t.value}>{t.label}</option>
        {/each}
      </select>
    </div>

    {#if type === 2}
      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1">Km percorsi</label>
        <input
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          type="number"
          min="0"
          step="0.1"
          placeholder="0.0"
          bind:value={kmPercorsi}
          disabled={saving}
          required
        />
      </div>

      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1">Coefficiente</label>
        <input
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          type="number"
          min="0"
          step="0.0001"
          placeholder="0.0000"
          bind:value={coefficiente}
          disabled={saving}
          required
        />
      </div>

      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1">Tragitto</label>
        <input
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          type="text"
          placeholder="es. Bergamo / Milano / Torino"
          bind:value={tragitto}
          disabled={saving}
          required
        />
      </div>
    {:else}
      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1">Importo</label>
        <input
          class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-orange-500 focus:outline-none"
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
          bind:value={importo}
          disabled={saving}
          required
        />
      </div>
    {/if}

    {#if localError || error}
      <div class="text-sm text-red-600 mb-2">
        {localError || error}
      </div>
    {/if}

    <div class="flex gap-2">
      <button
        type="button"
        class="flex-1 border border-gray-300 rounded-lg p-2 text-sm hover:bg-gray-50 transition"
        on:click={close}
        disabled={saving}
      >
        Annulla
      </button>

      <button
        type="submit"
        class="flex-1 bg-gray-900 text-white rounded-lg p-2 text-sm hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
        disabled={saving}
      >
        {saving ? 'Salvataggio...' : submitLabel}
      </button>
    </div>
  </form>
</div>

