<script lang="ts">
  import { onMount } from 'svelte';
  import {
    jiraReferencesAddJiraProjects,
    jiraReferencesDelete,
    jiraReferencesGet,
    jiraReferencesPut,
    type JiraReference,
    type JiraYearWorklogProject
  } from '$lib/services/jira';
  import ToastState from '$lib/components/ToastState.svelte';

  let references: JiraReference[] = [];
  export let selectedProjectNames: string[] = [];
  export let selectedProjectWorklogs: JiraYearWorklogProject[] = [];
  let loading = true;
  let error = '';
  let actionError = '';
  let actionMessage = '';
  let selectedReferenceId: number | null = null;
  let selectedPrice = '';
  let deleting = false;
  let importingProjects = false;
  let savingPrice = false;
  let toastOpen = false;
  let toastSuccess = true;
  let toastMessage = '';

  const priceFormatter = new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR'
  });

  function formatPrice(price: number) {
    return priceFormatter.format(Number(price || 0));
  }

  function formatHours(seconds: number) {
    return `${(Math.max(0, Number(seconds || 0)) / 3600).toLocaleString('it-IT', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 1
    })} h`;
  }

  function sortReferences(items: JiraReference[]) {
    return [...items].sort((first, second) => first.name.localeCompare(second.name, 'it'));
  }

  function normalizeReferenceName(value: string) {
    return String(value || '').trim().toLocaleLowerCase('it');
  }

  function selectReference(reference: JiraReference) {
    selectedReferenceId = reference.id;
    selectedPrice = String(reference.price);
  }

  function showToast(success: boolean, message: string) {
    toastSuccess = success;
    toastMessage = message;
    toastOpen = false;
    requestAnimationFrame(() => {
      toastOpen = true;
    });
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
      selectedPrice = '';
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

  async function saveSelectedPrice() {
    if (selectedReferenceId === null) return;
    const price = Number(selectedPrice);
    actionError = '';
    actionMessage = '';

    if (!Number.isFinite(price)) {
      actionError = 'Inserisci un prezzo valido.';
      return;
    }

    savingPrice = true;
    try {
      const response = await jiraReferencesPut([{ id: selectedReferenceId, price }]);
      const updatedReference = response.items[0];
      if (!updatedReference) throw new Error('Risposta aggiornamento non valida');

      references = references.map((reference) =>
        reference.id === updatedReference.id ? updatedReference : reference
      );
      selectedReferenceId = null;
      selectedPrice = '';
      showToast(true, `Prezzo di ${updatedReference.name} aggiornato.`);
    } catch (cause: any) {
      const message = String(cause?.message || cause || 'Errore aggiornamento prezzo');
      actionError = message;
      showToast(false, message);
    } finally {
      savingPrice = false;
    }
  }

  $: selectedProjectNameSet = new Set(selectedProjectNames.map(normalizeReferenceName).filter(Boolean));
  $: visibleReferences = selectedProjectNameSet.size > 0
    ? references.filter((reference) => selectedProjectNameSet.has(normalizeReferenceName(reference.name)))
    : references;
  $: if (selectedReferenceId !== null && !visibleReferences.some((reference) => reference.id === selectedReferenceId)) {
    selectedReferenceId = null;
    selectedPrice = '';
  }
  $: selectedReference = visibleReferences.find((reference) => reference.id === selectedReferenceId) || null;
  $: selectedProjectReference = selectedProjectNameSet.size > 0 ? visibleReferences[0] || null : null;
  $: selectedProjectWorklog = selectedProjectWorklogs[0] || null;
  $: selectedProjectSeconds = Math.max(0, Number(selectedProjectWorklog?.total_seconds || 0));
  $: selectedProjectHourlyPrice = selectedProjectReference && selectedProjectSeconds > 0
    ? selectedProjectReference.price / (selectedProjectSeconds / 3600)
    : null;
  $: pricedIssues = selectedProjectWorklog && selectedProjectHourlyPrice !== null
    ? selectedProjectWorklog.issues
      .filter((issue) => Number(issue.total_seconds || 0) > 0)
      .map((issue) => ({
        key: issue.issue_key,
        summary: issue.issue_summary || '-',
        seconds: Math.max(0, Number(issue.total_seconds || 0)),
        price: (Math.max(0, Number(issue.total_seconds || 0)) / 3600) * selectedProjectHourlyPrice
      }))
    : [];

  onMount(() => {
    void loadReferences();
  });
</script>

<section
  class="calculated-pricing"
  class:references-browser={selectedProjectNames.length === 0}
  data-history-hover
>
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

  {#if selectedReference}
    <div class="edit-price">
      <label for="selected-reference-price">Prezzo di {selectedReference.name}</label>
      <input
        id="selected-reference-price"
        type="number"
        bind:value={selectedPrice}
        step="0.01"
        inputmode="decimal"
        disabled={savingPrice}
      />
      <button type="button" class="save-btn" on:click={saveSelectedPrice} disabled={savingPrice}>
        {savingPrice ? 'Salvo...' : 'Salva prezzo'}
      </button>
    </div>
  {/if}

  {#if selectedProjectNames.length > 0}
    {#if !selectedProjectReference}
      <p class="state">Nessun prezzo di riferimento per il progetto Jira selezionato.</p>
    {:else if !selectedProjectWorklog || selectedProjectSeconds === 0}
      <p class="state">Nessuna ora lavorata nel periodo selezionato per questo progetto.</p>
    {:else}
      <section class="project-pricing" aria-label="Calcolo prezzo progetto selezionato">
        <div>
          <span>Prezzo progetto</span>
          <strong>{formatPrice(selectedProjectReference.price)}</strong>
        </div>
        <div>
          <span>Ore lavorate periodo</span>
          <strong>{formatHours(selectedProjectSeconds)}</strong>
        </div>
        <div>
          <span>Prezzo orario</span>
          <strong>{formatPrice(selectedProjectHourlyPrice || 0)}/h</strong>
        </div>
      </section>

      <div class="issue-pricing-table">
        <h4>Prezzo per issue</h4>
        {#if pricedIssues.length === 0}
          <p class="state">Nessuna issue con ore nel periodo selezionato.</p>
        {:else}
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Issue</th>
                  <th scope="col">Ore periodo</th>
                  <th scope="col">Prezzo</th>
                </tr>
              </thead>
              <tbody>
                {#each pricedIssues as issue (issue.key)}
                  <tr data-history-hover>
                    <td><strong>{issue.key}</strong> <span>{issue.summary}</span></td>
                    <td>{formatHours(issue.seconds)}</td>
                    <td>{formatPrice(issue.price)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}
  {/if}

  {#if actionError}
    <p class="state error">{actionError}</p>
  {:else if actionMessage}
    <p class="state success">{actionMessage}</p>
  {/if}

  {#if loading && references.length === 0}
    <p class="state">Caricamento riferimenti prezzo...</p>
  {:else if error}
    <p class="state error">{error}</p>
  {:else if visibleReferences.length === 0}
    <p class="state">
      {selectedProjectNames.length > 0
        ? 'Nessun riferimento prezzo per il progetto Jira selezionato.'
        : 'Nessun riferimento prezzo disponibile.'}
    </p>
  {:else}
    <div class="table-wrap" class:references-table-scroll={selectedProjectNames.length === 0}>
      <table>
        <thead>
          <tr>
            <th scope="col" class="selection-column">Seleziona</th>
            <th scope="col">Nome</th>
            <th scope="col">Prezzo</th>
          </tr>
        </thead>
        <tbody>
          {#each visibleReferences as reference (reference.id)}
            <tr data-history-hover>
              <td class="selection-column">
                <input
                  type="radio"
                  name="selected-jira-reference"
                  checked={selectedReferenceId === reference.id}
                  on:change={() => selectReference(reference)}
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

<ToastState bind:open={toastOpen} success={toastSuccess} message={toastMessage} />

<style>
  .calculated-pricing {
    margin-top: 0.95rem;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    padding: 0.85rem 0.95rem;
  }

  .calculated-pricing.references-browser {
    display: flex;
    flex-direction: column;
    height: 50vh;
    overflow: hidden;
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

  .edit-price {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 130px auto;
    align-items: end;
    gap: 0.5rem;
    margin-top: 0.7rem;
  }

  .edit-price label {
    color: #475569;
    font-family: var(--font-mono);
    font-size: 0.74rem;
  }

  .edit-price input {
    min-width: 0;
    min-height: 32px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #fff;
    color: #0f172a;
    font-family: var(--font-mono);
    font-size: 0.76rem;
    padding: 0.3rem 0.45rem;
  }

  .save-btn {
    min-height: 32px;
    border: 1px solid #15803d;
    border-radius: 8px;
    background: #16a34a;
    color: #fff;
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    padding: 0.3rem 0.55rem;
  }

  .save-btn:hover:not(:disabled) {
    background: #15803d;
  }

  .save-btn:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }

  .project-pricing {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.5rem;
    margin-top: 0.7rem;
  }

  .project-pricing div {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #f8fafc;
    padding: 0.48rem 0.55rem;
  }

  .project-pricing span,
  .project-pricing strong {
    display: block;
    font-family: var(--font-mono);
  }

  .project-pricing span {
    color: #64748b;
    font-size: 0.67rem;
  }

  .project-pricing strong {
    margin-top: 0.18rem;
    color: #0f172a;
    font-size: 0.84rem;
  }

  .issue-pricing-table {
    margin-top: 0.7rem;
  }

  .issue-pricing-table h4 {
    margin: 0;
    color: #334155;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    text-transform: uppercase;
  }

  .issue-pricing-table td:first-child strong {
    color: #0f172a;
  }

  .issue-pricing-table td:first-child span {
    color: #475569;
  }

  .table-wrap {
    margin-top: 0.7rem;
    overflow-x: auto;
  }

  .references-browser .references-table-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
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

    .edit-price {
      grid-template-columns: 1fr;
    }

    .project-pricing {
      grid-template-columns: 1fr;
    }

  }
</style>
