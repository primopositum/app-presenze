<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { auth } from '$lib/stores/auth';
  import ProfileCard from '$lib/components/ProfileCard.svelte';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import type { User } from '$lib/services/users';
  import type { UpdateAccountPayload } from '$lib/services/users';
  import { useDeleteAccountApi, useUpdateAccountApi, useUsersApi } from '$lib/hooks/useUserApi';
  let users: User[] = [];
  let error: string | null = null;
  let loading = false;
  let saving = false;
  let hasLoaded = false;

  $: isSuperuser = !!$auth.user?.is_superuser;
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
     <div class="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
  {#each visibleUsers as u}
    <div class="w-full">
      <ProfileCard user={u} currentUser={$auth.user ?? {}} onSave={saveAccount} onDelete={deleteAccount} />
    </div>
  {/each}
</div>


    {/if}

  {:else}
    <ProfileCard user={$auth.user} currentUser={$auth.user} onSave={saveAccount} />
  {/if}
</main>
