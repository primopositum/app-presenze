<script lang="ts">
  import { useTimeEntryFormContext } from '$lib/context/timeEntryForm';
  import { timeEntryReload } from '$lib/stores/timeEntryReload';
  import { useSubmitHours,useUpdateHours } from '$lib/hooks/useSubmitHours';
  import { useRangeOverrideTimeEntries } from '$lib/hooks/useTimeEntries';
  import { DateInput } from 'date-picker-svelte';

  const { state, closeForm } = useTimeEntryFormContext();

  let submitting = false;
  let error: string | null = null;

  let date = '';
  let oreTot = 8;
  let type = 1;
  let note = '';
  let utenteId: number | null = null;

  let mode: 'create' | 'update' = 'create';
  let teId: number | null = null;
  let rangeOverride = false;
  let dataS = '';
  let dataE = '';
  let dataSDate: Date | null = null;
  let dataEDate: Date | null = null;
  let lastArgsKey = '';

  const typeOptions = [
    { value: 1, label: 'Lavoro' },
    { value: 2, label: 'Ferie' },
    { value: 3, label: 'Versamento Banca Ore' },
    { value: 4, label: 'Prelievo Banca Ore' },
    { value: 5, label: 'Malattia' },
    { value: 6, label: 'Permesso Ordinario' },
    { value: 7, label: 'Permesso Studio' },
    { value: 8, label: 'Permesso 104' },
    { value: 9, label: 'Permesso Ex fest' },
    { value: 10, label: 'Permesso R.O.L.' },
    { value: 11, label: 'Congedo di maternita' },
    { value: 12, label: 'Sciopero' },
    { value: 14, label: 'Visite mediche L.106/25' }
  ];

  $: if ($state.open && $state.args) {
    const key = [
      $state.args.mode ?? 'create',
      $state.args.teId ?? '',
      $state.args.date,
      $state.args.oreTot,
      $state.args.type,
      $state.args.note ?? '',
      $state.args.utenteId ?? ''
    ].join('|');

    if (key !== lastArgsKey) {
      mode = $state.args.mode ?? 'create';
      teId = $state.args.teId ?? null;

      date = $state.args.date;
      oreTot = $state.args.oreTot;
      type = $state.args.type;
      note = $state.args.note ?? '';
      utenteId = $state.args.utenteId ?? null;
      dataS = $state.args.date;
      dataE = $state.args.date;
      dataSDate = toDateOrNull(dataS);
      dataEDate = toDateOrNull(dataE);
      rangeOverride = false;
      error = null;
      lastArgsKey = key;
    }
  } else {
    lastArgsKey = '';
  }

  function handleClose() {
    if (submitting) return;
    closeForm();
  }

  function toDateOrNull(isoDate: string) {
    if (!isoDate) return null;
    const [y, m, d] = isoDate.split('-').map(Number);
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
  }

  function toIsoDateOrEmpty(dateValue: Date | null) {
    if (!dateValue) return '';
    const y = dateValue.getFullYear();
    const m = String(dateValue.getMonth() + 1).padStart(2, '0');
    const d = String(dateValue.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  $: dataS = toIsoDateOrEmpty(dataSDate);
  $: dataE = toIsoDateOrEmpty(dataEDate);

  function validate(): string | null {
    if (utenteId == null) return 'Utente non disponibile';
    if (type == null || Number.isNaN(type)) return 'Tipo non valido';
    if (rangeOverride) {
      if (mode === 'update') return 'Range override non disponibile in modifica';
      if (!dataS || !dataE) return 'Date range obbligatorie';
      if (new Date(dataS).getTime() > new Date(dataE).getTime()) return 'Intervallo date non valido';
      return null;
    }
    if (!date) return 'Data obbligatoria';
    if (oreTot == null || Number.isNaN(oreTot) || oreTot < 0) return 'Ore non valide';
    if (mode === 'update' && !teId) return 'ID time entry mancante per aggiornamento';
    return null;
  }

  async function handleSubmit() {
    error = validate();
    if (error) return;

    submitting = true;
    try {
      if (rangeOverride) {
        const rangeOverrideSubmit = useRangeOverrideTimeEntries();
        await rangeOverrideSubmit({
          utenteId: utenteId!,
          dataS,
          dataE,
          type
        });
      } else if (mode === 'create') {
        const submitHours = useSubmitHours({ utenteId: utenteId!, validationLevel: 1 });
        await submitHours({ date, hours: oreTot, type, note });
      } else {
      const updateHours = useUpdateHours({ utenteId:utenteId!, TimeEntryId: teId! });
        await updateHours({
          date,
          type,
          hours: oreTot,
          note
        });
      }

      timeEntryReload.bump();
      closeForm();
    } catch (e: any) {
      error = e?.message ?? 'Errore durante il salvataggio';
    } finally {
      submitting = false;
    }
  }
</script>

{#if $state.open}
  <div class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" on:click={handleClose}>
    <div class="card" on:click|stopPropagation>
      <div class="card2">
        <div class="form">
          <p id="heading">
            {mode === 'update' ? 'Modifica Time Entry' : 'Aggiungi Time Entry'}
          </p>

          {#if !rangeOverride}
            <div class="flex items-center justify-center">
              <i class="fa-solid fa-calendar-day input-icon-fa"></i>
              <span class="text-display">{date}</span>
            </div>

            <div class="field">
              <i class="fa-solid fa-clock input-icon-fa"></i>
              <input
                class="input-field"
                type="number"
                min="0"
                step="0.25"
                bind:value={oreTot}
                placeholder="Ore lavorate"
              />
            </div>
          {:else}
            <div class="field">
              <i class="fa-solid fa-calendar-day input-icon-fa"></i>
              <DateInput
                class="range-date-input"
                bind:value={dataSDate}
                format="yyyy-MM-dd"
                placeholder="YYYY-MM-DD"
                closeOnSelection={true}
              />
            </div>

            <div class="field">
              <i class="fa-solid fa-calendar-check input-icon-fa"></i>
              <DateInput
                class="range-date-input"
                bind:value={dataEDate}
                format="yyyy-MM-dd"
                placeholder="YYYY-MM-DD"
                closeOnSelection={true}
              />
            </div>
          {/if}

          <div class="field">
            <i class="fa-solid fa-tag input-icon-fa"></i>
            <select class="input-field" bind:value={type}>
              {#each typeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </div>

          <div class="field note-field">
            <i class="fa-solid fa-note-sticky input-icon-fa"></i>
            <textarea
              class="input-field note-input"
              bind:value={note}
              rows="3"
              placeholder="Note (opzionale)"
            ></textarea>
          </div>

          {#if error}
            <p class="error-text">{error}</p>
          {/if}

          <div class="btn">
            <button class="button2" type="button" on:click={handleClose}>
              <i class="fa-solid fa-xmark"></i> Annulla
            </button>

            {#if mode !== 'update'}
              <label class="magic-toggle" class:is-active={rangeOverride} title="Attiva range override">
                <input type="checkbox" bind:checked={rangeOverride} />
                <i class="fa-solid fa-wand-magic-sparkles"></i>
              </label>
            {/if}

            <button class="button1" type="button" on:click={handleSubmit} disabled={submitting}>
              {#if submitting}
                <i class="fa-solid fa-spinner fa-spin"></i>
              {:else}
                <i class="fa-solid fa-check"></i>
                {#if rangeOverride}
                  Applica
                {:else}
                  {mode === 'update' ? 'Salva modifiche' : 'Salva'}
                {/if}
              {/if}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

  .card {
    background-image: linear-gradient(
      163deg,
      var(--color-auto-accent-500) 0%,
      var(--color-auto-primary) 100%
    );
    border-radius: 22px;
    transition: all 0.3s;
    width: 100%;
    max-width: 350px;
  }

  .card2 {
    border-radius: 20px;
    background-color: #171717;
    transition: all 0.2s;
  }

  .card2:hover {
    transform: scale(0.98);
  }

  .card:hover {
    box-shadow: 0px 0px 30px 1px rgba(249, 115, 22, 0.35);
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 2em;
  }

  #heading {
    text-align: center;
    margin-bottom: 1em;
    color: var(--color-auto-primary-contrast);
    font-size: 1.2em;
    font-weight: bold;
  }

  .field {
    display: flex;
    align-items: center;
    gap: 12px;
    border-radius: 25px;
    padding: 0.8em 1.2em;
    background-color: #171717;
    box-shadow: inset 2px 5px 10px rgb(5, 5, 5);
  }

  .input-icon-fa {
    color: var(--color-auto-accent-500);
    font-size: 1.1em;
    width: 20px;
    text-align: center;
  }

  .text-display {
    color: var(--color-auto-accent-200);
    font-size: 0.95em;
    font-weight: 500;
  }

  .input-field {
    background: none;
    border: none;
    outline: none;
    width: 100%;
    color: var(--color-auto-accent-100);
    font-size: 0.9em;
  }

  .note-field {
    align-items: flex-start;
  }

  .note-input {
    resize: vertical;
    min-height: 72px;
  }

  :global(.range-date-input) {
    width: 100%;
    --date-input-width: 100%;
    --date-picker-foreground: var(--color-auto-accent-100);
    --date-picker-background: #171717;
    --date-picker-highlight-border: var(--color-auto-accent-500);
    --date-picker-highlight-shadow: rgba(249, 115, 22, 0.45);
    --date-picker-selected-background: rgba(249, 115, 22, 0.25);
    --date-picker-selected-color: var(--color-auto-accent-100);
    --date-picker-today-border: rgba(249, 115, 22, 0.6);
  }

  :global(.range-date-input input) {
    width: 100%;
    border-radius: 12px !important;
    border-color: rgba(249, 115, 22, 0.35) !important;
    background: #171717 !important;
    color: var(--color-auto-accent-100) !important;
    font-size: 0.9em;
    padding: 0.45rem 0.7rem !important;
  }

  :global(.range-date-input .date-time-picker) {
    border-radius: 14px !important;
    border-color: rgba(249, 115, 22, 0.4) !important;
    background: #171717 !important;
  }

  select.input-field option {
    background-color: #171717;
    color: white;
  }

  .error-text {
    text-align: center;
    color: var(--color-auto-danger-700);
    font-size: 0.8em;
  }

  .btn {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-top: 1em;
  }

  .button1,
  .button2 {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.7em 1.4em;
    border-radius: 10px;
    border: none;
    cursor: pointer;
    font-weight: bold;
    transition: 0.3s;
    font-size: 0.85em;
  }

  .button1 {
    background-color: var(--color-auto-accent-500);
    color: var(--color-auto-accent-700);
  }

  .button1:hover:not(:disabled) {
    background-color: var(--color-auto-accent-100);
    box-shadow: 0 0 15px rgba(249, 115, 22, 0.6);
  }

  .button2 {
    background-color: var(--color-auto-primary);
    color: var(--color-auto-primary-contrast);
  }

  .magic-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background-color: var(--color-auto-primary);
    color: var(--color-auto-muted);
    cursor: pointer;
    transition: 0.3s;
  }

  .magic-toggle input {
    display: none;
  }

  .magic-toggle:hover {
    color: var(--color-auto-accent-200);
  }

  .magic-toggle.is-active {
    color: var(--color-auto-accent-700);
    background-color: var(--color-auto-accent-500);
    box-shadow: 0 0 15px rgba(249, 115, 22, 0.6);
  }

  .magic-toggle.is-disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 520px) {
    .form {
      padding: 1.4em;
    }

    .field {
      gap: 10px;
      padding: 0.7em 1em;
    }

    .btn {
      flex-direction: column;
      gap: 8px;
    }

    .button1,
    .button2 {
      width: 100%;
      justify-content: center;
    }

    .magic-toggle {
      width: 100%;
    }
  }
</style>
