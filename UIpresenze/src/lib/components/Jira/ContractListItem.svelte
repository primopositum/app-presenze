<script lang="ts">
  import type { ContrattoCliente } from '$lib/services/clienti';

  export let contract: ContrattoCliente;
  export let clientName: string;
  export let signedValue: number;
  export let currentValue: number;
  export let selected = false;
  export let onSelect: () => void;

  function handleKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    onSelect();
  }
</script>

<section
  class="contract-row"
  class:contract-selected={selected}
  role="button"
  tabindex="0"
  on:click={onSelect}
  on:keydown={handleKeydown}
>
  <strong>{contract.contract_id}</strong>
  <span>{clientName}</span>
  <span>Valore: € {signedValue.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
  {#if contract.periodicity}
    <span>Valore maturato: € {currentValue.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
  {/if}
  <small>{contract.start_date} → {contract.end_date}</small>
</section>

<style>
  .contract-row {
    display: grid;
    gap: 0.12rem;
    padding: 0.6rem 0.7rem;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    background: #fff;
    cursor: pointer;
    transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
  }

  .contract-row:hover,
  .contract-selected {
    border-color: #93c5fd;
    background: #eff6ff;
  }

  .contract-selected {
    box-shadow: inset 3px 0 0 #2563eb;
  }

  small {
    color: #64748b;
    font-size: 0.75rem;
  }
</style>
