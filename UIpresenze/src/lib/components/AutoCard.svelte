<script lang="ts">
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faTrash, faPenToSquare, faCar, faStar, faCheck, faXmark } from '@fortawesome/free-solid-svg-icons';
  import type { Automobile, AutomobileCreate } from '$lib/services/automobili';
  import LoadReceipts from '$lib/components/LoadReceipts.svelte';

  export let automobile: Automobile;
  export let onDelete: ((automobile: Automobile) => void) | undefined;
  export let onEdit: ((automobile: Automobile) => void) | undefined;
  export let onSave: ((automobile: Automobile, payload: AutomobileCreate) => void | Promise<void>) | undefined;
  export let onCancelEdit: (() => void) | undefined;
  export let onFavorite: ((automobile: Automobile) => void) | undefined;
  export let favorite = false;
  export let editing = false;
  export let saving = false;
const handleNavigation = () => {
    if (editing || saving) return;
    const url = "https://iam.aci.it/auth/realms/Cittadini/protocol/openid-connect/auth?client_id=CostiChilometrici_WEB&redirect_uri=https%3A%2F%2Fcostikm.aci.it&state=503cec0d-8574-43f6-84f4-d5191b331511&response_mode=fragment&response_type=code&scope=openid&nonce=dbc044a4-b191-41e7-80aa-666e9a58ff19";
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  let draftMarca = '';
  let draftAlimentazione = '';
  let draftDescrizione = '';
  let draftCoefficiente = '';
  let draftIsActive = true;
  let localError: string | null = null;
  let lastDraftKey = '';

  function getAutoId(a: Automobile): number | string | null {
    return a.id ?? a.a_id ?? a.A_ID ?? null;
  }

  $: autoId = getAutoId(automobile);
  $: draftKey = `${autoId ?? ''}|${automobile.marca ?? ''}|${automobile.alimentazione ?? ''}|${automobile.descrizione ?? ''}|${automobile.coefficiente ?? ''}|${automobile.is_active ? '1' : '0'}`;
  $: if (editing && draftKey !== lastDraftKey) {
    syncDraft();
    lastDraftKey = draftKey;
  }
  $: if (!editing) {
    lastDraftKey = '';
    localError = null;
  }

  function syncDraft() {
    draftMarca = automobile.marca || '';
    draftAlimentazione = automobile.alimentazione || '';
    draftDescrizione = automobile.descrizione || '';
    draftCoefficiente = String(automobile.coefficiente ?? '');
    draftIsActive = !!automobile.is_active;
  }

  function handleCoefficienteInput(event: Event) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target) return;
    draftCoefficiente = target.value.replace(/,/g, '.');
  }

  async function handleSave() {
    if (saving) return;
    localError = null;
    if (!draftMarca.trim() || !draftAlimentazione.trim()) {
      localError = 'Marca e alimentazione sono obbligatori.';
      return;
    }

    const payload: AutomobileCreate = {
      marca: draftMarca.trim(),
      alimentazione: draftAlimentazione.trim(),
      descrizione: draftDescrizione.trim(),
      coefficiente: draftCoefficiente.trim().replace(/,/g, '.') || 0,
      is_active: draftIsActive
    };

    await onSave?.(automobile, payload);
  }
</script> 

<li
  class="auto-card mx-auto w-full max-w-[320px] rounded-2xl border p-4 shadow-[0_8px_24px_rgba(14,165,233,0.2)] transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(14,165,233,0.28)]"
  class:editing
>
  <div class="mb-3 flex items-start justify-between gap-2">
    <div class="min-w-0">
      {#if editing}
        <input
          class="auto-title-input"
          bind:value={draftMarca}
          disabled={saving}
          aria-label="Marca automobile"
        />
        <label class="auto-active-toggle">
        <!-- todo: in editmode lasciare attiva uguale a come è normalmente e permettere di cliccarci sopra per cambiarla, invece di mostrarla come un campo a parte -->
          <input type="checkbox" bind:checked={draftIsActive} disabled={saving} />
          Attiva
        </label>
      {:else}
        <h3 class="truncate text-[0.95rem] font-semibold text-white">{automobile.marca}</h3>
        <span
          class={`mt-1 inline-flex items-center rounded-full px-2.5 py-1 text-[0.68rem] font-semibold ${
            automobile.is_active
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-rose-100 text-rose-700'
          }`}
        >
          {automobile.is_active ? 'Attiva' : 'Archiviata'}
        </span>
      {/if}
    </div>

    <div class="flex shrink-0 gap-1.5">
 <button
      type="button"
      on:click={handleNavigation}
      class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border border-gray-300 bg-white text-[1rem] leading-none transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      disabled={editing || saving}
      aria-label="Apri costi chilometrici ACI"
      title="Costi chilometrici ACI"
    >
      <FontAwesomeIcon icon={faCar} />
    </button>
      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-200"
        class:border-yellow-300={favorite}
        class:bg-yellow-100={favorite}
        class:text-yellow-600={favorite}
        class:border-auto-accent-200={!favorite}
        class:bg-white={!favorite}
        class:text-auto-accent-700={!favorite}
        class:hover:bg-yellow-50={!favorite}
        on:click={() => onFavorite?.(automobile)}
        disabled={editing || saving}
        aria-label={favorite ? 'Automobile preferita' : 'Imposta automobile preferita'}
        aria-pressed={favorite}
        title={favorite ? 'Automobile preferita' : 'Imposta come preferita'}
      >
        <FontAwesomeIcon icon={faStar} class="text-xs" />
      </button>
      {#if editing}
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 transition-all duration-200 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
          on:click={handleSave}
          disabled={saving}
          aria-label="Salva automobile"
          title="Salva"
        >
          <FontAwesomeIcon icon={faCheck} class="text-xs" />
        </button>
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-orange-200 bg-white/90 text-orange-700 transition-all duration-200 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-60"
          on:click={() => onCancelEdit?.()}
          disabled={saving}
          aria-label="Annulla modifica automobile"
          title="Annulla"
        >
          <FontAwesomeIcon icon={faXmark} class="text-xs" />
        </button>
      {:else}
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/60 bg-white/90 text-primary transition-all duration-200 hover:bg-white"
          on:click={() => onEdit?.(automobile)}
          aria-label="Modifica automobile"
          title="Modifica"
        >
          <FontAwesomeIcon icon={faPenToSquare} class="text-xs" />
        </button>
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/60 bg-white/90 text-primary transition-all duration-200 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
          on:click={() => onDelete?.(automobile)}
          aria-label="Elimina automobile"
          title="Elimina"
        >
          <FontAwesomeIcon icon={faTrash} class="text-xs" />
        </button>
      {/if}
    </div>
  </div>

  <div class="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2">
    <div class="auto-field-box" class:editing>
      <span class="block text-[0.65rem] font-semibold uppercase text-black/60">Alimentazione</span>
      {#if editing}
        <input
          class="auto-edit-input"
          bind:value={draftAlimentazione}
          disabled={saving}
          aria-label="Alimentazione automobile"
        />
      {:else}
        <span class="auto-field-value mt-0.5 block font-semibold text-black">
          {automobile.alimentazione || '-'}
        </span>
      {/if}
    </div>
    <div class="auto-field-box" class:editing>
      <span class="block text-[0.65rem] font-semibold uppercase text-black/60">Coefficiente</span>
      {#if editing}
        <input
          class="auto-edit-input"
          value={draftCoefficiente}
          disabled={saving}
          aria-label="Coefficiente automobile"
          on:input={handleCoefficienteInput}
        />
      {:else}
        <span class="auto-field-value mt-0.5 block font-semibold text-black">
          {automobile.coefficiente ?? '-'}
        </span>
      {/if}
    </div>
    <div class="auto-field-box sm:col-span-2" class:editing>
      <span class="block text-[0.65rem] font-semibold uppercase text-black/60">Descrizione</span>
      {#if editing}
        <textarea
          class="auto-edit-input auto-edit-textarea"
          bind:value={draftDescrizione}
          disabled={saving}
          aria-label="Descrizione automobile"
        ></textarea>
      {:else}
        <span class="auto-field-value mt-0.5 block font-semibold text-black">
          {automobile.descrizione || '-'}
        </span>
      {/if}
    </div>
    <!-- <div><span class="text-auto-accent-700/75">Creata:</span> {automobile.data_creaz}</div>
    <div><span class="text-auto-accent-700/75">Aggiornata:</span> {automobile.data_upd}</div> -->
  </div>

  {#if localError}
    <p class="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
      {localError}
    </p>
  {/if}

  {#if autoId !== null}
    <div class="mt-4 border-t border-white/30 pt-3">
      <LoadReceipts mode="auto" autoId={autoId} disabled={editing} />
    </div>
  {/if}
</li>

<style>
  .auto-card {
    container-type: inline-size;
    background: var(--color-primary);
    border-color: var(--color-primary);
  }

  .auto-card.editing {
    background: var(--color-secondary);
    border-color: var(--color-secondary);
    box-shadow: 0 14px 32px rgba(249, 115, 22, 0.26);
  }

  .auto-field-box {
    min-height: 82px;
    min-width: 0;
    overflow: hidden;
    border-radius: 0.75rem;
    border: 1px solid var(--color-auto-field-border);
    background: var(--color-auto-field-bg);
    padding: 0.75rem 1rem;
  }

  .auto-field-box.editing {
    border-color: var(--color-auto-edit-field-border);
    background: var(--color-auto-edit-field-bg);
  }

  .auto-title-input,
  .auto-edit-input {
    width: 100%;
    min-width: 0;
    border: 1px solid var(--color-auto-edit-field-border);
    border-radius: 0.65rem;
    background: var(--color-auto-edit-field-bg);
    color: var(--color-auto-edit-text);
    font-weight: 700;
    line-height: 1.2;
  }

  .auto-title-input {
    padding: 0.42rem 0.6rem;
    font-size: 0.9rem;
  }

  .auto-edit-input {
    margin-top: 0.25rem;
    padding: 0.45rem 0.55rem;
    font-size: 0.85rem;
  }

  .auto-edit-textarea {
    min-height: 4.6rem;
    resize: vertical;
  }

  .auto-title-input:focus,
  .auto-edit-input:focus {
    border-color: var(--color-auto-accent-500);
    outline: none;
    box-shadow: 0 0 0 3px var(--color-auto-edit-field-focus);
  }

  .auto-active-toggle {
    margin-top: 0.4rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    border-radius: 999px;
    background: var(--color-auto-edit-field-bg);
    padding: 0.3rem 0.55rem;
    color: var(--color-auto-edit-text);
    font-size: 0.72rem;
    font-weight: 700;
  }

  .auto-field-value {
    max-width: 100%;
    min-width: 0;
    overflow-wrap: anywhere;
    word-break: break-word;
    line-height: 1.2;
    font-size: clamp(0.72rem, 4.5cqw, 0.95rem);
  }
</style>
