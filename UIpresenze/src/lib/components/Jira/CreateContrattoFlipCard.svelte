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
  let value = '';
  let dataCreazione = '';
  let dataFine = '';
  let saving = false;

  async function createContratto() {
    saving = true;
    try {
      const parsedClienteId = Number(clienteId);
      if (!Number.isInteger(parsedClienteId) || parsedClienteId <= 0) throw new Error('Seleziona un cliente.');
      const normalizedValue = String(value ?? '').trim();
      if (!normalizedValue || !dataCreazione || !dataFine) throw new Error('Valore e date sono obbligatori.');
      await useContrattoClienteCreate({
        cliente_id: parsedClienteId,
        value: normalizedValue,
        pool_task: [],
        data_creazione: dataCreazione,
        data_fine: dataFine
      });
      clienteId = '';
      value = '';
      dataCreazione = '';
      dataFine = '';
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
      <label>Valore <input type="number" min="0" step="0.01" bind:value required /></label>
      <label>Data creazione <input type="date" bind:value={dataCreazione} required /></label>
      <label>Data fine <input type="date" bind:value={dataFine} required /></label>
      <button type="submit" data-history-hover-exclude disabled={saving}>{saving ? 'Creo...' : 'Crea contratto'}</button>
    </form>
  </div>
</div>

<style>
  .flip-card { min-height: 245px; perspective: 1100px; } .flip-card-inner { position: relative; width: 100%; min-height: 245px; transition: transform .55s ease; transform-style: preserve-3d; } .flipped .flip-card-inner { transform: rotateY(180deg); }
  .card-face { position: absolute; inset: 0; box-sizing: border-box; display: grid; align-content: center; gap: .55rem; padding: 1rem; border: 1px solid #c4b5fd; border-radius: 12px; background: #f5f3ff; backface-visibility: hidden; -webkit-backface-visibility: hidden; } .card-front { border: 1px dashed #8b5cf6; color: #4c1d95; cursor: pointer; justify-items: center; font: inherit; } .card-front:hover:not(:disabled) { background: #ede9fe; transform: translateY(-2px); } small { color: #475569; } .card-back { transform: rotateY(180deg); background: #fff; text-align: left; } .card-title { display: flex; justify-content: space-between; align-items: center; gap: .5rem; color: #0f172a; } label { display: grid; gap: .22rem; color: #334155; font-size: .73rem; font-weight: 600; } input, select { width: 100%; box-sizing: border-box; padding: .38rem .45rem; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; } button[type='submit'] { width: fit-content; max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: #fff; background: #7c3aed; font: inherit; cursor: pointer; overflow-wrap: anywhere; } button:disabled { opacity: .6; cursor: not-allowed; } .close { flex: 0 0 auto; border: 0; background: transparent; color: #475569; font-size: 1.35rem; cursor: pointer; }
</style>
