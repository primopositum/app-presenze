<script lang="ts">
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faTrash, faPenToSquare } from '@fortawesome/free-solid-svg-icons';
  import type { Automobile } from '$lib/services/automobili';

  export let automobile: Automobile;
  export let onDelete: ((automobile: Automobile) => void) | undefined;
  export let onEdit: ((automobile: Automobile) => void) | undefined;

  function getAutoId(a: Automobile): number | string {
    return a.id ?? a.a_id ?? a.A_ID ?? '-';
  }
</script>

<li
  class="mx-auto w-full max-w-[320px] rounded-2xl border border-auto-accent-200 bg-gradient-to-br from-auto-accent-50 via-auto-accent-100 to-auto-accent-200 p-4 shadow-[0_8px_24px_rgba(194,65,12,0.14)] transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(194,65,12,0.2)]"
>
  <div class="mb-3 flex items-start justify-between gap-2">
    <div class="min-w-0">
      <h3 class="truncate text-[0.95rem] font-semibold text-auto-accent-700">{automobile.marca}</h3>
      <span
        class={`mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-[0.68rem] font-semibold ${
          automobile.is_active
            ? 'bg-emerald-100 text-emerald-700'
            : 'bg-rose-100 text-rose-700'
        }`}
      >
        {automobile.is_active ? 'Attiva' : 'Archiviata'}
      </span>
    </div>

    <div class="flex shrink-0 gap-1.5">
      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-auto-accent-200 bg-white/80 text-auto-accent-700 transition-all duration-200 hover:bg-white hover:text-auto-accent-700"
        on:click={() => onEdit?.(automobile)}
        aria-label="Modifica automobile"
        title="Modifica"
      >
        <FontAwesomeIcon icon={faPenToSquare} class="text-xs" />
      </button>
      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-auto-accent-200 bg-white/80 text-auto-accent-700 transition-all duration-200 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
        on:click={() => onDelete?.(automobile)}
        aria-label="Elimina automobile"
        title="Elimina"
      >
        <FontAwesomeIcon icon={faTrash} class="text-xs" />
      </button>
    </div>
  </div>

  <div class="grid gap-1.5 text-[0.8rem] text-auto-accent-700/85">
    <div><span class="text-auto-accent-700/75">ID:</span> {getAutoId(automobile)}</div>
    <div><span class="text-auto-accent-700/75">Alimentazione:</span> {automobile.alimentazione}</div>
    <div><span class="text-auto-accent-700/75">Coefficiente:</span> {automobile.coefficiente}</div>
    <div><span class="text-auto-accent-700/75">Descrizione:</span> {automobile.descrizione || '-'}</div>
    <div><span class="text-auto-accent-700/75">Creata:</span> {automobile.data_creaz}</div>
    <div><span class="text-auto-accent-700/75">Aggiornata:</span> {automobile.data_upd}</div>
  </div>
</li>
