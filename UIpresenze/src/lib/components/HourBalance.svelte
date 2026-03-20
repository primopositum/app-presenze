<script lang="ts">
  export let saldo: number;
  export let title: string;
  export let color: [string, string] | undefined;
  export let saldoDaChiamataUtente = false;
  // normalizzo sempre a number (NaN se non valido)
  $: saldoNum = saldo === null || saldo === undefined ? NaN : Number(saldo);
  $: phrases =
    Number.isNaN(saldoNum)
      ? "Saldo non disponibile"
      : saldoNum > 0
        ? "Saldo positivo, ottimo lavoro!"
        : saldoNum < 0
          ? "Saldo negativo, non stiamo lavorando abbastanza!"
          : "Saldo in pari ðŸ‘Œ";

  // testo da mostrare (evita 'NaNh')
  $: saldoLabel = Number.isNaN(saldoNum) ? "--" : String(saldoNum);
</script>

<div
  class="card"
  style={`--hb-c1: ${color?.[0] ?? '#03a9f4'}; --hb-c2: ${color?.[1] ?? '#ff0058'};`}
>
  <b></b>

  <div class="default-label">
    {#if saldoDaChiamataUtente}
      Saldo VALIDATO: {saldoLabel}h
    {:else}
      Saldo: {saldoLabel}h
    {/if}
  </div>

  <div class="content">
    <ul class="sci">
      <li class="saldo">{saldoLabel}h</li>
    </ul>

    <p class="title">
      Saldo ore<br />
      <span class="text">{phrases}</span>
    </p>
  </div>
</div>

<style>
  /* il tuo CSS invariato */
  .card {
    position: fixed;
    bottom: 16px;
    right: 16px;
    width: clamp(140px, 40vw, 190px);
    height: clamp(120px, 35vw, 150px);
    background: #f00;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 14px;
    overflow: hidden;
  }

  .card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(315deg, var(--hb-c1), var(--hb-c2));
    border-radius: inherit;
  }

  .card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(315deg, var(--hb-c1), var(--hb-c2));
    border-radius: inherit;
    filter: blur(30px);
  }

  .card b {
    position: absolute;
    inset: 6px;
    background: rgba(0, 0, 0, 0.6);
    z-index: 2;
    border-radius: inherit;
  }

  .card .content {
    position: absolute;
    z-index: 3;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    transform: scale(0);
    transition: 0.5s;
  }

  .card:hover .content {
    transform: scale(1);
    bottom: 25px;
  }

  .card .default-label {
    position: absolute;
    z-index: 3;
    color: #fff;
    font-weight: 600;
    font-size: 1.1em;
    letter-spacing: 0.05em;
    transition: 0.3s ease;
  }

  .card:hover .default-label {
    opacity: 0;
    transform: translateY(-10px);
  }

  .content .title {
    position: relative;
    color: #fff;
    font-weight: 500;
    line-height: 1em;
    font-size: 1em;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-align: center;
  }

  .content .saldo {
    position: relative;
    color: #fff;
    font-weight: 700;
    line-height: 1em;
    font-size: 2em;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    text-align: center;
  }

  .content .title span {
    font-weight: 300;
    font-size: 0.50em;
  }

  .content .sci {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin-top: 5px;
  }

  .sci li {
    list-style: none;
  }

  @media (max-width: 520px) {
    .card {
      bottom: 12px;
      right: 12px;
      width: min(180px, calc(100vw - 24px));
      height: 130px;
    }

    .card:hover .content {
      bottom: 18px;
    }

    .card .default-label {
      font-size: 0.95em;
    }

    .content .saldo {
      font-size: 1.6em;
    }

    .content .title {
      font-size: 0.9em;
    }
  }
</style>
