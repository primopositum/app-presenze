<script lang="ts">
  import { useClienteCreate } from '$lib/hooks/useClienti';

  export let onCreated: (() => Promise<void> | void) | undefined = undefined;
  export let active = false;
  export let onSelect: (() => void) | undefined = undefined;
  export let onClose: (() => void) | undefined = undefined;
  export let onNotify: ((message: string, success: boolean) => void) | undefined = undefined;

  let nome = '';
  let indirizzo = '';
  let telefono = '';
  let saving = false;

  async function createCliente() {
    saving = true;
    try {
      if (!nome.trim()) throw new Error('Il nome del cliente è obbligatorio.');
      await useClienteCreate({ nome: nome.trim(), indirizzo: indirizzo.trim(), telefono: telefono.trim() });
      nome = '';
      indirizzo = '';
      telefono = '';
      onClose?.();
      onNotify?.('Cliente creato.', true);
      await onCreated?.();
    } catch (cause: any) {
      onNotify?.(String(cause?.message || cause || 'Impossibile creare il cliente.'), false);
    } finally {
      saving = false;
    }
  }
</script>

<div class="flip-card" class:flipped={active}>
  <div class="flip-card-inner">
    <button class="card-face card-front" type="button" data-history-hover-exclude on:click={() => onSelect?.()}>
      <strong>Crea cliente</strong>
      <small>Aggiungi una nuova anagrafica</small>
    </button>

    <form class="card-face card-back" on:submit|preventDefault={createCliente}>
      <div class="card-title"><strong>Crea cliente</strong><button type="button" class="close" data-history-hover-exclude on:click={() => onClose?.()} aria-label="Torna alla scelta di creazione">×</button></div>
      <label>Nome <input bind:value={nome} required /></label>
      <label>Indirizzo <input bind:value={indirizzo} /></label>
      <label>Telefono <input bind:value={telefono} /></label>
      <button type="submit" data-history-hover-exclude disabled={saving}>{saving ? 'Creo...' : 'Crea cliente'}</button>
    </form>
  </div>
</div>

<style>
  .flip-card { min-height: 245px; perspective: 1100px; } .flip-card-inner { position: relative; width: 100%; min-height: 245px; transition: transform .55s ease; transform-style: preserve-3d; } .flipped .flip-card-inner { transform: rotateY(180deg); }
  .card-face { position: absolute; inset: 0; box-sizing: border-box; display: grid; align-content: center; gap: .6rem; padding: 1rem; border: 1px solid #bfdbfe; border-radius: 12px; background: #eff6ff; backface-visibility: hidden; -webkit-backface-visibility: hidden; } .card-front { border: 1px dashed #60a5fa; color: #1e3a8a; cursor: pointer; justify-items: center; font: inherit; } .card-front:hover { background: #dbeafe; transform: translateY(-2px); } small { color: #475569; } .card-back { transform: rotateY(180deg); background: #fff; text-align: left; } .card-title { display: flex; justify-content: space-between; align-items: center; gap: .5rem; color: #0f172a; } label { display: grid; gap: .25rem; color: #334155; font-size: .75rem; font-weight: 600; } input { width: 100%; box-sizing: border-box; padding: .42rem .5rem; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; } button[type='submit'] { width: fit-content; max-width: 100%; border: 0; border-radius: 7px; padding: .42rem .65rem; color: #fff; background: #2563eb; font: inherit; cursor: pointer; overflow-wrap: anywhere; } button:disabled { opacity: .6; cursor: not-allowed; } .close { flex: 0 0 auto; border: 0; background: transparent; color: #475569; font-size: 1.35rem; cursor: pointer; }
</style>
