<script lang="ts">
  import { onMount } from 'svelte';
  import {
    jiraReferencesAddJiraProjects,
    jiraReferencesDelete,
    jiraReferencesGet,
    type JiraReference
  } from '$lib/services/jira';

  let references: JiraReference[] = [];
  let loading = true;
  let error = '';
  let actionError = '';
  let actionMessage = '';
  let selectedReferenceId: number | null = null;
  let deleting = false;
  let importingProjects = false;

  const priceFormatter = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR'
  });

  function formatPrice(price: number) {
    return priceFormatter.format(Number(price || 0));
  }

  function sortReferences(items: JiraReference[]) {
    return [...items].sort((first, second) => first.name.localeCompare(second.name, 'it'));
  }

  async function loadReferences() {
    loading = true;
    error = '';
    try {
      references = sortReferences(await jiraReferencesGet());
    } catch (cause: any) {
      error = String(cause?.message || cause || 'Errore caricamento riferimenti prezzo');
    } finally {
      loading = false;
    }
  }

  async function deleteSelectedReference() {
    if (selectedReferenceId === null) return;
    actionError = '';
    actionMessage = '';
    deleting = true;
    try {
      await jiraReferencesDelete([selectedReferenceId]);
      references = references.filter((reference) => reference.id !== selectedReferenceId);
      selectedReferenceId = null;
      actionMessage = 'Riferimento eliminato.';
    } catch (cause: any) {
      actionError = String(cause?.message || cause || 'Errore eliminazione riferimento');
    } finally {
      deleting = false;
    }
  }

  async function addJiraProjects() {
    actionError = '';
    actionMessage = '';
    importingProjects = true;
    try {
      const response = await jiraReferencesAddJiraProjects();
      references = sortReferences([...references, ...response.items]);
      actionMessage = response.count > 0
        ? `${response.count} progetti Jira aggiunti.`
        : 'Tutti i progetti Jira sono gia presenti.';
    } catch (cause: any) {
      actionError = String(cause?.message || cause || 'Errore importazione progetti Jira');
    } finally {
      importingProjects = false;
    }
  }

  onMount(() => {
    void loadReferences();
  });
</script>

<section class="calculated-pricing" data-history-hover>
  <div class="pricing-head">
    <div>
      <h3>Riferimenti prezzo Jira</h3>
      <p>Valori disponibili per il calcolo dei prezzi delle attivita Jira.</p>
    </div>
    <div class="pricing-actions">
      <button type="button" class="delete-btn" on:click={deleteSelectedReference} disabled={deleting || selectedReferenceId === null}>
        {deleting ? 'Elimino...' : 'Elimina'}
      </button>
      <button type="button" class="import-btn" on:click={addJiraProjects} disabled={importingProjects}>
        {importingProjects ? 'Importo...' : 'Aggiungi progetti Jira'}
      </button>
      <button type="button" on:click={loadReferences} disabled={loading}>
        {loading ? 'Aggiorno...' : 'Aggiorna'}
      </button>
    </div>
  </div>

  {#if actionError}
    <p class="state error">{actionError}</p>
  {:else if actionMessage}
    <p class="state success">{actionMessage}</p>
  {/if}

  {#if loading && references.length === 0}
    <p class="state">Caricamento riferimenti prezzo...</p>
  {:else if error}
    <p class="state error">{error}</p>
  {:else if references.length === 0}
    <p class="state">Nessun riferimento prezzo disponibile.</p>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col" class="selection-column">Seleziona</th>
            <th scope="col">Nome</th>
            <th scope="col">Prezzo</th>
          </tr>
        </thead>
        <tbody>
          {#each references as reference (reference.id)}
            <tr data-history-hover>
              <td class="selection-column">
                <input
                  type="radio"
                  name="selected-jira-reference"
                  checked={selectedReferenceId === reference.id}
                  on:change={() => (selectedReferenceId = reference.id)}
                  aria-label={`Seleziona ${reference.name}`}
                />
              </td>
              <td>{reference.name}</td>
              <td>{formatPrice(reference.price)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>

<style>
  .calculated-pricing {
    margin-top: 0.95rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    padding: 0.85rem 0.95rem;
  }

  .pricing-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.7rem;
  }

  .pricing-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.35rem;
  }

  h3 {
    margin: 0;
    color: #0f172a;
    font-family: var(--font-mono);
    font-size: 0.9rem;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  .pricing-head p,
  .state {
    margin: 0.35rem 0 0;
    color: #475569;
    font-family: var(--font-mono);
    font-size: 0.74rem;
    line-height: 1.35;
  }

  .pricing-actions button {
    min-height: 32px;
    border: 1px solid #d97706;
    border-radius: 8px;
    background: #f97316;
    color: #fff;
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    padding: 0.3rem 0.55rem;
  }

  .pricing-actions button:hover:not(:disabled) {
    background: #ea580c;
  }

  .pricing-actions button:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }

  .state.error {
    color: #b91c1c;
  }

  .state.success {
    color: #166534;
  }

  .delete-btn {
    border-color: #dc2626 !important;
    background: #dc2626 !important;
  }

  .delete-btn:hover:not(:disabled) {
    background: #b91c1c !important;
  }

  .import-btn {
    border-color: #2563eb !important;
    background: #2563eb !important;
  }

  .import-btn:hover:not(:disabled) {
    background: #1d4ed8 !important;
  }

  .table-wrap {
    margin-top: 0.7rem;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
  }

  th,
  td {
    border: 1px solid #e2e8f0;
    padding: 0.48rem 0.6rem;
    text-align: left;
  }

  th {
    background: #f8fafc;
    color: #475569;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  td {
    color: #0f172a;
    font-size: 0.78rem;
  }

  th:last-child,
  td:last-child {
    text-align: right;
    white-space: nowrap;
  }

  .selection-column {
    width: 1%;
    text-align: center !important;
    white-space: nowrap;
  }

  @media (max-width: 720px) {
    .pricing-head {
      flex-direction: column;
    }

    .pricing-actions {
      justify-content: flex-start;
    }

  }
</style>
