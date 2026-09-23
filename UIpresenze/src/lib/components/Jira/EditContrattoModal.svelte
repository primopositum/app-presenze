<script lang="ts">
  import { onMount } from 'svelte';
  import { useContrattoClienteUpdate } from '$lib/hooks/useClienti';
  import type { Cliente, ContrattoCliente } from '$lib/services/clienti';

  export let contratto: ContrattoCliente;
  export let clienti: Cliente[] = [];
  export let onSaved: (() => Promise<void> | void) | undefined = undefined;
  export let onClose: (() => void) | undefined = undefined;
  export let onNotify: ((message: string, success: boolean) => void) | undefined = undefined;

  let clienteId = String(contratto.client_id);
  let contractId = contratto.contract_id;
  let value = String(contratto.value);
  const hasPeriodicity = Boolean(contratto.periodicity);
  let periodicValue = String(contratto.periodicity?.periodic_value ?? '');
  let periodDays = String(contratto.periodicity?.period_days ?? '');
  let firstMeetingDate = contratto.periodicity?.first_meeting_date ?? '';
  let notificationDays = String(contratto.periodicity?.notification_days ?? '');
  let saving = false;
  let clienteSelect: HTMLSelectElement | null = null;

  function close() {
    if (!saving) onClose?.();
  }

  function closeOnEscape(event: KeyboardEvent) {
    if (event.key === 'Escape') close();
  }

  async function saveContratto() {
    saving = true;
    try {
      const parsedClienteId = Number(clienteId);
      if (!Number.isInteger(parsedClienteId) || parsedClienteId <= 0) throw new Error('Seleziona un cliente.');
      const normalizedContractId = String(contractId ?? '').trim();
      if (!normalizedContractId) throw new Error('L\'ID del contratto è obbligatorio.');
      const normalizedValue = String(value ?? '').trim();
      if (!normalizedValue) throw new Error('Il valore del contratto è obbligatorio.');

      const normalizedPeriodicValue = String(periodicValue ?? '').trim();
      const parsedPeriodicValue = Number(normalizedPeriodicValue);
      const parsedPeriodDays = Number(periodDays);
      const parsedNotificationDays = Number(notificationDays);
      if (
        hasPeriodicity &&
        (!normalizedPeriodicValue ||
          !Number.isFinite(parsedPeriodicValue) ||
          parsedPeriodicValue <= 0 ||
          !firstMeetingDate ||
          !Number.isInteger(parsedPeriodDays) ||
          parsedPeriodDays <= 0 ||
          !Number.isInteger(parsedNotificationDays) ||
          parsedNotificationDays <= 0)
      ) {
        throw new Error('Per la periodicità inserisci valore, periodo, primo incontro e preavviso validi.');
      }

      await useContrattoClienteUpdate(contratto.id, {
        contract_id: normalizedContractId,
        client_id: parsedClienteId,
        value: normalizedValue,
        pool_task: contratto.pool_task,
        ...(hasPeriodicity
          ? {
              periodicity: {
                periodic_value: normalizedPeriodicValue,
                period_days: parsedPeriodDays,
                first_meeting_date: firstMeetingDate,
                notification_days: parsedNotificationDays
              }
            }
          : {})
      });
      onClose?.();
      onNotify?.('Contratto commerciale salvato.', true);
      await onSaved?.();
    } catch (cause: any) {
      onNotify?.(String(cause?.message || cause || 'Impossibile salvare il contratto.'), false);
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    clienteSelect?.focus();
  });
</script>

<svelte:window on:keydown={closeOnEscape} />

<div class="edit-overlay" role="dialog" aria-modal="true" aria-labelledby="edit-contratto-title" data-history-hover-exclude>
  <button class="overlay-backdrop" type="button" data-history-hover-exclude aria-label="Chiudi modifica contratto" on:click={close}></button>

  <form class="edit-card" on:submit|preventDefault={saveContratto}>
    <div class="card-title">
      <div>
        <strong id="edit-contratto-title">Modifica contratto</strong>
        <small>{contratto.contract_id}{#if contratto.client} · {contratto.client.nome}{/if}</small>
      </div>
      <button type="button" class="close" data-history-hover-exclude on:click={close} disabled={saving} aria-label="Chiudi modifica contratto">×</button>
    </div>
    <label>Cliente <select bind:this={clienteSelect} bind:value={clienteId} required><option value="">Seleziona cliente</option>{#each clienti as cliente (cliente.id)}<option value={String(cliente.id)}>{cliente.nome}</option>{/each}</select></label>
    <label>ID contratto <input bind:value={contractId} required /></label>
    <label>Valore <input type="number" min="0" step="0.01" bind:value required /></label>
    <div class="date-fields">
      <label>Data inizio <input type="date" value={contratto.start_date} readonly /></label>
      <label>Data fine <input type="date" value={contratto.end_date || ''} readonly /></label>
    </div>
    {#if hasPeriodicity}
      <fieldset class="periodicity-fields">
        <legend>Periodicità</legend>
        <label>Valore periodico <input type="number" min="0.01" step="0.01" bind:value={periodicValue} required /></label>
        <label>Periodo (giorni) <input type="number" min="1" step="1" bind:value={periodDays} required /></label>
        <label>Primo incontro <input type="date" bind:value={firstMeetingDate} required /></label>
        <label>Preavviso (giorni) <input type="number" min="1" step="1" bind:value={notificationDays} required /></label>
      </fieldset>
    {/if}
    <div class="form-actions">
      <button type="submit" data-history-hover-exclude disabled={saving || clienti.length === 0}>{saving ? 'Salvo...' : 'Salva contratto'}</button>
      <button type="button" class="secondary" data-history-hover-exclude on:click={close} disabled={saving}>Annulla</button>
    </div>
  </form>
</div>

<style>
  .edit-overlay { position: fixed; inset: 0; z-index: 80; display: grid; place-items: center; padding: 1rem; }
  .overlay-backdrop { position: absolute; inset: 0; width: 100%; height: 100%; padding: 0; border: 0; background: rgb(15 23 42 / .72); cursor: default; animation: fade-in .25s ease; }
  .edit-card { position: relative; z-index: 1; box-sizing: border-box; display: grid; align-content: start; gap: .55rem; width: min(100%, 400px); max-height: calc(100dvh - 2rem); padding: 1rem; border: 1px solid #c4b5fd; border-radius: 12px; background: #fff; box-shadow: 0 18px 48px rgb(15 23 42 / .35); text-align: left; overflow-y: auto; overscroll-behavior-y: contain; scrollbar-gutter: stable; animation: center-card .4s ease; }
  .card-title { display: flex; align-items: center; gap: .5rem; color: #0f172a; }
  .card-title > div { display: grid; flex: 1; min-width: 0; gap: .1rem; }
  .card-title small { color: #475569; font-size: .72rem; overflow-wrap: anywhere; }
  label { display: grid; gap: .22rem; color: #334155; font-size: .73rem; font-weight: 600; }
  input, select { width: 100%; box-sizing: border-box; padding: .38rem .45rem; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; }
  input[readonly] { background: #f1f5f9; color: #475569; cursor: default; }
  .date-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .55rem; }
  .periodicity-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .55rem; margin: 0; padding: .65rem; border: 1px solid #ddd6fe; border-radius: 8px; }
  .periodicity-fields legend { padding: 0 .25rem; color: #6d28d9; font-size: .75rem; font-weight: 700; }
  .form-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .15rem; }
  .form-actions button { width: fit-content; max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: #fff; background: #7c3aed; font: inherit; cursor: pointer; overflow-wrap: anywhere; }
  .form-actions .secondary { background: #64748b; }
  button:disabled { opacity: .6; cursor: not-allowed; }
  .close { flex: 0 0 auto; border: 0; background: transparent; color: #475569; font-size: 1.35rem; cursor: pointer; }
  @keyframes center-card { from { opacity: .45; transform: scale(.88); } to { opacity: 1; transform: scale(1); } }
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
  @media (max-width: 480px) { .date-fields, .periodicity-fields { grid-template-columns: 1fr; } }
  @media (prefers-reduced-motion: reduce) { .overlay-backdrop, .edit-card { animation: none; } }
</style>
