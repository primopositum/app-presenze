<script lang="ts">
  import { fade, scale } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import type { SaldoRecord } from '$lib/services/saldo';

  export let saldoRecords: SaldoRecord[] = [];
  export let periodo: string;
  export let saldoMese: number | string = 0;

  type CardPosition = 'is-front' | 'is-left' | 'is-right';

  let open = false;
  let cardPositions: CardPosition[] = ['is-front', 'is-right', 'is-left'];

  function toFiniteNumber(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? n : NaN;
  }

  function formatSaldo(value: unknown) {
    const n = toFiniteNumber(value);
    if (Number.isNaN(n)) return '--';
    return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '');
  }

  function rotateFront() {
    cardPositions = cardPositions.map((position) => {
      if (position === 'is-front') return 'is-left';
      if (position === 'is-left') return 'is-right';
      return 'is-front';
    });
  }

  function handleCardClick(index: number) {
    const clickedPosition = cardPositions[index];
    if (clickedPosition === 'is-front') {
      rotateFront();
      return;
    }

    const frontIndex = cardPositions.findIndex((position) => position === 'is-front');
    const nextPositions: CardPosition[] = [...cardPositions];
    const oldFrontPosition = clickedPosition === 'is-left' ? 'is-right' : 'is-left';
    nextPositions[index] = 'is-front';
    if (frontIndex >= 0) nextPositions[frontIndex] = oldFrontPosition;

    const thirdIndex = nextPositions.findIndex((position, currentIndex) =>
      currentIndex !== index && currentIndex !== frontIndex && position !== 'is-front'
    );
    if (thirdIndex >= 0) {
      nextPositions[thirdIndex] = oldFrontPosition === 'is-left' ? 'is-right' : 'is-left';
    }
    cardPositions = nextPositions;
  }

  $: latestRecord = saldoRecords[saldoRecords.length - 1] ?? null;
  $: periodoRecord = saldoRecords.find((record) => record.periodo === periodo) ?? null;
  $: latestLabel = formatSaldo(latestRecord?.saldo);
  $: periodoLabel = formatSaldo(periodoRecord?.saldo);
  $: meseLabel = formatSaldo(saldoMese);

  $: cards = [
    {
      tone: 'bg-blue',
      value: latestLabel,
      title: 'saldo a oggi',
      description: latestRecord?.periodo ? `ultimo record ${latestRecord.periodo}` : 'nessun record'
    },
    {
      tone: 'bg-gold',
      value: periodoLabel,
      title: `card al ${periodo}`,
      description: 'saldo progressivo validato'
    },
    {
      tone: 'bg-purple',
      value: meseLabel,
      title: `stato mese ${periodo}`,
      description: 'versamenti - prelievi'
    }
  ];
</script>

<section class="balance-scene" aria-label="Saldo ore">
  <button type="button" class="balance-trigger" on:click={() => (open = !open)}>
    {open ? 'x' : `${latestLabel}h`}
  </button>

  {#if open}
    <div
      class="wrap-card"
      transition:scale={{ duration: 320, start: 0.7, opacity: 0, easing: cubicOut }}
    >
      {#each cards as card, index}
        <button
          type="button"
          class={`balance-card ${card.tone} ${cardPositions[index]}`}
          aria-label={`${card.title}: ${card.value} ore`}
          on:click={() => handleCardClick(index)}
        >
          <span class="card-value">{card.value}h</span>
          <span class="card-title">{card.title}</span>
          <span class="card-desc">{card.description}</span>
        </button>
      {/each}
    </div>

    <div class="lines" aria-hidden="true" transition:fade={{ duration: 200 }}>
      <div class="line"></div>
      <div class="line"></div>
    </div>
  {/if}
</section>

<style>
  .balance-scene {
    position: fixed;
    right: 18px;
    bottom: 18px;
    z-index: 1500;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    user-select: none;
  }

  .balance-trigger {
    width: 64px;
    height: 64px;
    border: 0;
    border-radius: 50%;
    background: radial-gradient(circle, #8ef9fc 0%, #20a4f6 44%, #0851c0 100%);
    color: #fff;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.22);
  }

  .balance-trigger:focus-visible {
    outline: 3px solid rgba(15, 23, 42, 0.35);
    outline-offset: 3px;
  }

  .wrap-card {
    position: relative;
    width: 330px;
    height: 150px;
  }

  .balance-card {
    position: absolute;
    width: 112px;
    height: 148px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 9px;
    border: 0;
    border-radius: 14px;
    padding: 14px 10px;
    color: #fff;
    text-align: center;
    cursor: pointer;
    overflow: hidden;
    transition:
      transform 0.55s cubic-bezier(0.75, 0, 0, 1.01),
      left 0.55s cubic-bezier(0.75, 0, 0, 1.01),
      top 0.55s cubic-bezier(0.75, 0, 0, 1.01),
      box-shadow 0.2s ease;
  }

  .balance-card:focus-visible {
    outline: 3px solid rgba(15, 23, 42, 0.35);
    outline-offset: 3px;
  }

  .balance-card.is-front {
    z-index: 3;
    top: 0;
    left: 109px;
    transform: rotate(0deg);
    box-shadow: 0 18px 35px rgba(15, 23, 42, 0.22);
  }

  .balance-card.is-left {
    z-index: 1;
    top: 24px;
    left: 20px;
    transform: rotate(-15deg);
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.16);
  }

  .balance-card.is-right {
    z-index: 1;
    top: 24px;
    left: 198px;
    transform: rotate(15deg);
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.16);
  }

  .card-value {
    font-size: 29px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 0;
    font-variant-numeric: tabular-nums;
    word-break: break-word;
  }

  .card-title {
    max-width: 100%;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  .card-desc {
    max-width: 100%;
    font-size: 10px;
    font-weight: 500;
    line-height: 1.25;
    color: rgba(255, 255, 255, 0.78);
  }

  .bg-gold {
    background: radial-gradient(circle, #fff08a 0%, #f5b225 44%, #b98206 100%);
  }

  .bg-blue {
    background: radial-gradient(circle, #8ef9fc 0%, #20a4f6 44%, #0851c0 100%);
  }

  .bg-purple {
    background: radial-gradient(circle, #e08bed 0%, #c923ec 44%, #7d068e 100%);
  }

  .lines {
    position: relative;
    width: 330px;
    height: 14px;
  }

  .line {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .line::before {
    content: "";
    position: absolute;
    width: 100%;
    height: 4px;
    background: linear-gradient(to right, transparent, #2f69f2, transparent);
    filter: blur(3px);
  }

  .line::after {
    content: "";
    position: absolute;
    width: 100%;
    height: 1px;
    background: linear-gradient(to right, transparent, #6366f1, transparent);
  }

  .line:nth-child(2)::before {
    width: 50%;
    background: linear-gradient(to right, transparent, #84ccfc, transparent);
  }

  .line:nth-child(2)::after {
    width: 50%;
    background: linear-gradient(to right, transparent, #14d3f5, transparent);
  }

  @media (max-width: 900px) {
    .balance-scene {
      right: 12px;
      bottom: 12px;
      transform: scale(0.86);
      transform-origin: bottom right;
    }
  }
</style>
