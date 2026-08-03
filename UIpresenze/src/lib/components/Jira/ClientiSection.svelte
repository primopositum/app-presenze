<script lang="ts">
  import { onMount } from 'svelte';
  import {
    useClientiList,
    useClienteCreate,
    useClienteDelete,
    useClienteUpdate,
    useContrattiClientiList,
    useContrattoClienteCreate,
    useContrattoClienteDelete,
    useContrattoClientePoolTaskAppend,
    useContrattoClientePoolTaskDelete,
    useContrattoClienteUpdate
  } from '$lib/hooks/useClienti';
  import type { Cliente, ContrattoCliente } from '$lib/services/clienti';

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
  let error = '';
  let success = '';
  let clienteForm = emptyClienteForm();
  let contrattoForm = emptyContrattoForm();
  let poolTaskInputs: Record<number, string> = {};

  async function loadData() {
    loading = true;
    error = '';
    try {
      const [loadedClienti, loadedContratti] = await Promise.all([useClientiList(), useContrattiClientiList()]);
      clienti = loadedClienti;
      contratti = loadedContratti;
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile caricare clienti e contratti.');
    } finally {
      loading = false;
    }
  }

  function setSuccess(message: string) {
    success = message;
    error = '';
  }

  async function saveCliente() {
    savingCliente = true;
    error = '';
    try {
      const payload = {
        nome: clienteForm.nome.trim(),
        indirizzo: clienteForm.indirizzo.trim(),
        telefono: clienteForm.telefono.trim()
      };
      if (!payload.nome) throw new Error('Il nome del cliente è obbligatorio.');

      if (clienteForm.id === null) await useClienteCreate(payload);
      else await useClienteUpdate(clienteForm.id, payload);

      clienteForm = emptyClienteForm();
      setSuccess('Cliente salvato.');
      await loadData();
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile salvare il cliente.');
    } finally {
      savingCliente = false;
    }
  }

  function editCliente(cliente: Cliente) {
    clienteForm = { ...cliente };
    success = '';
  }

  async function deleteCliente(cliente: Cliente) {
    if (!confirm(`Eliminare il cliente ${cliente.nome}?`)) return;
    try {
      await useClienteDelete(cliente.id);
      if (clienteForm.id === cliente.id) clienteForm = emptyClienteForm();
      setSuccess('Cliente eliminato.');
      await loadData();
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile eliminare il cliente.');
    }
  }

  async function saveContratto() {
    savingContratto = true;
    error = '';
    try {
      const clienteId = Number(contrattoForm.cliente_id);
      if (!Number.isInteger(clienteId) || clienteId <= 0) throw new Error('Seleziona un cliente.');
      if (!contrattoForm.value.trim()) throw new Error('Il valore del contratto è obbligatorio.');

      if (contrattoForm.id === null) {
        if (!contrattoForm.data_creazione || !contrattoForm.data_fine) {
          throw new Error('Le date di creazione e fine sono obbligatorie.');
        }
        await useContrattoClienteCreate({
          cliente_id: clienteId,
          value: contrattoForm.value,
          pool_task: contrattoForm.pool_task,
          data_creazione: contrattoForm.data_creazione,
          data_fine: contrattoForm.data_fine
        });
      } else {
        await useContrattoClienteUpdate(contrattoForm.id, {
          cliente_id: clienteId,
          value: contrattoForm.value,
          pool_task: contrattoForm.pool_task
        });
      }

      contrattoForm = emptyContrattoForm();
      setSuccess('Contratto commerciale salvato.');
      await loadData();
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile salvare il contratto.');
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
    success = '';
  }

  async function deleteContratto(contratto: ContrattoCliente) {
    if (!confirm(`Eliminare il contratto di ${contratto.cliente.nome}?`)) return;
    try {
      await useContrattoClienteDelete(contratto.id);
      if (contrattoForm.id === contratto.id) contrattoForm = emptyContrattoForm();
      setSuccess('Contratto commerciale eliminato.');
      await loadData();
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile eliminare il contratto.');
    }
  }

  async function appendTask(contratto: ContrattoCliente) {
    const task = String(poolTaskInputs[contratto.id] || '').trim();
    try {
      const updated = await useContrattoClientePoolTaskAppend(contratto.id, task);
      contratti = contratti.map((item) => (item.id === updated.id ? updated : item));
      if (contrattoForm.id === updated.id) contrattoForm.pool_task = [...updated.pool_task];
      poolTaskInputs = { ...poolTaskInputs, [contratto.id]: '' };
      setSuccess('Task aggiunta al pool.');
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile aggiungere la task.');
    }
  }

  async function deleteTask(contratto: ContrattoCliente, task: string) {
    try {
      const updated = await useContrattoClientePoolTaskDelete(contratto.id, task);
      contratti = contratti.map((item) => (item.id === updated.id ? updated : item));
      if (contrattoForm.id === updated.id) contrattoForm.pool_task = [...updated.pool_task];
      setSuccess('Task rimossa dal pool.');
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Impossibile rimuovere la task.');
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<section class="clienti-section" data-history-hover>
  <header class="section-header">
    <div>
      <h2>Clienti e contratti commerciali</h2>
      <p>Gestisci anagrafiche, valori contrattuali e pool di task Jira.</p>
    </div>
    <button type="button" class="refresh-button" on:click={loadData} disabled={loading}>Aggiorna</button>
  </header>

  {#if error}<p class="feedback error">{error}</p>{/if}
  {#if success}<p class="feedback success">{success}</p>{/if}

  <div class="editor-grid">
    <form class="editor-card" on:submit|preventDefault={saveCliente}>
      <h3>{clienteForm.id === null ? 'Nuovo cliente' : 'Modifica cliente'}</h3>
      <label>Nome <input bind:value={clienteForm.nome} required /></label>
      <label>Indirizzo <input bind:value={clienteForm.indirizzo} /></label>
      <label>Telefono <input bind:value={clienteForm.telefono} /></label>
      <div class="form-actions">
        <button type="submit" disabled={savingCliente}>{savingCliente ? 'Salvo...' : 'Salva cliente'}</button>
        {#if clienteForm.id !== null}<button type="button" class="secondary" on:click={() => (clienteForm = emptyClienteForm())}>Annulla</button>{/if}
      </div>
    </form>

    <form class="editor-card" on:submit|preventDefault={saveContratto}>
      <h3>{contrattoForm.id === null ? 'Nuovo contratto' : 'Modifica contratto'}</h3>
      <label>
        Cliente
        <select bind:value={contrattoForm.cliente_id} required>
          <option value="">Seleziona cliente</option>
          {#each clienti as cliente (cliente.id)}<option value={cliente.id}>{cliente.nome}</option>{/each}
        </select>
      </label>
      <label>Valore <input type="number" min="0" step="0.01" bind:value={contrattoForm.value} required /></label>
      <label>Data creazione <input type="date" bind:value={contrattoForm.data_creazione} required readonly={contrattoForm.id !== null} /></label>
      <label>Data fine <input type="date" bind:value={contrattoForm.data_fine} required readonly={contrattoForm.id !== null} /></label>
      <div class="form-actions">
        <button type="submit" disabled={savingContratto || clienti.length === 0}>{savingContratto ? 'Salvo...' : 'Salva contratto'}</button>
        {#if contrattoForm.id !== null}<button type="button" class="secondary" on:click={() => (contrattoForm = emptyContrattoForm())}>Annulla</button>{/if}
      </div>
    </form>
  </div>

  <div class="data-grid">
    <article class="list-card">
      <h3>Clienti ({clienti.length})</h3>
      {#if loading}<p>Caricamento...</p>
      {:else if clienti.length === 0}<p>Nessun cliente presente.</p>
      {:else}<ul>{#each clienti as cliente (cliente.id)}
        <li>
          <div><strong>{cliente.nome}</strong>{#if cliente.indirizzo}<span>{cliente.indirizzo}</span>{/if}{#if cliente.telefono}<span>{cliente.telefono}</span>{/if}</div>
          <div class="row-actions"><button type="button" on:click={() => editCliente(cliente)}>Modifica</button><button type="button" class="danger" on:click={() => deleteCliente(cliente)}>Elimina</button></div>
        </li>
      {/each}</ul>{/if}
    </article>

    <article class="list-card contracts-card">
      <h3>Contratti ({contratti.length})</h3>
      {#if loading}<p>Caricamento...</p>
      {:else if contratti.length === 0}<p>Nessun contratto commerciale presente.</p>
      {:else}<div class="contracts-list">{#each contratti as contratto (contratto.id)}
        <section class="contract-row">
          <div class="contract-heading"><div><strong>{contratto.cliente.nome}</strong><span>€ {Number(contratto.value).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span><small>{contratto.data_creazione} → {contratto.data_fine}</small></div><div class="row-actions"><button type="button" on:click={() => editContratto(contratto)}>Modifica</button><button type="button" class="danger" on:click={() => deleteContratto(contratto)}>Elimina</button></div></div>
          <div class="pool"><span>Pool task</span><div class="task-list">{#each contratto.pool_task as task (`${contratto.id}-${task}`)}<span class="task-chip">{task}<button type="button" aria-label={`Rimuovi ${task}`} on:click={() => deleteTask(contratto, task)}>×</button></span>{/each}</div><div class="add-task"><input placeholder="PROJ-123" value={poolTaskInputs[contratto.id] || ''} on:input={(event) => (poolTaskInputs = { ...poolTaskInputs, [contratto.id]: event.currentTarget.value })} /><button type="button" on:click={() => appendTask(contratto)}>Aggiungi</button></div></div>
        </section>
      {/each}</div>{/if}
    </article>
  </div>
</section>

<style>
  .clienti-section { margin: 1.25rem 0; padding: 1rem; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; }
  .section-header, .contract-heading, .row-actions, .form-actions, .add-task { display: flex; align-items: center; gap: .55rem; }
  .section-header { justify-content: space-between; margin-bottom: 1rem; }
  h2, h3, p { margin-top: 0; } h2 { font-size: 1.1rem; } h3 { font-size: .92rem; } .section-header p, .list-card > p { margin-bottom: 0; color: #64748b; font-size: .82rem; }
  button { border: 0; border-radius: 7px; padding: .42rem .65rem; color: white; background: #2563eb; cursor: pointer; font: inherit; font-size: .78rem; } button:disabled { opacity: .6; cursor: not-allowed; } button.secondary { background: #64748b; } button.danger { background: #dc2626; } .refresh-button { background: #475569; }
  .editor-grid, .data-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; } .editor-card, .list-card { padding: .85rem; border: 1px solid #e2e8f0; border-radius: 9px; background: #f8fafc; }
  label { display: grid; gap: .25rem; margin: .55rem 0; color: #334155; font-size: .78rem; font-weight: 600; } input, select { width: 100%; box-sizing: border-box; padding: .43rem .5rem; border: 1px solid #cbd5e1; border-radius: 6px; background: white; color: #0f172a; font: inherit; } input[readonly] { background: #e2e8f0; color: #475569; }
  .form-actions { margin-top: .8rem; } .feedback { padding: .55rem .7rem; border-radius: 7px; font-size: .82rem; } .feedback.error { background: #fee2e2; color: #991b1b; } .feedback.success { background: #dcfce7; color: #166534; }
  ul { margin: 0; padding: 0; list-style: none; } li, .contract-row { padding: .65rem 0; border-top: 1px solid #e2e8f0; } li:first-child, .contract-row:first-child { border-top: 0; } li, li > div:first-child { display: flex; } li { justify-content: space-between; align-items: center; gap: .5rem; } li > div:first-child { flex-direction: column; } li span, small { color: #64748b; font-size: .75rem; }
  .contracts-list { display: grid; gap: .1rem; } .contract-heading { justify-content: space-between; } .contract-heading > div:first-child { display: grid; gap: .12rem; } .pool { margin-top: .55rem; display: grid; gap: .4rem; font-size: .74rem; color: #475569; } .task-list { display: flex; flex-wrap: wrap; gap: .3rem; } .task-chip { display: inline-flex; align-items: center; gap: .25rem; padding: .2rem .38rem; border-radius: 999px; background: #dbeafe; color: #1e3a8a; font-family: var(--font-mono); font-size: .7rem; } .task-chip button { padding: 0; color: #1e3a8a; background: transparent; font-size: 1rem; line-height: .7; } .add-task input { min-width: 0; }
  @media (max-width: 760px) { .editor-grid, .data-grid { grid-template-columns: 1fr; } .section-header, .contract-heading, li { align-items: flex-start; flex-direction: column; } .row-actions { flex-wrap: wrap; } }
</style>
