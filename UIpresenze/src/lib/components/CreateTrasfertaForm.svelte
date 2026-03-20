<script lang="ts">
  import { auth } from '$lib/stores/auth';
  import { useCreateTrasferta } from '$lib/hooks/useTrasferte';
  import type { TrasfertaCreate } from '$lib/services/trasferte';

  export let onCreated: (() => void) | undefined;
  export let onClose: (() => void) | undefined;

  let data = '';
  let azienda = '';
  let email_Id = '';
  let saving = false;
  let error: string | null = null;
  let ok = false;

  $: isSuper = !!$auth.user?.is_superuser;

  function reset() {
    data = '';
    azienda = '';
    email_Id = '';
  }

  function closeForm() {
    onClose?.();
  }

  function onOverlayClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeForm();
    }
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      closeForm();
    }
  }

  async function submit() {
    error = null;
    ok = false;
    if (!data || !azienda) {
      error = 'Data e azienda sono obbligatorie.';
      return;
    }
    saving = true;
    try {
      const payload: TrasfertaCreate = { data, azienda };
      const e_Id = isSuper && email_Id ? String(email_Id) : undefined;
      const create = useCreateTrasferta({ utente_mail: e_Id });
      await create(payload);
      ok = true;
      reset();
      onCreated?.();
      closeForm();
    } catch (e: any) {
      error = e?.message || 'Errore creazione trasferta';
    } finally {
      saving = false;
    }
  }
</script>

<!-- Overlay -->
<svelte:window on:keydown={onKeydown} />

<div class="fixed inset-0 bg-slate-900/35 backdrop-blur-[1px] flex items-center justify-center z-50" on:click={onOverlayClick}>
  <form class="bg-white rounded-xl p-6 w-full max-w-md shadow-lg" on:submit|preventDefault={submit}>
    <h2 class="text-lg font-semibold mb-4 text-gray-800">Crea Trasferta</h2>

    <div class="mb-4">
      <label class="block text-sm text-gray-700 mb-1">Data</label>
      <input type="date" bind:value={data} required class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"/>
    </div>

    <div class="mb-4">
      <label class="block text-sm text-gray-700 mb-1">Azienda</label>
      <input type="text" bind:value={azienda} placeholder="Nome azienda" required class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"/>
    </div>

    {#if isSuper}
      <div class="mb-4">
        <label class="block text-sm text-gray-700 mb-1">Email utente</label>
        <input type="text" min="1" bind:value={email_Id} placeholder="Email utente" class="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"/>
      </div>
    {/if}

    {#if error}
      <div class="text-sm text-red-600 mb-2">{error}</div>
    {:else if ok}
      <div class="text-sm text-green-600 mb-2">Trasferta creata.</div>
    {/if}

    <button type="submit" disabled={saving} class="w-full bg-gray-900 text-white rounded-lg p-2 text-sm hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed">
      {saving ? 'Salvataggio...' : 'Crea trasferta'}
    </button>
  </form>
</div>
