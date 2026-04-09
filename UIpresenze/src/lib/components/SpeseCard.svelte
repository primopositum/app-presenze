<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faTrash } from '@fortawesome/free-solid-svg-icons';
  import type { Spesa } from '$lib/services/trasferte';
  import { useDeleteSpese } from '$lib/hooks/useTrasferte';

  export let spesa: Spesa;
  export let readonly = false;
  let loading = false;

  const dispatch = createEventDispatcher<{ delete: Spesa }>();
  const types: Record<number, string> = {
    1: 'Pedaggi',
    2: 'Rimborso km',
    3: 'Ristoranti',
    4: 'Albergo',
    5: 'Parcheggi',
    6: 'Aerei/treni',
    7: 'Altro'
  };

  async function handleDelete(spesa: Spesa) {
    let error: string | null = null;
    try {
      loading = true;
      const deleteSpese = useDeleteSpese({ sId: spesa.id });
      await deleteSpese();
    } catch (e: any) {
      error = e?.message || 'Errore cancellazione';
    } finally {
      loading = false;
    }
    if (!error) {
      dispatch('delete', spesa);
    }
  }

  $: typeLabel = types[Number(spesa.type)] ?? String(spesa.type);
  $: tragittoLabel =
    Number(spesa.type) === 2 && Array.isArray(spesa.tragitto) && spesa.tragitto.length > 0
      ? spesa.tragitto.join(' / ')
      : null;
</script>

<article class="flex items-center justify-between gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm">
  <div class="flex flex-wrap gap-2">
    <span>Spesa per {typeLabel}</span>
    <span>importo: {spesa.importo} &euro;</span>
    {#if tragittoLabel}
      <span>tragitto: {tragittoLabel}</span>
    {/if}
  </div>
  {#if !readonly}
    <button
      type="button"
      class="shrink-0 h-8 w-8 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50 flex items-center justify-center"
      on:click={() => handleDelete(spesa)}
      aria-label="Elimina spesa"
      title="Elimina"
      disabled={loading}
    >
      <FontAwesomeIcon icon={faTrash} class="text-sm text-slate-600" />
    </button>
  {/if}
</article>

