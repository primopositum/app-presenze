<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { auth } from '$lib/stores/auth';
  import ProfileCard from '$lib/components/ProfileCard.svelte';
  import PreSetWeek from '$lib/components/PreSetWeek.svelte';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import type { User } from '$lib/services/users';
  import type { CreateAccountPayload, UpdateAccountPayload } from '$lib/services/users';
  import { useCreateAccountApi, useDeleteAccountApi, useUpdateAccountApi, useUsersApi } from '$lib/hooks/useUserApi';
  let users: User[] = [];
  let error: string | null = null;
  let loading = false;
  let saving = false;
  let hasLoaded = false;
  let showCreateModal = false;
  let creating = false;
  let createEmail = '';
  let createPassword = '';
  let createNome = '';
  let createCognome = '';
  let createIsActive = true;
  let createIsSuperuser = false;
  let createTipologiaContratto = '';

  $: isSuperuser = !!$auth.user?.is_superuser;
  $: isStaff = !!$auth.user?.is_staff;
  $: showOwnPresetWeek = !!$auth.user && !isSuperuser && !isStaff;
  $: showAllUsers = $page.url.searchParams.get('show_all_users') === '1';
  $: visibleUsers = showAllUsers
    ? users
    : users.filter((u: User) => !u.is_superuser && u.is_active !== false);

  async function loadProfiles() {
    if (!isSuperuser) return;
    loading = true;

    const result = await useUsersApi();
    users = result.users;

    error = result.error;
    loading = false;
    hasLoaded = true;
  }

  onMount(() => {
    loadProfiles();
  });

  $: if (isSuperuser && !hasLoaded && !loading) {
    loadProfiles();
  }

  async function saveAccount(payload: UpdateAccountPayload) {
    saving = true;
    const res = await useUpdateAccountApi(payload);
    if (res.error) {
      error = res.error;
      saving = false;
      throw new Error(res.error);
    } else {
      error = null;
      if (res.user?.id) {
        users = users.map((u) => (u.id === res.user!.id ? res.user! : u));
      }
    }
    saving = false;
  }

  async function deleteAccount(userId: number) {
    saving = true;
    const res = await useDeleteAccountApi(userId);
    if (res.error) {
      error = res.error;
      saving = false;
      throw new Error(res.error);
    }
    error = null;
    if (res.deletedUserId) {
      users = users.filter((u) => u.id !== res.deletedUserId);
    }
    saving = false;
  }

  function openCreateModal() {
    if (!isSuperuser) return;
    showCreateModal = true;
  }

  function closeCreateModal() {
    if (creating) return;
    showCreateModal = false;
  }

  function resetCreateForm() {
    createEmail = '';
    createPassword = '';
    createNome = '';
    createCognome = '';
    createIsActive = true;
    createIsSuperuser = false;
    createTipologiaContratto = '';
  }

  async function createAccount() {
    const payload: CreateAccountPayload = {
      email: createEmail.trim(),
      password: createPassword,
      nome: createNome.trim(),
      cognome: createCognome.trim(),
      is_active: createIsActive,
      is_superuser: createIsSuperuser,
      tipologia_contratto: createTipologiaContratto.trim()
    };

    if (!payload.email || !payload.password) {
      error = 'Email e password sono obbligatorie.';
      return;
    }

    creating = true;
    const res = await useCreateAccountApi(payload);
    if (res.error) {
      error = res.error;
      creating = false;
      return;
    }

    if (res.user) {
      users = [...users, res.user];
    }
    users = [...users].sort((a, b) => (a.email ?? '').localeCompare(b.email ?? ''));
    error = null;
    creating = false;
    resetCreateForm();
    showCreateModal = false;
  }
</script>

<main class="w-full p-4">
  <h1 class="text-2xl font-infinity  tracking-[3px] mb-6">Profilo Utente</h1>

  <LoaderOverlay show={loading || saving || !$auth.user} />



  {#if error}
    <p class="text-red-600">{error}</p>

  {:else if !$auth.user} 
    <div></div>

  {:else if isSuperuser}
    {#if loading}
      <div></div>
    {:else}
     <div class="profiles-grid grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
  {#each visibleUsers as u}
    <div class="w-full profile-grid-item">
      <ProfileCard user={u} currentUser={$auth.user ?? {}} onSave={saveAccount} onDelete={deleteAccount} />
    </div>
  {/each}
  <div class="w-full profile-grid-item">
    <button
      type="button"
      class="add-user-card"
      aria-label="Aggiungi nuovo utente"
      title="Aggiungi nuovo utente"
      on:click={openCreateModal}
    >
      <span class="add-user-plus">+</span>
    </button>
  </div>
</div>


    {/if}

  {:else}
    <div class="space-y-6">
      <ProfileCard user={$auth.user} currentUser={$auth.user} onSave={saveAccount} />
      {#if showOwnPresetWeek}
        <PreSetWeek />
      {/if}
    </div>
  {/if}
</main>

{#if showCreateModal}
  <div class="create-backdrop" on:click={closeCreateModal} />
  <div class="create-modal" role="dialog" aria-modal="true" on:click|stopPropagation>
    <h2 class="create-title">Nuovo utente</h2>
    <div class="create-grid">
      <input class="create-input" type="email" placeholder="Email *" bind:value={createEmail} />
      <input class="create-input" type="password" placeholder="Password *" bind:value={createPassword} />
      <input class="create-input" type="text" placeholder="Nome" bind:value={createNome} />
      <input class="create-input" type="text" placeholder="Cognome" bind:value={createCognome} />
      <input class="create-input" type="text" placeholder="Tipologia contratto (es. Impiegato)" bind:value={createTipologiaContratto} />
      <div class="toggle-row">
        <span>Account attivo</span>
        <button
          type="button"
          class="toggle-switch {createIsActive ? 'is-on' : ''}"
          role="switch"
          aria-checked={createIsActive}
          aria-label="Account attivo"
          on:click={() => (createIsActive = !createIsActive)}
        >
          <span class="toggle-knob"></span>
        </button>
      </div>
      <div class="toggle-row">
        <span>Superuser</span>
        <button
          type="button"
          class="toggle-switch {createIsSuperuser ? 'is-on' : ''}"
          role="switch"
          aria-checked={createIsSuperuser}
          aria-label="Superuser"
          on:click={() => (createIsSuperuser = !createIsSuperuser)}
        >
          <span class="toggle-knob"></span>
        </button>
      </div>
    </div>
    <div class="create-actions">
      <button type="button" class="btn-cancel" on:click={closeCreateModal} disabled={creating}>Annulla</button>
      <button type="button" class="btn-create" on:click={createAccount} disabled={creating}>
        {creating ? 'Creazione...' : 'Crea utente'}
      </button>
    </div>
  </div>
{/if}

<style>
  .profile-grid-item {
    display: flex;
    align-items: stretch;
  }
  .add-user-card {
    width: 100%;
    height: 100%;
    min-height: 0;
    border: 1px dashed rgba(148, 163, 184, 0.6);
    border-radius: 1rem;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.85), rgba(241, 245, 249, 0.55));
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 20px 50px -8px rgba(15, 23, 42, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06);
    transition: border-color 0.25s ease, transform 0.25s ease, background-color 0.25s ease, box-shadow 0.25s ease;
  }
  .add-user-card:hover {
    border-color: rgba(249, 115, 22, 0.8);
    transform: translateY(-2px);
    background: linear-gradient(135deg, rgba(255, 247, 237, 0.7), rgba(255, 237, 213, 0.42));
    box-shadow: 0 8px 12px -2px rgba(15, 23, 42, 0.12), 0 24px 52px -8px rgba(15, 23, 42, 0.18), 0 2px 4px rgba(0, 0, 0, 0.08);
  }
  .add-user-plus {
    font-size: 5.5rem;
    line-height: 1;
    font-weight: 700;
    color: rgba(249, 115, 22, 0.75);
    user-select: none;
  }
  .create-backdrop {
    position: fixed;
    inset: 0;
    z-index: 3200;
    background: rgba(0, 0, 0, 0.45);
  }
  .create-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 3201;
    width: min(460px, 92vw);
    border-radius: 14px;
    background: #fff;
    border: 1px solid #e5e7eb;
    padding: 16px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
  }
  .create-title {
    margin: 0 0 12px 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: #111827;
  }
  .create-grid {
    display: grid;
    gap: 10px;
  }
  .create-input {
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 0.92rem;
    outline: none;
  }
  .create-input:focus {
    border-color: #f97316;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.18);
  }
  .toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.86rem;
    color: #374151;
    padding: 2px 2px 2px 0;
  }
  .toggle-switch {
    width: 46px;
    height: 26px;
    border: none;
    border-radius: 999px;
    background: #d1d5db;
    padding: 3px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    transition: background-color 0.24s ease, box-shadow 0.24s ease;
  }
  .toggle-switch.is-on {
    background: #f97316;
    box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.2);
  }
  .toggle-knob {
    width: 20px;
    height: 20px;
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
    transform: translateX(0);
    transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1);
  }
  .toggle-switch.is-on .toggle-knob {
    transform: translateX(20px);
  }
  .create-actions {
    margin-top: 14px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .btn-cancel {
    border: 1px solid #d1d5db;
    background: #fff;
    color: #374151;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn-create {
    border: 1px solid #f97316;
    background: #f97316;
    color: #fff;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 700;
    cursor: pointer;
  }
  .btn-cancel:disabled,
  .btn-create:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  @media (max-width: 640px) {
    .add-user-card {
      min-height: 0;
    }
  }
  .profiles-grid {
    align-items: stretch;
  }
</style>
