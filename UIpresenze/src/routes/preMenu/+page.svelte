<script lang="ts">
  interface CustomState {
    route: string;
  }

  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { useUsersApi } from '$lib/hooks/useUserApi';
  import { auth } from '$lib/stores/auth';
  import { get } from 'svelte/store';
  import type { User } from '$lib/services/users';
  import ProfileCard from '$lib/components/ProfileCard.svelte';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  let users: User[] = [];
  let error: string | null = null;
  let loading = false;

  $: route = (($page.state as CustomState | null)?.route) ?? '/';

  function isUser(x: unknown): x is User {
    return (
      !!x &&
      typeof x === 'object' &&
      typeof (x as any).id === 'number' &&
      typeof (x as any).nome === 'string'
    );
  }

  function normalizeUsers(payload: unknown): User[] {
    const arr = Array.isArray(payload)
      ? payload
      : payload && typeof payload === 'object' && 'results' in payload
        ? (payload as any).results
        : [];

    if (!Array.isArray(arr)) return [];
    return arr.filter(isUser);
  }

  async function loadUsers() {
    loading = true;
    try {
      const result = await useUsersApi();
      users = normalizeUsers(result.users as unknown);
      error = result.error;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    const state = get(auth);
    if (state.isAuthed || state.user) {
      void loadUsers();
      return;
    }
    const unsub = auth.subscribe((value) => {
      if (value.isAuthed || value.user) {
        unsub();
        void loadUsers();
      }
    });
  });

  function handlePickUser(u: User) {
    timeEntryUser.setUser(u);
    if ($page.url.pathname === '/preMenu') {
      goto('/presences');
      return;
    }
    goto(route);
  }

  //  const PALETTE = [
  //   '#e160e3',
  //   '#4dd4ac',
  //   '#ffb703',
  //   '#90dbf4',
  //   '#f07167'
  // ];

  // const baseColor = PALETTE[Math.floor(Math.random() * PALETTE.length)];
  // const hoverColor = `${baseColor}cc`; // più trasparente
  // colors={{ baseColor, hoverColor }} 
</script>

<LoaderOverlay show={loading} />

{#if error}
  <p>Errore: {error}</p>
{:else}
  <div class="usersGrid">
    {#if users.length > 0}
      {#each users as u (u.id)}
        {#if !u.is_superuser}
          <button class="userButton" type="button" on:click={() => handlePickUser(u)}>
            <ProfileCard user={u} />
          </button>
        {/if}
      {/each}
    {/if}
  </div>
{/if}

<style>
  .usersGrid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    align-items: start;
    padding: 12px;
    justify-items: center;
  }

  .userButton {
    all: unset;
    display: block;
    cursor: pointer;
  }
</style>

