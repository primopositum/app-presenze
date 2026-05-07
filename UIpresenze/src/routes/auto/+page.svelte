<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import AutoCard from '$lib/components/AutoCard.svelte';
  import {
    useAutomobiliList,
    useCreateAutomobile,
    useDeleteAutomobile,
    useUpdateAutomobile
  } from '$lib/hooks/useAutomobile';
  import type { Automobile, AutomobileCreate } from '$lib/services/automobili';

  let items: Automobile[] = [];
  let loading = false;
  let showForm = false;
  let saving = false;
  let error: string | null = null;
  let isEdit = false;
  let selectedId: number | string | null = null;
  let bootstrapped = false;
  let isAuthed = false;

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
    resetForm();
    showForm = true;
  }

  function closeForm() {
    if (saving) return;
    showForm = false;
  }

  function openEdit(automobile: Automobile) {
    selectedId = getAutoId(automobile);
    if (selectedId === null) return;
    isEdit = true;
    marca = automobile.marca || '';
    alimentazione = automobile.alimentazione || '';
    descrizione = automobile.descrizione || '';
    coefficiente = String(automobile.coefficiente ?? '');
    isActive = !!automobile.is_active;
    showForm = true;
  }

  async function loadAutomobili() {
    loading = true;
    error = null;
    try {
      const list = useAutomobiliList();
      const res = await list();
      items = res.payload;
    } catch (e: any) {
      error = e?.message || 'Errore caricamento automobili';
    } finally {
      loading = false;
    }
  }

  async function handleDelete(automobile: Automobile) {
    const id = getAutoId(automobile);
    if (id === null || loading) return;
    try {
      loading = true;
      const remove = useDeleteAutomobile({ pk: id });
      await remove();
      await loadAutomobili();
    } catch (e: any) {
      error = e?.message || 'Errore eliminazione automobile';
      loading = false;
    }
  }

  async function submitForm() {
    error = null;
    if (!marca.trim() || !alimentazione.trim()) {
      error = 'Marca e alimentazione sono obbligatori.';
      return;
    }

    const coefficienteValue = coefficiente.trim() || 0;

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
      } else {
        const create = useCreateAutomobile();
        await create(payload);
      }
      showForm = false;
      resetForm();
      await loadAutomobili();
    } catch (e: any) {
      error = e?.message || 'Errore salvataggio automobile';
    } finally {
      saving = false;
    }
  }

  function handleWindowKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && showForm) {
      closeForm();
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
      <button class="ghost" type="button" on:click={openCreate}>+</button>
      <button class="refresh" type="button" on:click={loadAutomobili}>Aggiorna</button>
    </div>
  </header>

  <main class="content">
    <LoaderOverlay show={loading} />

    {#if error}
      <p class="state error">{error}</p>
    {/if}

    {#if loading}
      <p class="state">Caricamento...</p>
    {:else if items.length === 0}
      <p class="state">Nessuna automobile trovata</p>
    {:else}
      <section class="cars-pane">
        <ul class="list">
          {#each items as item, idx (`${item.id ?? item.a_id ?? item.A_ID ?? idx}`)}
            <AutoCard automobile={item} onDelete={handleDelete} onEdit={openEdit} />
          {/each}
        </ul>
      </section>
    {/if}
  </main>
</div>

{#if showForm}
  <div class="modal-backdrop" on:click={closeForm}>
    <div class="form-wrap modal-card" role="dialog" aria-modal="true" on:click|stopPropagation>
      <h2>{isEdit ? 'Modifica automobile' : 'Nuova automobile'}</h2>
      <div class="form-grid">
        <input type="text" bind:value={marca} placeholder="Marca" />
        <input type="text" bind:value={alimentazione} placeholder="Alimentazione" />
        <input type="text" bind:value={coefficiente} placeholder="Coefficiente" />
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

<style>
  .page {
    background: var(--color-auto-bg);
    overscroll-behavior-y: contain;
  }

  .topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    min-height: 56px;
    background: var(--color-auto-bg-soft);
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

