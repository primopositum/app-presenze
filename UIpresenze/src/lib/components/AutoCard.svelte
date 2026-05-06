<script lang="ts">
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faTrash, faPenToSquare, faCar } from '@fortawesome/free-solid-svg-icons';
  import type { Automobile } from '$lib/services/automobili';
  import LoadReceipts from '$lib/components/LoadReceipts.svelte';

  export let automobile: Automobile;
  export let onDelete: ((automobile: Automobile) => void) | undefined;
  export let onEdit: ((automobile: Automobile) => void) | undefined;
const handleNavigation = () => {
    const url = "https://iam.aci.it/auth/realms/Cittadini/protocol/openid-connect/auth?client_id=CostiChilometrici_WEB&redirect_uri=https%3A%2F%2Fcostikm.aci.it&state=503cec0d-8574-43f6-84f4-d5191b331511&response_mode=fragment&response_type=code&scope=openid&nonce=dbc044a4-b191-41e7-80aa-666e9a58ff19";
    window.open(url, '_blank', 'noopener,noreferrer');
  };
  function getAutoId(a: Automobile): number | string | null {
    return a.id ?? a.a_id ?? a.A_ID ?? null;
  }

  $: autoId = getAutoId(automobile);
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
      on:click={handleNavigation}
      class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border border-gray-300 bg-white text-[1rem] leading-none transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      aria-label="Apri costi chilometrici ACI"
      title="Costi chilometrici ACI"
    >
      <FontAwesomeIcon icon={faCar} />
    </button>
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
    <div><span class="text-auto-accent-700/75">ID:</span> {autoId ?? '-'}</div>
    <div><span class="text-auto-accent-700/75">Alimentazione:</span> {automobile.alimentazione}</div>
    <div><span class="text-auto-accent-700/75">Coefficiente:</span> {automobile.coefficiente}</div>
    <div><span class="text-auto-accent-700/75">Descrizione:</span> {automobile.descrizione || '-'}</div>
    <!-- <div><span class="text-auto-accent-700/75">Creata:</span> {automobile.data_creaz}</div>
    <div><span class="text-auto-accent-700/75">Aggiornata:</span> {automobile.data_upd}</div> -->
  </div>

  {#if autoId !== null}
    <div class="mt-4 border-t border-auto-accent-200 pt-3">
      <LoadReceipts mode="auto" autoId={autoId} />
    </div>
  {/if}
</li>
