<script lang="ts">
  import { useContrattoClienteCreate } from '$lib/hooks/useClienti';
  import type { Cliente } from '$lib/services/clienti';

  export let clienti: Cliente[] = [];
  export let onCreated: (() => Promise<void> | void) | undefined = undefined;
  export let active = false;
  export let onSelect: (() => void) | undefined = undefined;
  export let onClose: (() => void) | undefined = undefined;
  export let onNotify: ((message: string, success: boolean) => void) | undefined = undefined;

  let clienteId = '';
  let contractId = '';
  let value = '';
  let startDate = '';
  let endDate = '';
  let isPeriodic = false;
  let periodicValue = '';
  let periodDays = '';
  let firstMeetingDate = '';
  let notificationDays = '';
  let saving = false;

  async function createContratto() {
    saving = true;
    try {
      const parsedClienteId = Number(clienteId);
      if (!Number.isInteger(parsedClienteId) || parsedClienteId <= 0) throw new Error('Seleziona un cliente.');
      const normalizedContractId = String(contractId ?? '').trim();
      const normalizedValue = String(value ?? '').trim();
      if (!normalizedContractId || !normalizedValue || !startDate || !endDate) throw new Error('ID contratto, valore e date sono obbligatori.');
      const parsedPeriodDays = Number(periodDays);
      const parsedNotificationDays = Number(notificationDays);
      const normalizedPeriodicValue = String(periodicValue ?? '').trim();
      const parsedPeriodicValue = Number(normalizedPeriodicValue);
      if (isPeriodic && (
        !normalizedPeriodicValue ||
        !Number.isFinite(parsedPeriodicValue) || parsedPeriodicValue <= 0 ||
        !firstMeetingDate ||
        !Number.isInteger(parsedPeriodDays) || parsedPeriodDays <= 0 ||
        !Number.isInteger(parsedNotificationDays) || parsedNotificationDays <= 0
      )) {
        throw new Error('Per la periodicità inserisci valore, periodo, primo incontro e preavviso validi.');
      }
      await useContrattoClienteCreate({
        contract_id: normalizedContractId,
        client_id: parsedClienteId,
        value: normalizedValue,
        pool_task: [],
        start_date: startDate,
        end_date: endDate,
        ...(isPeriodic
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
      clienteId = '';
      contractId = '';
      value = '';
      startDate = '';
      endDate = '';
      isPeriodic = false;
      periodicValue = '';
      periodDays = '';
      firstMeetingDate = '';
      notificationDays = '';
      onClose?.();
      onNotify?.('Contratto commerciale creato.', true);
      await onCreated?.();
    } catch (cause: any) {
      onNotify?.(String(cause?.message || cause || 'Impossibile creare il contratto.'), false);
    } finally {
      saving = false;
    }
  }
</script>

<div class="flip-card" class:flipped={active}>
  <div class="flip-card-inner">
    <button class="card-face card-front" type="button" data-history-hover-exclude on:click={() => onSelect?.()} disabled={clienti.length === 0}>
      <strong>Crea contratto</strong>
      <small>{clienti.length ? 'Collega un cliente e definisci le date' : 'Crea prima un cliente'}</small>
    </button>

    <form class="card-face card-back" on:submit|preventDefault={createContratto}>
      <div class="card-title"><strong>Crea contratto</strong><button type="button" class="close" data-history-hover-exclude on:click={() => onClose?.()} aria-label="Torna alla scelta di creazione">×</button></div>
      <label>Cliente <select bind:value={clienteId} required><option value="">Seleziona cliente</option>{#each clienti as cliente (cliente.id)}<option value={String(cliente.id)}>{cliente.nome}</option>{/each}</select></label>
      <label>ID contratto <input bind:value={contractId} required /></label>
      <label>Valore <input type="number" min="0" step="0.01" bind:value required /></label>
      <label>Data inizio <input type="date" bind:value={startDate} required /></label>
      <label>Data fine <input type="date" bind:value={endDate} required /></label>
      <label class="periodicity-toggle">
        <input type="checkbox" bind:checked={isPeriodic} />
        Contratto periodico
      </label>
      {#if isPeriodic}
        <fieldset class="periodicity-fields">
          <legend>Periodicità</legend>
          <label>Valore periodico <input type="number" min="0.01" step="0.01" bind:value={periodicValue} required /></label>
          <label>Periodo (giorni) <input type="number" min="1" step="1" bind:value={periodDays} required /></label>
          <label>Primo incontro <input type="date" bind:value={firstMeetingDate} required /></label>
          <label>Preavviso (giorni) <input type="number" min="1" step="1" bind:value={notificationDays} required /></label>
        </fieldset>
      {/if}
      <button type="submit" data-history-hover-exclude disabled={saving}>{saving ? 'Creo...' : 'Crea contratto'}</button>
    </form>
  </div>
</div>

<style>
  .flip-card { --card-height: min(600px, calc(100dvh - 2rem)); height: var(--card-height); perspective: 1100px; }
  .flip-card-inner { position: relative; width: 100%; height: 100%; transform-style: preserve-3d; }
  .flipped .flip-card-inner { transform: rotateY(180deg); }
  .card-face { position: absolute; inset: 0; box-sizing: border-box; display: grid; align-content: start; gap: .55rem; padding: 1rem; border: 1px solid #c4b5fd; border-radius: 12px; background: #f5f3ff; backface-visibility: hidden; -webkit-backface-visibility: hidden; overflow-y: auto; overscroll-behavior-y: contain; scrollbar-gutter: stable; }
  .card-front { align-content: center; border: 1px dashed #8b5cf6; color: #4c1d95; cursor: pointer; justify-items: center; font: inherit; }
  .card-front:hover:not(:disabled) { background: #ede9fe; transform: translateY(-2px); }
  small { color: #475569; }
  .card-back { transform: rotateY(180deg); background: #fff; text-align: left; }
  .card-title { display: flex; align-items: center; gap: .5rem; color: #0f172a; }
  .card-title strong { flex: 1; }
  label { display: grid; gap: .22rem; color: #334155; font-size: .73rem; font-weight: 600; }
  input, select { width: 100%; box-sizing: border-box; padding: .38rem .45rem; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; }
  .periodicity-toggle { display: flex; align-items: center; gap: .45rem; cursor: pointer; }
  .periodicity-toggle input { width: auto; }
  .periodicity-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .55rem; margin: 0; padding: .65rem; border: 1px solid #ddd6fe; border-radius: 8px; }
  .periodicity-fields legend { padding: 0 .25rem; color: #6d28d9; font-size: .75rem; font-weight: 700; }
  button[type='submit'] { width: fit-content; max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: #fff; background: #7c3aed; font: inherit; cursor: pointer; overflow-wrap: anywhere; }
  button:disabled { opacity: .6; cursor: not-allowed; }
  .close { flex: 0 0 auto; border: 0; background: transparent; color: #475569; font-size: 1.35rem; cursor: pointer; }
  @media (max-width: 480px) { .periodicity-fields { grid-template-columns: 1fr; } }
</style>
