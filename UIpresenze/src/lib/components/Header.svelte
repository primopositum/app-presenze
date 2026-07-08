<script lang="ts">
  import ButtonGradient from './ButtonGradient.svelte';
  import { auth } from '$lib/stores/auth';
  import { apiLogout, stopAutoRefresh } from '$lib/api';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faHouse, faKey, faHammer, faUsers, faQuestion } from '@fortawesome/free-solid-svg-icons';
  import ChangePasswordCard from '$lib/components/ChangePasswordCard.svelte';
  import GuideModal from '$lib/components/GuideModal.svelte';

  const GUIDE_ROUTES = new Map([
    ['Automobili', 'Automobili'],
    ['JiraBoard', 'JiraBoard'],
    ['Presenze', 'Presenze'],
    ['trasferte', 'Trasferte']
  ]);

  $: isProfileRoute = $page.url.pathname === '/profilo';
  $: showAllProfiles = $page.url.searchParams.get('show_all_users') === '1';
  $: canToggleAllProfiles = isProfileRoute && !!$auth.user?.is_superuser;
  $: currentRouteName = $page.url.pathname.split('/').filter(Boolean)[0] || '';
  $: guideName = GUIDE_ROUTES.get(currentRouteName) ?? '';
  $: guidePdfUrl = guideName
    ? `/docs/tutorialGrafici/${encodeURIComponent(guideName)}.pdf`
    : '';

  let open = false;
  let successMessage: string | null = null;
  let successTimer: ReturnType<typeof setTimeout> | null = null;
  let guideRotation = 0;
  let guideOpen = false;
  let lastGuidePdfUrl = '';

  $: if (guidePdfUrl !== lastGuidePdfUrl) {
    guideOpen = false;
    lastGuidePdfUrl = guidePdfUrl;
  }
  
  async function handleLogout() {
    stopAutoRefresh();
    try {
      await apiLogout();
    } catch {
      // prosegui comunque con logout locale
    }
    auth.logout();
  }

  function goToProfile() {
    goto('/profilo');
  }
  function handleGuideClick() {
    guideRotation += 360;
    guideOpen = true;
  }
  function toggleAllProfiles() {
    const params = new URLSearchParams($page.url.searchParams);
    if (showAllProfiles) {
      params.delete('show_all_users');
    } else {
      params.set('show_all_users', '1');
    }
    const query = params.toString();
    const target = query ? `${$page.url.pathname}?${query}` : $page.url.pathname;
    goto(target, { replaceState: true, noScroll: true, keepFocus: true });
  }
    // $: showProfileButton = page.url.pathname !== '/profilo';
  function handlePasswordChanged(message: string) {
    open = false;
    successMessage = message;
    if (successTimer) clearTimeout(successTimer);
    successTimer = setTimeout(() => (successMessage = null), 3000);
  }
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
          <div class="profile-controls">
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
            {#if canToggleAllProfiles}
              <button
                type="button"
                class="toggle-profiles-btn inline-flex h-10 items-center justify-center rounded-full border px-3 text-sm font-semibold transition {showAllProfiles
                  ? 'border-orange-400 bg-orange-50 text-orange-700 hover:bg-orange-100'
                  : 'border-gray-300 bg-white text-gray-800 hover:border-gray-400 hover:text-black'}"
                title={showAllProfiles ? 'Mostra solo utenti normali' : 'Mostra tutti gli utenti'}
                aria-label={showAllProfiles ? 'Mostra solo utenti normali' : 'Mostra tutti gli utenti'}
                on:click={toggleAllProfiles}
              >
                <FontAwesomeIcon icon={showAllProfiles ? faHammer : faUsers} class="text-base" />
              </button>
            {/if}
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
      {#if guidePdfUrl}
        <button
          type="button"
          class="guide-button"
          style={`--guide-rotation: ${guideRotation}deg;`}
          title="Guida"
          aria-label={`Apri la guida di ${currentRouteName}`}
          on:click={handleGuideClick}
        >
          <FontAwesomeIcon icon={faQuestion} class="text-[150%]" />
        </button>
      {/if}
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
</nav>

{#if successMessage}
  <div class="success-toast" role="status" aria-live="polite">
    {successMessage}
  </div>
{/if}

{#if guidePdfUrl}
  {#key guidePdfUrl}
    <GuideModal
      isOpen={guideOpen}
      onClose={() => (guideOpen = false)}
      pdfUrl={guidePdfUrl}
      title={`Guida ${currentRouteName}`}
    />
  {/key}
{/if}



<style>
  .guide-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #374151;
    border-radius: 9999px;
    background: #374151;
    color: #fff;
    width: 3.15rem;
    height: 3.15rem;
    flex: 0 0 3.15rem;
    padding: 0;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transform: rotateX(var(--guide-rotation, 0deg));
    transform-style: preserve-3d;
    transition: transform 0.55s ease-in-out, background-color 0.2s ease, border-color 0.2s ease;
  }

  .guide-button:hover {
    border-color: #4b5563;
    background: #4b5563;
  }

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
    .profile-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .toggle-profiles-btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>
