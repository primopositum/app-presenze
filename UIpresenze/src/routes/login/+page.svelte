<script lang="ts">
  import { goto } from '$app/navigation';
  import { getToken } from '$lib/api';
  import { auth } from '$lib/stores/auth';
  import ButtonGradient from '$lib/components/ButtonGradient.svelte';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import { onMount } from 'svelte';
  import palette from '../../theme/palette.js';

  let email = '';
  let password = '';
  let loading = false;
  let error: string | null = null;

  // ✅ toggle password
  let showPassword = false;
  const togglePassword = () => (showPassword = !showPassword);

  async function submit(e: Event) {
    e.preventDefault();
    error = null;
    loading = true;
    try {
      const data = await getToken(email, password);
      auth.login(data.token, data.user);
      console.log(data.user)
      await goto('/');
    } catch (err: any) {
      error = err?.message || 'Errore imprevisto';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    auth.init();
    if ($auth.isAuthed) goto('/');
  });
</script>

<main class="flex min-h-screen flex-col items-center justify-center px-4">
  <LoaderOverlay show={loading} />
  <img src="/logo2.png" alt="logo1" class="mb-4 w-full max-w-[240px] sm:max-w-[320px]">

  <div class="py-6 w-full max-w-md">
    <div class="border border-slate-300 rounded-lg p-6 shadow-[0_2px_22px_-4px_rgba(93,96,127,0.2)]">
      <form on:submit|preventDefault={submit} class="space-y-6">
        <div class="mb-12">
          <h1 class="text-slate-900 text-3xl font-semibold">Accedi</h1>
          <p class="text-slate-600 text-[15px] mt-6 leading-relaxed">Inserisci nome utente e password</p>
        </div>

        <div>
          <label class="text-slate-900 text-sm font-medium mb-2 block">Account</label>
          <div class="relative flex items-center">
            <input
              bind:value={email}
              type="email"
              required
              class="w-full text-sm text-slate-900 border border-slate-300 pl-4 pr-4 py-3 rounded-lg outline-blue-600"
              placeholder="Inserisci il nome utente"
            />
          </div>
        </div>

        <div>
          <label class="text-slate-900 text-sm font-medium mb-2 block">Password</label>

          <div class="relative flex items-center">
            <input
              bind:value={password}
              type={showPassword ? 'text' : 'password'}
              required
              class="w-full text-sm text-slate-900 border border-slate-300 pl-4 pr-12 py-3 rounded-lg outline-blue-600"
              placeholder="Inserisci la password"
            />

            <button
              type="button"
              on:click={togglePassword}
              class="absolute right-2 inline-flex items-center justify-center w-9 h-9 rounded-md hover:bg-slate-100"
              aria-label={showPassword ? 'Nascondi password' : 'Mostra password'}
              title={showPassword ? 'Nascondi password' : 'Mostra password'}
            >
              {#if showPassword}
                <svg xmlns="http://www.w3.org/2000/svg" fill={palette.icon.muted} stroke={palette.icon.muted} class="w-[18px] h-[18px]" viewBox="0 0 24 24">
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" fill="none" stroke-width="2" />
                  <path d="M4 4 20 20" fill="none" stroke-width="2" />
                  <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" fill="none" stroke-width="2" />
                </svg>
              {:else}
                <svg xmlns="http://www.w3.org/2000/svg" fill={palette.icon.muted} stroke={palette.icon.muted} class="w-[18px] h-[18px]" viewBox="0 0 24 24">
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12Z" fill="none" stroke-width="2" />
                  <circle cx="12" cy="12" r="3" fill="none" stroke-width="2" />
                </svg>
              {/if}
            </button>
          </div>
        </div>

        {#if error}
          <p class="text-red-600 text-sm">{error}</p>
        {/if}

        <div class="!mt-12">
          <ButtonGradient
            title="Accedi al sistema"
            buttonText={loading ? 'Accesso…' : 'Accedi'}
            onClick={submit}
          />
        </div>
      </form>
    </div>
  </div>
</main>

<style>
  form input { width: 100%; padding: 0.5rem; }
  form button { padding: 0.5rem; }
  label { display:flex; gap: 0.5rem; flex-direction: column; }
</style>
