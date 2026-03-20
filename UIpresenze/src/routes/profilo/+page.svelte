<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';
  import ProfileCard from '$lib/components/ProfileCard.svelte';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import type { User } from '$lib/services/users';
  import { useUsersApi } from '$lib/hooks/useUserApi';
  let users: User[] = [];
  let error: string | null = null;
  let loading = false;
  let hasLoaded = false;

  $: isSuperuser = !!$auth.user?.is_superuser;

  async function loadProfiles() {
    if (!isSuperuser) return;
    loading = true;

    const result = await useUsersApi();
    const payload = result.users as unknown;
    const list: User[] = Array.isArray(payload) ? payload : ((payload as any)?.results ?? []);

    users = list.filter((u: User) => !u.is_superuser);

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
  
</script>

<main class="w-full p-4">
  <h1 class="text-2xl font-infinity  tracking-[3px] mb-6">Profilo Utente</h1>
 
  <LoaderOverlay show={loading || !$auth.user} />



  {#if error}
    <p class="text-red-600">{error}</p>

  {:else if !$auth.user} 
    <div></div>

  {:else if isSuperuser}
    {#if loading}
      <div></div>
    {:else}
     <div class="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
  {#each users as u}
    <div class="w-full">
      <ProfileCard user={u} />
    </div>
  {/each}
</div>


    {/if}

  {:else}
    <ProfileCard user={$auth.user} />
  {/if}
</main>
