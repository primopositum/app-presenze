<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import AutoCard from '$lib/components/AutoCard.svelte';
  import ErrorCard from '$lib/components/ErrorCard.svelte';
  import GenericButtton from '$lib/components/GenericButtton.svelte';
  import ToastState from '$lib/components/ToastState.svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faPlus, faRotate } from '@fortawesome/free-solid-svg-icons';
  import {
    useAutomobiliList,
    useCreateAutomobile,
    useDeleteAutomobile,
    useUpdateAutomobile
  } from '$lib/hooks/useAutomobile';
  import type { Automobile, AutomobileCreate } from '$lib/services/automobili';
  import {
    getFavoriteAutomobileId,
    isFavoriteAutomobile,
    setFavoriteAutomobileId,
    sortFavoriteAutomobileFirst
  } from '$lib/services/automobilePreference';

  let items: Automobile[] = [];
  let loading = false;
  let showForm = false;
  let saving = false;
  let error: string | null = null;
  let isEdit = false;
  let selectedId: number | string | null = null;
  let bootstrapped = false;
  let isAuthed = false;
  let favoriteAutoId = '';
  let editingId = '';
  let savingEditId = '';
  let toastOpen = false;
  let toastSuccess = true;
  let toastMessage = '';

  let marca = '';
  let alimentazione = ''; 
  let descrizione = '';
  let coefficiente = '';
  let isActive = true;

  function getAutoId(a: Automobile): number | string | null {
    return a.id ?? a.a_id ?? a.A_ID ?? null;
  }

  function resetForm() {
    marca = '';
    alimentazione = '';
    descrizione = '';
    coefficiente = '';
    isActive = true;
    selectedId = null;
    isEdit = false;
  }

  function openCreate() {
    editingId = '';
    resetForm();
    showForm = true;
  }

  function closeForm() {
    if (saving) return;
    showForm = false;
  }

  function getErrorMessage(value: unknown, fallback: string) {
    if (value instanceof Error) return value.message || fallback;
    if (typeof value === 'string') return value || fallback;
    const message = (value as any)?.message;
    return typeof message === 'string' && message ? message : fallback;
  }

  function showToast(message: string, success = true) {
    toastSuccess = success;
    toastMessage = message;
    toastOpen = false;
    setTimeout(() => {
      toastOpen = true;
    }, 0);
  }

  function showError(value: unknown, fallback: string) {
    const message = getErrorMessage(value, fallback);
    error = message;
    showToast(message, false);
  }

  function openEdit(automobile: Automobile) {
    if (saving || savingEditId) return;
    const id = getAutoId(automobile);
    if (id === null) return;
    showForm = false;
    resetForm();
    editingId = String(id);
  }

  function cancelEdit() {
    if (savingEditId) return;
    editingId = '';
  }

  async function loadAutomobili(options: { notify?: boolean } = {}) {
    loading = true;
    error = null;
    try {
      const list = useAutomobiliList();
      const res = await list();
      favoriteAutoId = getFavoriteAutomobileId();
      items = sortFavoriteAutomobileFirst(res.payload, favoriteAutoId, getAutoId);
      if (options.notify) {
        showToast('Automobili aggiornate.');
      }
    } catch (e: any) {
      showError(e, 'Errore caricamento automobili');
    } finally {
      loading = false;
    }
  }

  async function handleDelete(automobile: Automobile) {
    const id = getAutoId(automobile);
    if (id === null || loading || savingEditId) return;
    try {
      loading = true;
      const remove = useDeleteAutomobile({ pk: id });
      await remove();
      if (String(id) === favoriteAutoId) {
        favoriteAutoId = '';
        setFavoriteAutomobileId(null);
      }
      await loadAutomobili();
      showToast('Automobile eliminata o archiviata correttamente.');
    } catch (e: any) {
      showError(e, 'Errore eliminazione automobile');
      loading = false;
    }
  }

  async function handleInlineSave(automobile: Automobile, payload: AutomobileCreate) {
    const id = getAutoId(automobile);
    if (id === null || savingEditId) return;

    savingEditId = String(id);
    error = null;
    try {
      const update = useUpdateAutomobile({ pk: id });
      const res = await update(payload);
      items = sortFavoriteAutomobileFirst(
        items.map((item) => (String(getAutoId(item)) === String(id) ? res.payload : item)),
        favoriteAutoId,
        getAutoId
      );
      editingId = '';
      showToast('Automobile aggiornata correttamente.');
    } catch (e: any) {
      showError(e, 'Errore salvataggio automobile');
    } finally {
      savingEditId = '';
    }
  }

  function handleFavorite(automobile: Automobile) {
    if (savingEditId) return;
    const id = getAutoId(automobile);
    if (id === null) return;
    favoriteAutoId = isFavoriteAutomobile(id, favoriteAutoId) ? '' : String(id);
    setFavoriteAutomobileId(favoriteAutoId || null);
    items = sortFavoriteAutomobileFirst(items, favoriteAutoId, getAutoId);
    showToast(favoriteAutoId ? 'Automobile impostata come preferita.' : 'Preferenza automobile rimossa.');
  }

  function handleBoundaryError(boundaryError: unknown) {
    showToast(getErrorMessage(boundaryError, 'Errore visualizzazione automobili'), false);
  }

  function handleCoefficienteInput(event: Event) {
    const target = event.currentTarget as HTMLInputElement | null;
    if (!target) return;
    coefficiente = target.value.replace(/,/g, '.');
  }

  async function submitForm() {
    error = null;
    if (!marca.trim() || !alimentazione.trim()) {
      showError('Marca e alimentazione sono obbligatori.', 'Marca e alimentazione sono obbligatori.');
      return;
    }

    const coefficienteValue = coefficiente.trim().replace(/,/g, '.') || 0;

    const payload: AutomobileCreate = {
      marca: marca.trim(),
      alimentazione: alimentazione.trim(),
      descrizione: descrizione.trim(),
      coefficiente: coefficienteValue,
      is_active: isActive
    };

    saving = true;
    try {
      if (isEdit && selectedId !== null) {
        const update = useUpdateAutomobile({ pk: selectedId });
        await update(payload);
        showToast('Automobile aggiornata correttamente.');
      } else {
        const create = useCreateAutomobile();
        await create(payload);
        showToast('Automobile creata correttamente.');
      }
      showForm = false;
      resetForm();
      await loadAutomobili();
    } catch (e: any) {
      showError(e, 'Errore salvataggio automobile');
    } finally {
      saving = false;
    }
  }

  function handleWindowKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && showForm) {
      closeForm();
    } else if (event.key === 'Escape' && editingId) {
      cancelEdit();
    }
  }

  $: isAuthed = $auth.isAuthed;
  $: if (isAuthed && !bootstrapped) {
    bootstrapped = true;
    void loadAutomobili();
  }
  $: if (!isAuthed) {
    bootstrapped = false;
  }

  $: if (typeof document !== 'undefined') {
    document.body.style.overflow = showForm ? 'hidden' : '';
  }

  onMount(() => {
    favoriteAutoId = getFavoriteAutomobileId();
    if (isAuthed && !bootstrapped) {
      bootstrapped = true;
      void loadAutomobili();
    }
  });
  onDestroy(() => {
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
    }
  });
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<div class="page">
  <p class="font-infinity tracking-[3px] text-center text-5xl">Automobili</p>

  <header class="topbar">
    <div class="actions">
      <GenericButtton color="#f97316" label="Nuova automobile" title="Nuova automobile" on:click={openCreate}>
        <FontAwesomeIcon icon={faPlus} class="text-base" />
      </GenericButtton>
      <GenericButtton
        color="#374151"
        label="Aggiorna automobili"
        title="Aggiorna automobili"
        on:click={() => loadAutomobili({ notify: true })}
      >
        <FontAwesomeIcon icon={faRotate} class="text-base" />
      </GenericButtton>
    </div>
  </header>

  <main class="content">
    <LoaderOverlay show={loading} />

    <svelte:boundary onerror={handleBoundaryError}>
      {#if loading}
        <p class="state">Caricamento...</p>
      {:else if items.length === 0}
        <p class="state">Nessuna automobile trovata</p>
      {:else}
        <section class="cars-pane">
          <ul class="list">
            {#each items as item, idx (`${item.id ?? item.a_id ?? item.A_ID ?? idx}`)}
              <AutoCard
                automobile={item}
                favorite={isFavoriteAutomobile(getAutoId(item), favoriteAutoId)}
                editing={getAutoId(item) !== null && String(getAutoId(item)) === editingId}
                saving={getAutoId(item) !== null && String(getAutoId(item)) === savingEditId}
                onDelete={handleDelete}
                onEdit={openEdit}
                onSave={handleInlineSave}
                onCancelEdit={cancelEdit}
                onFavorite={handleFavorite}
              />
            {/each}
          </ul>
        </section>
      {/if}

      {#snippet failed(boundaryError, reset)}
        <div class="error-shell">
          <ErrorCard
            message={getErrorMessage(boundaryError, 'Errore visualizzazione automobili')}
            onClose={reset}
          />
        </div>
      {/snippet}
    </svelte:boundary>
  </main>
</div>

{#if showForm}
  <div class="modal-backdrop" on:click={closeForm}>
    <div
      class="form-wrap modal-card"
      class:new-auto={!isEdit}
      role="dialog"
      aria-modal="true"
      on:click|stopPropagation
    >
      <h2>{isEdit ? 'Modifica automobile' : 'Nuova automobile'}</h2>
      <div class="form-grid">
        <input type="text" bind:value={marca} placeholder="Marca" />
        <input type="text" bind:value={alimentazione} placeholder="Alimentazione" />
        <input
          type="text"
          bind:value={coefficiente}
          placeholder="Coefficiente"
          on:input={handleCoefficienteInput}
        />
        <input type="text" bind:value={descrizione} placeholder="Descrizione" />
        <label class="check">
          <input type="checkbox" bind:checked={isActive} />
          is_active
        </label>
      </div>
      <div class="form-actions">
        <button class="ghost" type="button" on:click={closeForm}>Annulla</button>
        <button class="refresh" type="button" on:click={submitForm} disabled={saving}>
          {saving ? 'Salvataggio...' : 'Salva'}
        </button>
      </div>

    </div>
  </div>
{/if}

{#if error}
  <div class="error-backdrop">
    <button
      type="button"
      class="error-close-layer"
      aria-label="Chiudi errore"
      on:click={() => (error = null)}
    ></button>
    <div class="error-card-wrap">
      <ErrorCard message={error} onClose={() => (error = null)} />
    </div>
  </div>
{/if}

<ToastState bind:open={toastOpen} success={toastSuccess} message={toastMessage} />

<style>
  .page {
    background: var(--color-auto-bg);
    overscroll-behavior-y: contain;
  }

  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    min-height: 56px;
    color: var(--color-auto-text);
    border-bottom: 1px solid var(--color-auto-primary);
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .refresh {
    appearance: none;
    border: 1px solid var(--color-auto-border-strong);
    background: var(--color-auto-primary);
    color: var(--color-auto-primary-contrast);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .ghost {
    appearance: none;
    border: 1px solid var(--color-auto-border-strong);
    background: transparent;
    color: var(--color-auto-text);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .content {
    padding: 16px;
    display: grid;
    gap: 12px;
  }

  .form-wrap {
    width: min(100%, 460px);
    justify-self: center;
    background: var(--color-auto-panel-soft);
    border: 1px solid var(--color-auto-border);
    border-radius: 14px;
    padding: 14px;
    display: grid;
    gap: 12px;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  }

  .form-wrap h2 {
    margin: 0;
    font-size: 1rem;
    color: var(--color-auto-text);
  }

  .form-grid {
    display: grid;
    gap: 8px;
  }

  .form-grid input[type='text'] {
    border: 1px solid var(--color-auto-border);
    border-radius: 10px;
    padding: 9px 10px;
    font-size: 0.9rem;
  }

  .form-grid input[type='text']::placeholder {
    color: #9a3412;
    opacity: 0.7;
  }

  .check {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--color-auto-muted);
  }

  .form-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .state {
    text-align: center;
    color: var(--color-auto-muted);
    padding: 24px 8px;
  }

  .state.error {
    color: var(--color-auto-danger-700);
    padding: 8px;
  }

  .error-shell {
    display: grid;
    place-items: center;
    padding: 24px 8px;
  }

  .cars-pane {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--color-auto-border);
    border-radius: 12px;
    background: var(--color-auto-panel);
    overflow: hidden;
  }

  .cars-pane h2 {
    margin: 0;
    font-size: 1rem;
    color: var(--color-auto-text);
  }

  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 4px;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: var(--color-auto-overlay);
    display: grid;
    place-items: center;
    padding: 16px;
    z-index: 1000;
  }

  .modal-card {
    width: min(520px, 100%);
    max-height: calc(100vh - 32px);
    overflow: auto;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.28);
  }

  .error-backdrop {
    position: fixed;
    inset: 0;
    z-index: 2100;
    display: grid;
    place-items: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.5);
  }

  .error-close-layer {
    position: absolute;
    inset: 0;
    border: 0;
    background: transparent;
    cursor: default;
  }

  .error-card-wrap {
    position: relative;
    z-index: 1;
  }

  .form-wrap.new-auto {
    background: var(--color-auto-accent-50);
    border-color: var(--color-auto-accent-200);
    color: #7c2d12;
    box-shadow: 0 20px 40px rgba(249, 115, 22, 0.18);
    color-scheme: light;
  }

  .form-wrap.new-auto h2 {
    color: #c2410c;
  }

  .form-wrap.new-auto .form-grid input[type='text'] {
    background: #ffffff;
    border-color: var(--color-auto-accent-200);
    color: #7c2d12;
  }

  .form-wrap.new-auto .form-grid input[type='text']:focus {
    border-color: var(--color-auto-accent-500);
    outline: none;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2);
  }

  .form-wrap.new-auto .check {
    color: #9a3412;
  }

  .form-wrap.new-auto .ghost {
    background: #ffffff;
    border-color: var(--color-auto-accent-200);
    color: #c2410c;
  }

  .form-wrap.new-auto .ghost:hover {
    background: var(--color-auto-accent-100);
  }

  .form-wrap.new-auto .refresh {
    border-color: var(--color-auto-accent-500);
    background: var(--color-auto-accent-500);
    color: #ffffff;
  }

  .form-wrap.new-auto .refresh:hover {
    background: #ea580c;
    border-color: #ea580c;
  }

  @media (max-width: 980px) {
    .list {
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      max-height: 52vh;
      flex: unset;
    }
  }

  @media (max-width: 520px) {
    .list {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 520px) {
    .topbar {
      padding: 12px;
    }
    .content {
      padding: 12px;
    }
  }
</style>

