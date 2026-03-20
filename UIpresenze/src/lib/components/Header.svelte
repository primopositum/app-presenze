<script lang="ts">
  import ButtonGradient from './ButtonGradient.svelte';
  import { auth } from '$lib/stores/auth';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faHouse, faKey } from '@fortawesome/free-solid-svg-icons';
  import HourBalance from './HourBalance.svelte';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  import { hourBalanceExtra } from '$lib/stores/hourBalanceExtra';
  import ChangePasswordCard from '$lib/components/ChangePasswordCard.svelte';

  $: saldoValidato = $auth.user?.saldo?.valore_saldo_validato ?? null;
  $: saldoTimeEntryUser = $timeEntryUser.user?.saldo?.valore_saldo_validato ?? null;
  $: isPresencesRoute = $page.url.pathname.startsWith('/presences');
  $: isProfileRoute = $page.url.pathname === '/profilo';

  $: extra = $hourBalanceExtra ?? null;
  $: canShowExtra = !!extra && extra.saldo !== undefined && extra.saldo !== null;
  let mode: 'persistente' | 'extra' = 'extra';
  let open = false;
  let successMessage: string | null = null;
  let successTimer: ReturnType<typeof setTimeout> | null = null;
  const toNumber = (v: unknown) => {
    const n = typeof v === 'string' ? Number(v) : (v as number);
    return Number.isFinite(n) ? n : 0;
  };
  $: showSaldo =
    $auth.isAuthed &&
    ((!$auth.user?.is_superuser && saldoValidato !== null) ||
      ($auth.user?.is_superuser && isPresencesRoute && saldoTimeEntryUser !== null));

  $: saldoToShow =
    $auth.user?.is_superuser && isPresencesRoute ? saldoTimeEntryUser : saldoValidato;
  
  function handleLogout() {
    auth.logout();
    goto('/login');
  }

  function goToProfile() {
    goto('/profilo');
  }
    // $: showProfileButton = page.url.pathname !== '/profilo';
  function toggle() {
    if (!canShowExtra) return;
    mode = mode === 'persistente' ? 'extra' : 'persistente';
  }

  function handlePasswordChanged(message: string) {
    open = false;
    successMessage = message;
    if (successTimer) clearTimeout(successTimer);
    successTimer = setTimeout(() => (successMessage = null), 3000);
  }

  $: hbTitle =
    mode === 'extra' && extra?.title ? extra.title : 'saldo persistente';
  $: hbSaldo =
    mode === 'extra' && extra?.saldo !== undefined && extra?.saldo !== null
      ? toNumber(extra.saldo) + toNumber(saldoToShow)
      : saldoToShow;
  $: hbColor = mode === 'extra' && extra?.color ? extra.color : undefined;
</script>

<nav class="flex items-center justify-between px-8 py-4 bg-white-200">
  {#if $auth.isAuthed}
    <!-- Sinistra: Profilo -->
    <div class="flex-1 flex justify-start">
       {#if !isProfileRoute}
      <ButtonGradient
        onClick={goToProfile}
        title="Profilo"
        buttonText="Profilo"
      />
      {/if}
      <div class="px-4">
        {#if isProfileRoute}
          <div class="flex items-center gap-3">
            <span class="hidden text-xl font-infinity tracking-[3px] text-gray-900 sm:inline">Profilo Utente</span>
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-gray-300 bg-white text-gray-800 transition hover:border-gray-400 hover:text-black"
              title="Cambia password"
              aria-label="Cambia password"
              on:click={() => (open = true)}
            >
              <FontAwesomeIcon icon={faKey} class="text-base" />
            </button>
          </div>
         {/if}
      </div>
    </div>

    <!-- Centro: Home -->
    <div class="absolute left-1/2 -translate-x-1/2">
      <a href="/" class="text-lg font-semibold text-gray-800 hover:text-blue-600 transition">
        <FontAwesomeIcon icon={faHouse} class="text-gray-700 text-[280%]" />
      </a>
    </div>
 
    <div class="flex-1 flex justify-end items-center gap-2">
      <ButtonGradient
        onClick={handleLogout}
        title="Logout"
        buttonText="Logout"
      />

    
  

      {#if open}
        <div class="modal-backdrop" on:click={() => (open = false)} />
        <div class="modal-panel" role="dialog" aria-modal="true" on:click|stopPropagation>
          <div class="modal-header">
            <h2 class="modal-title">Cambia password</h2>
            <button class="modal-close" type="button" on:click={() => (open = false)} aria-label="Chiudi">
              ×
            </button>
          </div>

    <ChangePasswordCard onSuccess={handlePasswordChanged} />
        </div>
      {/if}
      </div>
  {/if}




  {#if showSaldo}
    <div class={`hide-mobile-saldo ${canShowExtra ? 'cursor-pointer' : 'cursor-default'}`} on:click={toggle}>
      <HourBalance title={hbTitle} saldo={hbSaldo} color={hbColor}/>
    </div>
  {/if}
</nav>

{#if successMessage}
  <div class="success-toast" role="status" aria-live="polite">
    {successMessage}
  </div>
{/if}



<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    z-index: 2000;
    animation: fade-in 140ms ease-out;
  }

  .modal-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 2001;
    max-width: 90%;
    max-height: 90%;
    overflow: auto;
    animation: pop-in 160ms ease-out;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .modal-title {
    font-size: 16px;
    font-weight: 600;
  }

  .modal-close {
    border: 0;
    background: transparent;
    width: 32px;
    height: 32px;
    line-height: 32px;
    border-radius: 6px;
    font-size: 22px;
  }

  .modal-close:hover {
    background: rgba(0, 0, 0, 0.08);
    cursor: pointer;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes pop-in {
    from { opacity: 0; transform: translate(-50%, -48%) scale(0.98); }
    to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  }

  .success-toast {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 2100;
    background: #16a34a;
    color: white;
    padding: 10px 14px;
    border-radius: 10px;
    font-weight: 600;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
    animation: toast-in 160ms ease-out;
  }

  @keyframes toast-in {
    from { opacity: 0; transform: translateY(-6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 640px) {
    .hide-mobile-saldo {
      display: none;
    }
  }
</style>
