<script lang="ts">
  import { onMount } from 'svelte';
  import {
    useClientiList,
    useClienteDelete,
    useClienteUpdate,
    useContrattiClientiList,
    useContrattoClienteDelete,
    useContrattoClientePoolTaskAppend,
    useContrattoClientePoolTaskDelete,
    useContrattoClienteUpdate
  } from '$lib/hooks/useClienti';
  import type { Cliente, ContrattoCliente } from '$lib/services/clienti';
  import ClientiCreateCards from '$lib/components/Jira/ClientiCreateCards.svelte';
  import DeleteConfirmCard from '$lib/components/DeleteConfirmCard.svelte';
  import ToastState from '$lib/components/ToastState.svelte';

  type JiraPoolTask = {
    key: string;
    summary: string;
    seconds: number;
  };

  type PoolTaskRow = JiraPoolTask & { found: boolean; costoOrario: number; guadagno: number };
  type DeleteTarget =
    | { type: 'cliente'; cliente: Cliente }
    | { type: 'contratto'; contratto: ContrattoCliente };

  export let jiraTasks: JiraPoolTask[] = [];

  type ClienteForm = { id: number | null; nome: string; indirizzo: string; telefono: string };
  type ContrattoForm = {
    id: number | null;
    cliente_id: string;
    value: string;
    data_creazione: string;
    data_fine: string;
    pool_task: string[];
  };

  const emptyClienteForm = (): ClienteForm => ({ id: null, nome: '', indirizzo: '', telefono: '' });
  const emptyContrattoForm = (): ContrattoForm => ({
    id: null,
    cliente_id: '',
    value: '',
    data_creazione: '',
    data_fine: '',
    pool_task: []
  });

  let clienti: Cliente[] = [];
  let contratti: ContrattoCliente[] = [];
  let loading = true;
  let savingCliente = false;
  let savingContratto = false;
  let toastOpen = false;
  let toastSuccess = true;
  let toastMessage = '';
  let clienteForm = emptyClienteForm();
  let contrattoForm = emptyContrattoForm();
  let poolTaskInputs: Record<number, string> = {};
  let listsOpen = false;
  let creating = false;
  let selectedContrattoId: number | null = null;
  let deleteTarget: DeleteTarget | null = null;
  let deleting = false;

  $: selectedContratto = contratti.find((contratto) => contratto.id === selectedContrattoId) || null;
  $: jiraTasksByKey = new Map(jiraTasks.map((task) => [task.key.trim().toUpperCase(), task]));
  $: selectedPoolTaskRows = buildPoolTaskRows(selectedContratto, jiraTasksByKey);
  $: selectedPoolTaskTotalSeconds = selectedPoolTaskRows.reduce((total, task) => total + task.seconds, 0);

  function buildPoolTaskRows(
    contratto: ContrattoCliente | null,
    tasksByKey: Map<string, JiraPoolTask>
  ): PoolTaskRow[] {
    if (!contratto) return [];

    const totalSeconds = contratto.pool_task.reduce(
      (total, taskKey) => total + Math.max(0, Number(tasksByKey.get(taskKey.trim().toUpperCase())?.seconds || 0)),
      0
    );
    const value = Number(contratto.value || 0);

    return contratto.pool_task.map((taskKey) => {
      const task = tasksByKey.get(taskKey.trim().toUpperCase());
      const seconds = Math.max(0, Number(task?.seconds || 0));
      return {
        key: taskKey,
        summary: task?.summary || 'Task non presente nei worklog del periodo',
        seconds,
        found: Boolean(task),
        costoOrario: totalSeconds > 0 ? value / (totalSeconds / 3600) : 0,
        guadagno: totalSeconds > 0 ? (value / totalSeconds) * seconds : 0
      };
    });
  }

  function formatHours(seconds: number) {
    const hours = seconds / 3600;
    return `${hours.toLocaleString('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 2 })} h`;
  }

  function formatCurrency(value: number) {
    return value.toLocaleString('it-IT', { style: 'currency', currency: 'EUR' });
  }

  async function loadData() {
    loading = true;
    try {
      const [loadedClienti, loadedContratti] = await Promise.all([useClientiList(), useContrattiClientiList()]);
      clienti = loadedClienti;
      contratti = loadedContratti;
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile caricare clienti e contratti.'), false);
    } finally {
      loading = false;
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
      : `Sei veramente sicuro di eliminare il contratto per ${target.contratto.cliente.nome}? Se lo elimini perderai il valore delle task associate.`;
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    deleting = true;
    try {
      if (deleteTarget.type === 'cliente') {
        const { cliente } = deleteTarget;
        await useClienteDelete(cliente.id);
        if (clienteForm.id === cliente.id) clienteForm = emptyClienteForm();
        showToast('Cliente eliminato.');
      } else {
        const { contratto } = deleteTarget;
        await useContrattoClienteDelete(contratto.id);
        if (contrattoForm.id === contratto.id) contrattoForm = emptyContrattoForm();
        if (selectedContrattoId === contratto.id) selectedContrattoId = null;
        showToast('Contratto commerciale eliminato.');
      }
      await loadData();
      deleteTarget = null;
    } catch (cause: any) {
      const fallback = deleteTarget.type === 'cliente' ? 'Impossibile eliminare il cliente.' : 'Impossibile eliminare il contratto.';
      showToast(String(cause?.message || cause || fallback), false);
    } finally {
      deleting = false;
    }
  }

  async function saveContratto() {
    savingContratto = true;
    try {
      const clienteId = Number(contrattoForm.cliente_id);
      if (!Number.isInteger(clienteId) || clienteId <= 0) throw new Error('Seleziona un cliente.');
      const normalizedValue = String(contrattoForm.value ?? '').trim();
      if (!normalizedValue) throw new Error('Il valore del contratto è obbligatorio.');

      if (contrattoForm.id === null) return;
      await useContrattoClienteUpdate(contrattoForm.id, {
        cliente_id: clienteId,
        value: normalizedValue,
        pool_task: contrattoForm.pool_task
      });

      contrattoForm = emptyContrattoForm();
      showToast('Contratto commerciale salvato.');
      await loadData();
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile salvare il contratto.'), false);
    } finally {
      savingContratto = false;
    }
  }

  function editContratto(contratto: ContrattoCliente) {
    contrattoForm = {
      id: contratto.id,
      cliente_id: String(contratto.cliente.id),
      value: String(contratto.value),
      data_creazione: contratto.data_creazione,
      data_fine: contratto.data_fine,
      pool_task: [...(contratto.pool_task || [])]
    };
  }

  function selectContratto(contratto: ContrattoCliente) {
    selectedContrattoId = contratto.id;
  }

  function selectContrattoOnKeydown(event: KeyboardEvent, contratto: ContrattoCliente) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    selectContratto(contratto);
  }

  async function appendTask(contratto: ContrattoCliente) {
    const task = String(poolTaskInputs[contratto.id] || '').trim();
    try {
      const updated = await useContrattoClientePoolTaskAppend(contratto.id, task);
      contratti = contratti.map((item) => (item.id === updated.id ? updated : item));
      if (contrattoForm.id === updated.id) contrattoForm.pool_task = [...updated.pool_task];
      poolTaskInputs = { ...poolTaskInputs, [contratto.id]: '' };
      showToast('Task aggiunta al pool.');
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile aggiungere la task.'), false);
    }
  }

  async function deleteTask(contratto: ContrattoCliente, task: string) {
    try {
      const updated = await useContrattoClientePoolTaskDelete(contratto.id, task);
      contratti = contratti.map((item) => (item.id === updated.id ? updated : item));
      if (contrattoForm.id === updated.id) contrattoForm.pool_task = [...updated.pool_task];
      showToast('Task rimossa dal pool.');
    } catch (cause: any) {
      showToast(String(cause?.message || cause || 'Impossibile rimuovere la task.'), false);
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<section class="clienti-section" data-history-hover data-history-hover-exclude={creating || undefined}>
  <header class="section-header">
    <div>
      <h2>Clienti e contratti commerciali</h2>
      <p>Gestisci anagrafiche, valori contrattuali e pool di task Jira.</p>
    </div>
    <button type="button" class="refresh-button" on:click={loadData} disabled={loading}>Aggiorna</button>
  </header>

  <ClientiCreateCards
    {clienti}
    onCreated={handleCreated}
    onOpen={() => (creating = true)}
    onClosed={() => (creating = false)}
    onNotify={showToast}
  />

  {#if clienteForm.id !== null || contrattoForm.id !== null}
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

    {#if contrattoForm.id !== null}<form class="editor-card" on:submit|preventDefault={saveContratto}>
      <h3>Modifica contratto</h3>
      <label>
        Cliente
        <select bind:value={contrattoForm.cliente_id} required>
          <option value="">Seleziona cliente</option>
          {#each clienti as cliente (cliente.id)}<option value={String(cliente.id)}>{cliente.nome}</option>{/each}
        </select>
      </label>
      <label>Valore <input type="number" min="0" step="0.01" bind:value={contrattoForm.value} required /></label>
      <label>Data creazione <input type="date" bind:value={contrattoForm.data_creazione} required readonly={contrattoForm.id !== null} /></label>
      <label>Data fine <input type="date" bind:value={contrattoForm.data_fine} required readonly={contrattoForm.id !== null} /></label>
      <div class="form-actions">
        <button type="submit" disabled={savingContratto || clienti.length === 0}>{savingContratto ? 'Salvo...' : 'Salva contratto'}</button>
        <button type="button" class="secondary" on:click={() => (contrattoForm = emptyContrattoForm())}>Annulla</button>
      </div>
    </form>{/if}
  </div>
  {/if}

  <button type="button" class="list-toggle" on:click={() => (listsOpen = !listsOpen)} aria-expanded={listsOpen}>
    <span>{listsOpen ? '⌃' : '⌄'}</span>
    Clienti e contratti esistenti ({clienti.length + contratti.length})
  </button>

  {#if listsOpen}<div class="data-grid">
    <article class="list-card clienti-card">
      <h3>Clienti ({clienti.length})</h3>
      {#if loading}<p>Caricamento...</p>
      {:else if clienti.length === 0}<p>Nessun cliente presente.</p>
      {:else}<ul>{#each clienti as cliente (cliente.id)}
        <li>
          <div><strong>{cliente.nome}</strong>{#if cliente.indirizzo}<span>{cliente.indirizzo}</span>{/if}{#if cliente.telefono}<span>{cliente.telefono}</span>{/if}</div>
          <div class="row-actions"><button type="button" on:click={() => editCliente(cliente)}>Modifica</button><button type="button" class="danger" on:click={() => requestDeleteCliente(cliente)}>Elimina</button></div>
        </li>
      {/each}</ul>{/if}
    </article>

    <article class="list-card contracts-card">
      <h3>Contratti ({contratti.length})</h3>
      {#if loading}<p>Caricamento...</p>
      {:else if contratti.length === 0}<p>Nessun contratto commerciale presente.</p>
      {:else}<div class="contracts-list">{#each contratti as contratto (contratto.id)}
        <section
          class="contract-row"
          class:contract-selected={selectedContrattoId === contratto.id}
          role="button"
          tabindex="0"
          on:click={() => selectContratto(contratto)}
          on:keydown={(event) => selectContrattoOnKeydown(event, contratto)}
        >
          <div class="contract-heading"><div><strong>{contratto.cliente.nome}</strong><span>€ {Number(contratto.value).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span><small>{contratto.data_creazione} → {contratto.data_fine}</small></div><div class="row-actions"><button type="button" on:click={() => editContratto(contratto)}>Modifica</button><button type="button" class="danger" on:click={() => requestDeleteContratto(contratto)}>Elimina</button></div></div>
          <div class="pool"><span>Pool task</span><div class="task-list">{#each contratto.pool_task as task (`${contratto.id}-${task}`)}<span class="task-chip">{task}<button type="button" aria-label={`Rimuovi ${task}`} on:click={() => deleteTask(contratto, task)}>×</button></span>{/each}</div><div class="add-task"><input placeholder="PROJ-123" value={poolTaskInputs[contratto.id] || ''} on:input={(event) => (poolTaskInputs = { ...poolTaskInputs, [contratto.id]: event.currentTarget.value })} /><button type="button" on:click={() => appendTask(contratto)}>Aggiungi</button></div></div>
        </section>
      {/each}</div>{/if}
    </article>

    <aside class="contract-detail" aria-live="polite">
      {#if selectedContratto}
        <div class="detail-heading">
          <div>
            <span>Contratto selezionato</span>
            <h3>{selectedContratto.cliente.nome}</h3>
          </div>
          <div class="row-actions">
            <button type="button" on:click={() => editContratto(selectedContratto)}>Modifica</button>
            <button type="button" class="danger" on:click={() => requestDeleteContratto(selectedContratto)}>Elimina</button>
          </div>
        </div>
        <dl class="contract-data">
          <div><dt>Valore</dt><dd>€ {Number(selectedContratto.value).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</dd></div>
          <div><dt>Data creazione</dt><dd>{selectedContratto.data_creazione}</dd></div>
          <div><dt>Data fine</dt><dd>{selectedContratto.data_fine}</dd></div>
        </dl>
        <div class="pool">
          <span>Pool task</span>
          <div class="task-list">
            {#each selectedContratto.pool_task as task (`detail-${selectedContratto.id}-${task}`)}
              <span class="task-chip">{task}<button type="button" aria-label={`Rimuovi ${task}`} on:click={() => deleteTask(selectedContratto, task)}>×</button></span>
            {/each}
          </div>
          <div class="add-task">
            <input placeholder="PROJ-123" value={poolTaskInputs[selectedContratto.id] || ''} on:input={(event) => (poolTaskInputs = { ...poolTaskInputs, [selectedContratto.id]: event.currentTarget.value })} />
            <button type="button" on:click={() => appendTask(selectedContratto)}>Aggiungi</button>
          </div>
        </div>
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
                  <span>{formatCurrency(task.costoOrario)}/h</span>
                  <strong>{formatCurrency(task.guadagno)}</strong>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      {:else}
        <p class="detail-placeholder">Seleziona un contratto dall'elenco per visualizzarne tutti i dettagli.</p>
      {/if}
    </aside>
  </div>{/if}
</section>

<style>
  .clienti-section { margin: 1.25rem 0; padding: 1rem; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; }
  .section-header, .contract-heading, .row-actions, .form-actions, .add-task { display: flex; align-items: center; flex-wrap: wrap; gap: .55rem; }
  .section-header { justify-content: space-between; margin-bottom: 1rem; }
  h2, h3, p { margin-top: 0; } h2 { font-size: 1.1rem; } h3 { font-size: .92rem; } .section-header p, .list-card > p { margin-bottom: 0; color: #64748b; font-size: .82rem; }
  button { max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: white; background: #2563eb; cursor: pointer; font: inherit; font-size: .78rem; overflow-wrap: anywhere; } button:disabled { opacity: .6; cursor: not-allowed; } button.secondary { background: #64748b; } button.danger { background: #dc2626; } .refresh-button { background: #475569; } .list-toggle { width: 100%; display: flex; align-items: center; gap: .45rem; margin-top: 1rem; background: #334155; text-align: left; } .list-toggle span { flex: 0 0 auto; font-size: 1rem; }
  .editor-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .data-grid { display: grid; grid-template-columns: minmax(190px, .42fr) minmax(230px, .7fr) minmax(300px, 1.15fr); align-items: start; gap: .7rem; max-height: 460px; margin-top: .7rem; padding: .1rem .45rem .1rem .1rem; overflow-y: auto; overscroll-behavior: contain; } .data-grid > * { min-width: 0; }
  .editor-card, .list-card { padding: .85rem; border: 1px solid #e2e8f0; border-radius: 9px; background: #f8fafc; }
  .list-card { padding: .7rem; }
  .clienti-card { max-width: 285px; }
  label { display: grid; gap: .25rem; margin: .55rem 0; color: #334155; font-size: .78rem; font-weight: 600; } input, select { width: 100%; box-sizing: border-box; padding: .43rem .5rem; border: 1px solid #cbd5e1; border-radius: 6px; background: white; color: #0f172a; font: inherit; } input[readonly] { background: #e2e8f0; color: #475569; }
  .form-actions { margin-top: .8rem; }
  ul, .contracts-list { display: grid; gap: .45rem; margin: 0; padding: 0; list-style: none; }
  li, .contract-row { padding: .6rem .7rem; border: 1px solid #e2e8f0; border-radius: 7px; background: #fff; }
  li, li > div:first-child { display: flex; } li { justify-content: space-between; align-items: center; gap: .5rem; } li > div:first-child { flex-direction: column; } li span, small { color: #64748b; font-size: .75rem; }
  .contract-row { cursor: pointer; transition: border-color .15s ease, background-color .15s ease, box-shadow .15s ease; }
  .contract-row:hover, .contract-selected { border-color: #93c5fd; background: #eff6ff; }
  .contract-selected { box-shadow: inset 3px 0 0 #2563eb; }
  .contracts-card .pool, .contracts-card .row-actions { display: none; }
  .contract-heading { justify-content: space-between; } .contract-heading > div:first-child { display: grid; gap: .12rem; }
  .contract-detail { min-height: 190px; padding: .8rem; border: 1px solid #bfdbfe; border-radius: 9px; background: #eff6ff; }
  .detail-heading { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: .65rem; } .detail-heading h3 { margin: .12rem 0 0; color: #0f172a; } .detail-heading span { color: #475569; font-size: .7rem; }
  .contract-data { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .45rem; margin: .75rem 0; } .contract-data div { padding: .45rem; border-radius: 7px; background: #fff; } .contract-data dt { color: #64748b; font-size: .67rem; } .contract-data dd { margin: .18rem 0 0; color: #0f172a; font-size: .75rem; font-weight: 700; }
  .pool { margin-top: .45rem; display: grid; gap: .35rem; font-size: .74rem; color: #475569; } .task-list { display: flex; flex-wrap: wrap; gap: .3rem; } .task-chip { display: inline-flex; align-items: center; max-width: 100%; gap: .25rem; padding: .2rem .38rem; border-radius: 999px; background: #dbeafe; color: #1e3a8a; font-family: var(--font-mono); font-size: .7rem; overflow-wrap: anywhere; } .task-chip button { flex: 0 0 auto; padding: 0; color: #1e3a8a; background: transparent; font-size: 1rem; line-height: .7; } .add-task input { flex: 1 1 9rem; min-width: 0; }
  .pool-task-results { margin-top: .85rem; padding-top: .75rem; border-top: 1px solid #bfdbfe; }
  .pool-task-results-head { display: flex; align-items: start; justify-content: space-between; gap: .6rem; } .pool-task-results-head h4, .pool-task-results-head p { margin: 0; } .pool-task-results-head h4 { color: #0f172a; font-size: .82rem; } .pool-task-results-head p, .task-results-empty { color: #64748b; font-size: .7rem; } .pool-task-results-head > strong { color: #1e3a8a; font-size: .76rem; white-space: nowrap; }
  .pool-task-result-list { display: grid; gap: .35rem; margin-top: .55rem; } .pool-task-result { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; align-items: center; gap: .55rem; padding: .45rem .5rem; border: 1px solid #dbeafe; border-radius: 7px; background: #fff; } .pool-task-result > div { display: grid; min-width: 0; gap: .1rem; } .pool-task-result > div > strong { color: #1e3a8a; font-family: var(--font-mono); font-size: .7rem; } .pool-task-result > div > span { overflow: hidden; color: #334155; font-size: .7rem; text-overflow: ellipsis; white-space: nowrap; } .pool-task-result > span { color: #475569; font-size: .7rem; white-space: nowrap; } .pool-task-result > strong { color: #166534; font-size: .74rem; white-space: nowrap; } .task-not-found { border-style: dashed; opacity: .72; } .task-not-found > strong { color: #92400e; }
  .detail-placeholder { margin: 0; color: #64748b; font-size: .8rem; }
  .delete-confirm-overlay { position: fixed; inset: 0; z-index: 90; display: grid; place-items: center; padding: 1rem; }
  .delete-confirm-backdrop { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; background: rgb(15 23 42 / .68); cursor: default; }
  .delete-confirm-content { position: relative; z-index: 1; width: min(100%, 390px); }
  @media (max-width: 980px) { .data-grid { grid-template-columns: minmax(180px, .45fr) minmax(0, 1fr); } .contract-detail { grid-column: 1 / -1; } }
  @media (max-width: 760px) { .editor-grid, .data-grid { grid-template-columns: 1fr; } .data-grid { max-height: 420px; } .clienti-card { max-width: none; } .contract-detail { grid-column: auto; } .contract-data { grid-template-columns: 1fr; } .section-header, .contract-heading, .detail-heading, li { align-items: flex-start; flex-direction: column; } .pool-task-result { grid-template-columns: 1fr; gap: .25rem; } .row-actions { flex-wrap: wrap; } }
</style>

{#if deleteTarget}
  <div class="delete-confirm-overlay" data-history-hover-exclude>
    <button class="delete-confirm-backdrop" type="button" aria-label="Annulla eliminazione" on:click={closeDeleteConfirmation}></button>
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
