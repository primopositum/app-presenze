<script lang="ts">
  import { onMount } from 'svelte';
  import {
    useClienteDelete,
    useClienteUpdate,
    useContrattoClienteDelete,
    useContrattoClientePoolTaskAppend,
    useContrattoClientePoolTaskDelete
  } from '$lib/hooks/useClienti';
  import type { Cliente, ContrattoCliente } from '$lib/services/clienti';
  import { contractProfitability, tasksByKey } from '$lib/components/charts/contractsSelectors';
  import {
    chartsData,
    ensureContrattiLoaded,
    removeCliente,
    removeContratto,
    replaceContratto
  } from '$lib/remo/chartsData';
  import ClientiCreateCards from '$lib/components/Jira/ClientiCreateCards.svelte';
  import ContractListItem from '$lib/components/Jira/ContractListItem.svelte';
  import ContractTaskPool from '$lib/components/Jira/ContractTaskPool.svelte';
  import EditContrattoModal from '$lib/components/Jira/EditContrattoModal.svelte';
  import DeleteConfirmCard from '$lib/components/DeleteConfirmCard.svelte';
  import ToastState from '$lib/components/ToastState.svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faChevronDown, faChevronUp } from '@fortawesome/free-solid-svg-icons';

  type ClientSortDirection = 'asc' | 'desc' | null;
  type DeleteTarget =
    | { type: 'cliente'; cliente: Cliente }
    | { type: 'contratto'; contratto: ContrattoCliente };

  type ClienteForm = { id: number | null; nome: string; indirizzo: string; telefono: string };

  const emptyClienteForm = (): ClienteForm => ({ id: null, nome: '', indirizzo: '', telefono: '' });

  // Clienti, contratti e task Jira arrivano dallo store condiviso /remo: la
  // schermata contratti del cubo legge esattamente gli stessi dati.
  $: clienti = $chartsData.clienti as Cliente[];
  $: contratti = $chartsData.contratti as ContrattoCliente[];
  $: jiraTasks = $chartsData.poolTasks;
  // Prima carica: non c'e' ancora niente da mostrare. Una ricarica successiva
  // tiene la lista a schermo, altrimenti ogni aggiornamento la farebbe sparire.
  $: loading = !$chartsData.contrattiLoaded;
  $: refreshing = $chartsData.contrattiRefreshing;

  let contractSearch = '';
  let clientSortDirection: ClientSortDirection = null;
  let savingCliente = false;
  let toastOpen = false;
  let toastSuccess = true;
  let toastMessage = '';
  let clienteForm = emptyClienteForm();
  let editingContrattoId: number | null = null;
  let poolTaskInputs: Record<number, string> = {};
  let listsOpen = false;
  let creating = false;
  let selectedContrattoId: number | null = null;
  let deleteTarget: DeleteTarget | null = null;
  let deleting = false;

  $: selectedContratto = contratti.find((contratto) => contratto.id === selectedContrattoId) || null;
  $: editingContratto = contratti.find((contratto) => contratto.id === editingContrattoId) || null;
  $: normalizedContractSearch = contractSearch.trim().toLowerCase();
  $: filteredContracts = contratti.filter((contratto) => {
    if (!normalizedContractSearch) return true;
    return [
      contratto.contract_id,
      contractClientName(contratto),
      contratto.start_date,
      contratto.end_date || '',
      ...(contratto.pool_task || [])
    ].some((value) => String(value).toLowerCase().includes(normalizedContractSearch));
  });
  $: sortedContracts = clientSortDirection
    ? [...filteredContracts].sort((first, second) => {
        const comparison = contractClientName(first).localeCompare(contractClientName(second), 'it', {
          sensitivity: 'base'
        });
        return clientSortDirection === 'asc' ? comparison : -comparison;
      })
    : filteredContracts;
  // Ore e quote di valore del pool: e' lo stesso calcolo che alimenta i grafici
  // di redditivita', quindi vive una volta sola nei selettori dei contratti.
  $: jiraTasksByKey = tasksByKey(jiraTasks);
  $: selectedPoolTaskRows = selectedContratto
    ? contractProfitability(selectedContratto, jiraTasksByKey).tasks
    : [];
  $: selectedPoolTaskTotalSeconds = selectedPoolTaskRows.reduce((total, task) => total + task.seconds, 0);

  function formatHours(seconds: number) {
    const hours = seconds / 3600;
    return `${hours.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} h`;
  }

  function formatCurrency(value: number) {
    return value.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' });
  }

  function contractDisplayValue(contratto: ContrattoCliente): number {
    const currentValueText = String(contratto.current_value ?? '').trim();
    const currentValue = Number(currentValueText);
    if (currentValueText && Number.isFinite(currentValue)) return currentValue;

    return contractSignedValue(contratto);
  }

  function contractSignedValue(contratto: ContrattoCliente): number {
    const signedValueText = String(contratto.value ?? '').trim();
    const signedValue = Number(signedValueText);
    return signedValueText && Number.isFinite(signedValue) ? signedValue : 0;
  }

  function contractClientName(contratto: ContrattoCliente) {
    return contratto.client?.nome || 'Cliente non disponibile';
  }

  function toggleClientSort() {
    clientSortDirection = clientSortDirection === 'asc' ? 'desc' : 'asc';
  }

  function clientSortDescription() {
    return clientSortDirection === 'asc'
      ? 'Ordina i clienti dalla Z alla A'
      : 'Ordina i clienti dalla A alla Z';
  }

  async function loadData(force = true) {
    try {
      await ensureContrattiLoaded(force);
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile caricare clienti e contratti.'), false);
    }
  }

  function showToast(message: string, success = true) {
    toastSuccess = success;
    toastMessage = message;
    toastOpen = false;
    requestAnimationFrame(() => {
      toastOpen = true;
    });
  }

  async function handleCreated() {
    await loadData();
  }

  async function saveCliente() {
    savingCliente = true;
    try {
      const payload = {
        nome: clienteForm.nome.trim(),
        indirizzo: clienteForm.indirizzo.trim(),
        telefono: clienteForm.telefono.trim()
      };
      if (!payload.nome) throw new Error('Il nome del cliente è obbligatorio.');

      if (clienteForm.id === null) return;
      await useClienteUpdate(clienteForm.id, payload);

      clienteForm = emptyClienteForm();
      showToast('Cliente salvato.');
      await loadData();
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile salvare il cliente.'), false);
    } finally {
      savingCliente = false;
    }
  }

  function editCliente(cliente: Cliente) {
    clienteForm = { ...cliente };
  }

  function requestDeleteCliente(cliente: Cliente) {
    deleteTarget = { type: 'cliente', cliente };
  }

  function requestDeleteContratto(contratto: ContrattoCliente) {
    deleteTarget = { type: 'contratto', contratto };
  }

  function closeDeleteConfirmation() {
    if (!deleting) deleteTarget = null;
  }

  function deleteConfirmationMessage(target: DeleteTarget) {
    return target.type === 'cliente'
      ? `Sei veramente sicuro di eliminare il cliente ${target.cliente.nome}? Se lo elimini perderai il valore delle task associate.`
      : `Sei veramente sicuro di eliminare il contratto per ${contractClientName(target.contratto)}? Se lo elimini perderai il valore delle task associate.`;
  }

  /**
   * Elimina e basta: appena il server conferma si toglie la voce dalla memoria
   * condivisa, senza ricaricare tutto.
   *
   * Una ricarica completa svuotava clienti, contratti e grafici per il tempo
   * della richiesta, e la pagina lampeggiava in bianco a ogni eliminazione.
   */
  async function confirmDelete() {
    if (!deleteTarget) return;
    const target = deleteTarget;
    deleting = true;
    try {
      if (target.type === 'cliente') {
        await useClienteDelete(target.cliente.id);
        if (clienteForm.id === target.cliente.id) clienteForm = emptyClienteForm();
        removeCliente(target.cliente.id);
        showToast('Cliente eliminato.');
      } else {
        await useContrattoClienteDelete(target.contratto.id);
        if (editingContrattoId === target.contratto.id) editingContrattoId = null;
        if (selectedContrattoId === target.contratto.id) selectedContrattoId = null;
        removeContratto(target.contratto.id);
        showToast('Contratto commerciale eliminato.');
      }
      deleteTarget = null;
    } catch (cause: any) {
      const fallback =
        target.type === 'cliente'
          ? 'Impossibile eliminare il cliente.'
          : 'Impossibile eliminare il contratto.';
      showToast(String(cause?.message || cause || fallback), false);
    } finally {
      deleting = false;
    }
  }

  function editContratto(contratto: ContrattoCliente) {
    editingContrattoId = contratto.id;
  }

  function closeEditContratto() {
    editingContrattoId = null;
  }

  function selectContratto(contratto: ContrattoCliente) {
    selectedContrattoId = contratto.id;
  }

  async function appendTask(contratto: ContrattoCliente) {
    const task = String(poolTaskInputs[contratto.id] || '').trim();
    try {
      const updated = await useContrattoClientePoolTaskAppend(contratto.id, task);
      replaceContratto(updated);
      poolTaskInputs = { ...poolTaskInputs, [contratto.id]: '' };
      showToast('Task aggiunta al pool.');
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile aggiungere la task.'), false);
    }
  }

  async function deleteTask(contratto: ContrattoCliente, task: string) {
    try {
      const updated = await useContrattoClientePoolTaskDelete(contratto.id, task);
      replaceContratto(updated);
      showToast('Task rimossa dal pool.');
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile rimuovere la task.'), false);
    }
  }

  function setPoolTaskInput(contractId: number, value: string) {
    poolTaskInputs = { ...poolTaskInputs, [contractId]: value };
  }

  onMount(() => {
    void loadData(false);
  });
</script>

<section class="clienti-section" data-history-hover data-history-hover-exclude={creating || undefined}>
  <header class="section-header">
    <div>
      <h2>Clienti e contratti commerciali</h2>
      <p>Gestisci anagrafiche, valori contrattuali e pool di task Jira.</p>
    </div>
    <button type="button" class="refresh-button" on:click={() => loadData()} disabled={loading || refreshing}>
      {refreshing ? 'Aggiorno...' : 'Aggiorna'}
    </button>
  </header>

  <ClientiCreateCards
    {clienti}
    onCreated={handleCreated}
    onOpen={() => (creating = true)}
    onClosed={() => (creating = false)}
    onNotify={showToast}
  />

  {#if clienteForm.id !== null}
  <div class="editor-grid">
    {#if clienteForm.id !== null}<form class="editor-card" on:submit|preventDefault={saveCliente}>
      <h3>Modifica cliente</h3>
      <label>Nome <input bind:value={clienteForm.nome} required /></label>
      <label>Indirizzo <input bind:value={clienteForm.indirizzo} /></label>
      <label>Telefono <input bind:value={clienteForm.telefono} /></label>
      <div class="form-actions">
        <button type="submit" disabled={savingCliente}>{savingCliente ? 'Salvo...' : 'Salva cliente'}</button>
        <button type="button" class="secondary" on:click={() => (clienteForm = emptyClienteForm())}>Annulla</button>
      </div>
    </form>{/if}
  </div>
  {/if}

  <button type="button" class="list-toggle" on:click={() => (listsOpen = !listsOpen)} aria-expanded={listsOpen}>
    <span class="toggle-icon">
      {#if listsOpen}<FontAwesomeIcon icon={faChevronUp} />{:else}<FontAwesomeIcon icon={faChevronDown} />{/if}
    </span>
    Contratti esistenti ({contratti.length})
  </button>

  {#if listsOpen}
  <div class="data-grid" class:stale={refreshing}>
    <aside class="contracts-tools">
      <h3>Cerca contratti</h3>
      <label class="search-label" for="contracts-search">Ricerca</label>
      <input
        id="contracts-search"
        class="contracts-search"
        bind:value={contractSearch}
        placeholder="ID, cliente, data o task Jira"
      />
      <div class="sort-bar">
        <span>Ordina per</span>
        <button
          type="button"
          class="sort-client-button"
          class:sort-desc={clientSortDirection === 'desc'}
          aria-label={clientSortDescription()}
          aria-pressed={clientSortDirection !== null}
          on:click={toggleClientSort}
        >
          Aa
          <span class="sort-tooltip" role="tooltip">{clientSortDescription()}</span>
        </button>
      </div>
      <p>{filteredContracts.length} di {contratti.length} contratti</p>
    </aside>

    <article class="list-card contracts-card">
      <h3>Contratti ({filteredContracts.length})</h3>
      {#if loading}<p>Caricamento...</p>
      {:else if contratti.length === 0}<p>Nessun contratto commerciale presente.</p>
      {:else if filteredContracts.length === 0}<p>Nessun contratto corrisponde alla ricerca.</p>
      {:else}
        <div class="contracts-list">
          {#each sortedContracts as contratto (contratto.id)}
            <ContractListItem
              contract={contratto}
              clientName={contractClientName(contratto)}
              signedValue={contractSignedValue(contratto)}
              currentValue={contractDisplayValue(contratto)}
              selected={selectedContrattoId === contratto.id}
              onSelect={() => selectContratto(contratto)}
            />
          {/each}
        </div>
      {/if}
    </article>

    <aside class="contract-detail" aria-live="polite">
      {#if selectedContratto}
        <div class="detail-heading">
          <div>
            <span>Contratto selezionato</span>
            <h3>{selectedContratto.contract_id}</h3>
          </div>
          <div class="row-actions">
            <button type="button" on:click={() => editContratto(selectedContratto)}>Modifica</button>
            <button type="button" class="danger" on:click={() => requestDeleteContratto(selectedContratto)}>Elimina</button>
          </div>
        </div>
        <dl class="contract-data">
          <div>
            <dt>ID contratto</dt>
            <dd>{selectedContratto.contract_id}</dd>
          </div>
          <div>
            <dt>Cliente</dt>
            <dd>{contractClientName(selectedContratto)}</dd>
          </div>
          <div>
            <dt>Valore</dt>
            <dd>€ {contractSignedValue(selectedContratto).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</dd>
          </div>
          {#if selectedContratto.periodicity}
            <div>
              <dt>Valore maturato</dt>
              <dd>€ {contractDisplayValue(selectedContratto).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</dd>
            </div>
          {/if}
          <div>
            <dt>Data inizio</dt>
            <dd>{selectedContratto.start_date}</dd>
          </div>
          <div>
            <dt>Data fine</dt>
            <dd>{selectedContratto.end_date}</dd>
          </div>
        </dl>
        <ContractTaskPool
          contract={selectedContratto}
          taskInput={poolTaskInputs[selectedContratto.id] || ''}
          onTaskInput={(value) => setPoolTaskInput(selectedContratto.id, value)}
          onAppendTask={() => appendTask(selectedContratto)}
          onDeleteTask={(task) => deleteTask(selectedContratto, task)}
        />
        <section class="pool-task-results">
          <div class="pool-task-results-head">
            <div>
              <h4>Task del pool</h4>
              <p>Ore Jira del periodo e quota del valore del contratto.</p>
            </div>
            <strong>{formatHours(selectedPoolTaskTotalSeconds)}</strong>
          </div>
          {#if selectedPoolTaskRows.length === 0}
            <p class="task-results-empty">Aggiungi almeno una task al pool per calcolare le quote.</p>
          {:else}
            <div class="pool-task-result-list">
              {#each selectedPoolTaskRows as task (`result-${selectedContratto.id}-${task.key}`)}
                <div class:task-not-found={!task.found} class="pool-task-result">
                  <div>
                    <strong>{task.key}</strong>
                    <span>{task.summary}</span>
                  </div>
                  <span>{formatHours(task.seconds)}</span>
                  <span>{formatCurrency(task.hourlyRate)}/h</span>
                  <strong>{formatCurrency(task.share)}</strong>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      {:else}
        <p class="detail-placeholder">Seleziona un contratto dall'elenco per visualizzarne tutti i dettagli.</p>
      {/if}
    </aside>
  </div>
  {/if}
</section>

<style>
  .clienti-section { margin: 1.25rem 0; padding: 1rem; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; }
  .section-header, .row-actions, .form-actions { display: flex; align-items: center; flex-wrap: wrap; gap: .55rem; }
  .section-header { justify-content: space-between; margin-bottom: 1rem; }
  h2, h3, p { margin-top: 0; } h2 { font-size: 1.1rem; } h3 { font-size: .92rem; } .section-header p, .list-card > p { margin-bottom: 0; color: #64748b; font-size: .82rem; }
  button { max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: white; background: #2563eb; cursor: pointer; font: inherit; font-size: .78rem; overflow-wrap: anywhere; } button:disabled { opacity: .6; cursor: not-allowed; } button.secondary { background: #64748b; } button.danger { background: #dc2626; } .refresh-button { background: #475569; } .list-toggle { width: 100%; display: flex; align-items: center; gap: .45rem; margin-top: 1rem; background: #334155; text-align: left; } .list-toggle .toggle-icon { flex: 0 0 auto; display: inline-flex; font-size: .78rem; }
  .editor-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .data-grid.stale { opacity: .65; }
  .data-grid { transition: opacity .16s ease; --contracts-panel-height: 460px; display: grid; grid-template-columns: minmax(190px, .42fr) minmax(230px, .7fr) minmax(300px, 1.15fr); align-items: start; gap: .7rem; margin-top: .7rem; padding: .1rem .45rem .1rem .1rem; } .data-grid > * { min-width: 0; }
  .editor-card, .list-card, .contracts-tools { padding: .85rem; border: 1px solid #e2e8f0; border-radius: 9px; background: #f8fafc; }
  .list-card { padding: .7rem; }
  .contracts-card { display: grid; grid-template-rows: auto minmax(0, 1fr); height: var(--contracts-panel-height); overflow: hidden; }
  .contracts-tools { align-self: start; }
  .contracts-tools h3 { margin-bottom: .7rem; }
  .search-label { margin: 0 0 .25rem; }
  .contracts-search { min-width: 0; }
  .contracts-tools p { margin: .55rem 0 0; color: #64748b; font-size: .72rem; }
  .sort-bar { display: flex; align-items: center; gap: .45rem; margin-top: .7rem; padding-top: .7rem; border-top: 1px solid #e2e8f0; color: #475569; font-size: .72rem; font-weight: 600; }
  .sort-client-button { position: relative; min-width: 2.1rem; padding: .32rem .45rem; background: #475569; font-weight: 700; letter-spacing: -.04em; }
  .sort-client-button.sort-desc { background: #1d4ed8; }
  .sort-tooltip { position: absolute; z-index: 2; top: 50%; left: calc(100% + .5rem); width: max-content; max-width: 180px; padding: .35rem .45rem; border-radius: 5px; background: #0f172a; color: #fff; font-size: .68rem; font-weight: 500; letter-spacing: normal; line-height: 1.25; opacity: 0; pointer-events: none; transform: translateY(-50%); transition: opacity .15s ease; visibility: hidden; }
  .sort-client-button:hover .sort-tooltip, .sort-client-button:focus-visible .sort-tooltip { opacity: 1; visibility: visible; }
  label { display: grid; gap: .25rem; margin: .55rem 0; color: #334155; font-size: .78rem; font-weight: 600; } input { width: 100%; box-sizing: border-box; padding: .43rem .5rem; border: 1px solid #cbd5e1; border-radius: 6px; background: white; color: #0f172a; font: inherit; }
  .form-actions { margin-top: .8rem; }
  .contracts-list { display: grid; min-height: 0; gap: .45rem; margin: 0; padding: 0 .2rem 0 0; overflow-y: auto; overscroll-behavior: contain; }
  .contract-detail { height: var(--contracts-panel-height); box-sizing: border-box; padding: .8rem; border: 1px solid #bfdbfe; border-radius: 9px; background: #eff6ff; overflow-y: auto; overscroll-behavior: contain; }
  .detail-heading { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: .65rem; } .detail-heading h3 { margin: .12rem 0 0; color: #0f172a; } .detail-heading span { color: #475569; font-size: .7rem; }
  .contract-data { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .45rem; margin: .75rem 0; } .contract-data div { padding: .45rem; border-radius: 7px; background: #fff; } .contract-data dt { color: #64748b; font-size: .67rem; } .contract-data dd { margin: .18rem 0 0; color: #0f172a; font-size: .75rem; font-weight: 700; }
  .pool-task-results { margin-top: .85rem; padding-top: .75rem; border-top: 1px solid #bfdbfe; }
  .pool-task-results-head { display: flex; align-items: start; justify-content: space-between; gap: .6rem; } .pool-task-results-head h4, .pool-task-results-head p { margin: 0; } .pool-task-results-head h4 { color: #0f172a; font-size: .82rem; } .pool-task-results-head p, .task-results-empty { color: #64748b; font-size: .7rem; } .pool-task-results-head > strong { color: #1e3a8a; font-size: .76rem; white-space: nowrap; }
  .pool-task-result-list { display: grid; gap: .35rem; margin-top: .55rem; } .pool-task-result { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; align-items: center; gap: .55rem; padding: .45rem .5rem; border: 1px solid #dbeafe; border-radius: 7px; background: #fff; } .pool-task-result > div { display: grid; min-width: 0; gap: .1rem; } .pool-task-result > div > strong { color: #1e3a8a; font-family: var(--font-mono); font-size: .7rem; } .pool-task-result > div > span { overflow: hidden; color: #334155; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; } .pool-task-result > span { color: #475569; font-size: .7rem; white-space: nowrap; } .pool-task-result > strong { color: #166534; font-size: .74rem; white-space: nowrap; } .task-not-found { border-style: dashed; opacity: .72; } .task-not-found > strong { color: #92400e; }
  .detail-placeholder { margin: 0; color: #64748b; font-size: .8rem; }
  .delete-confirm-overlay { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 1rem; }
  .delete-confirm-backdrop { position: absolute; inset: 0; width: 100%; height: 100%; max-width: none; padding: 0; border: 0; border-radius: 0; background: rgb(15 23 42 / .68); cursor: default; }
  .delete-confirm-content { position: relative; z-index: 1; width: min(100%, 390px); }
  @media (max-width: 980px) { .data-grid { grid-template-columns: minmax(180px, .45fr) minmax(0, 1fr); } .contract-detail { grid-column: 1 / -1; } }
  @media (max-width: 760px) { .editor-grid, .data-grid { grid-template-columns: 1fr; } .data-grid { --contracts-panel-height: 420px; } .contract-detail { grid-column: auto; } .contract-data { grid-template-columns: 1fr; } .section-header, .detail-heading { align-items: flex-start; flex-direction: column; } .sort-tooltip { top: calc(100% + .4rem); left: 0; transform: none; } .pool-task-result { grid-template-columns: 1fr; gap: .25rem; } .row-actions { flex-wrap: wrap; } }
</style>

{#if editingContratto}
  <EditContrattoModal
    contratto={editingContratto}
    {clienti}
    onClose={closeEditContratto}
    onSaved={() => loadData()}
    onNotify={showToast}
  />
{/if}

{#if deleteTarget}
  <div class="delete-confirm-overlay" data-history-hover-exclude>
    <button class="delete-confirm-backdrop" type="button" data-history-hover-exclude aria-label="Annulla eliminazione" on:click={closeDeleteConfirmation}></button>
    <div class="delete-confirm-content" data-history-hover-exclude>
      <DeleteConfirmCard
        message={deleteConfirmationMessage(deleteTarget)}
        {deleting}
        onCancel={closeDeleteConfirmation}
        onConfirm={confirmDelete}
      />
    </div>
  </div>
{/if}

<ToastState bind:open={toastOpen} success={toastSuccess} message={toastMessage} />
