<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchTrasfertaDossier, getTrasferte, type Trasferta } from '$lib/services/trasferte';
    import CreateTrasfertaForm from '$lib/components/CreateTrasfertaForm.svelte';
    import { timeEntryReload } from '$lib/stores/timeEntryReload';
    import TrasferteCard from '$lib/components/TrasferteCard.svelte';
    import { goto } from '$app/navigation';
    import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
    import ErrorCard from '$lib/components/ErrorCard.svelte';
    import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
    import { faDownload } from '@fortawesome/free-solid-svg-icons';
    import { auth } from '$lib/stores/auth';
    import { fetchUsers, type User } from '$lib/services/users';

    let items: Trasferta[] = [];
    let loading: boolean = false;
    let showForm = false;
    let mounted = false;
    let generatingDossier = false;
    let dossierError: string | null = null;
    let dossierMonth = new Date().toISOString().slice(0, 7);
    let dossierDate = `${dossierMonth}-01`;
    let dossierUsers: Array<{ id: number; label: string }> = [];
    let selectedDossierUserId = '';
    let usersLoaded = false;
    let usersLoading = false;

    $: isSuperuser = !!$auth.user?.is_superuser;
    $: currentUserId = $auth.user?.id ?? null;
    $: if (!isSuperuser && currentUserId) {
      selectedDossierUserId = String(currentUserId);
    }

    $: if (mounted && isSuperuser && !usersLoaded && !usersLoading) {
      void loadDossierUsers();
    }

    async function loadTrasferte() {
        try {
        loading = true;
        const data = await getTrasferte();
        items = data;
        } catch (e) {
        console.error('Errore caricamento trasferte', e);
        } finally {
        loading = false;
        }
    }
    function openTrasferta(item: Trasferta) {
        goto(`/trasferte/${item.id}`, { state: { trasf: item } });
    }

    function normalizeUsers(payload: unknown): User[] {
      if (Array.isArray(payload)) return payload as User[];
      if (Array.isArray((payload as any)?.results)) return (payload as any).results as User[];
      if (Array.isArray((payload as any)?.users)) return (payload as any).users as User[];
      return [];
    }

    async function loadDossierUsers() {
      usersLoading = true;
      dossierError = null;
      try {
        const payload = await fetchUsers();
        const users = normalizeUsers(payload);
        dossierUsers = users
          .filter((u: User) => !u.is_superuser)
          .map((u: User) => ({
            id: Number(u.id),
            label: `${u.nome ?? ''} ${u.cognome ?? ''}`.trim() || `Utente ${u.id}`
          }))
          .filter((u) => Number.isFinite(u.id))
          .sort((a, b) => a.label.localeCompare(b.label, 'it'));
        selectedDossierUserId = '';
        usersLoaded = true;
      } catch (e: any) {
        dossierError = e?.message || 'Errore caricamento utenti';
      } finally {
        usersLoading = false;
      }
    }

    function getDossierTargetUserId(): number | null {
      if (!isSuperuser) {
        return currentUserId ? Number(currentUserId) : null;
      }
      const parsed = Number(selectedDossierUserId);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    function monthToFirstDay(monthValue: string): string {
      const safe = (monthValue || '').trim();
      if (!/^\d{4}-\d{2}$/.test(safe)) return '';
      return `${safe}-01`;
    }

    async function handleGenerateDossier() {
      if (generatingDossier) return;
      dossierError = null;

      dossierDate = monthToFirstDay(dossierMonth);
      if (!dossierDate) {
        dossierError = 'Seleziona mese e anno validi.';
        return;
      }

      const targetUserId = getDossierTargetUserId();
      if (!targetUserId) {
        dossierError = 'Seleziona un utente valido.';
        return;
      }

      generatingDossier = true;
      try {
        const res = await fetchTrasfertaDossier(targetUserId, dossierDate);
        const firmaStatus = (res.headers.get('X-Firma-Status') || '').toLowerCase();
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dossier_trasferte_${targetUserId}_${dossierDate}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        if (firmaStatus.includes('mancante')) {
          dossierError = 'dossier generato ma firma mancante o caricata non correttamente.';
        }
      } catch (e: any) {
        dossierError = e?.message || 'Errore generazione dossier trasferte';
      } finally {
        generatingDossier = false;
      }
    }

    onMount(() => {
        mounted = true;
    });

    $: if (mounted) {
        $timeEntryReload;
        loadTrasferte();
    }
    </script>

    <div class="page">
          <p  class="font-infinity tracking-[3px] text-center  text-5xl ">Trasferte</p>

    <header class="topbar">
        <div class="actions">
        <button class="ghost" type="button" on:click={() => (showForm = !showForm)}>
            {showForm ? 'Creating..' : 'Nuova'}
        </button>
        <button class="refresh" type="button" on:click={loadTrasferte}>
            Aggiorna
        </button>
        </div>
    </header>

    <main class="content">
        <section class="dossier-bar">
          <div class="dossier-fields">
            <label class="field">
              <span>Data</span>
              <input type="month" bind:value={dossierMonth} />
            </label>
            {#if isSuperuser}
              <label class="field">
                <span>Utente</span>
                <select bind:value={selectedDossierUserId} disabled={usersLoading}>
                  <option value="">Seleziona utente</option>
                  {#each dossierUsers as user (user.id)}
                    <option value={String(user.id)}>
                      {user.label}
                    </option>
                  {/each}
                </select>
              </label>
            {/if}
          </div>
          <button
            class="refresh"
            type="button"
            on:click={handleGenerateDossier}
            disabled={generatingDossier || usersLoading || (isSuperuser && !selectedDossierUserId)}
            aria-label="Scarica dossier ZIP"
            title="Scarica dossier ZIP"
          >
            <FontAwesomeIcon icon={faDownload} class="text-base" />
          </button>
        </section>
        <LoaderOverlay show={loading} />
        {#if showForm}
        <CreateTrasfertaForm onCreated={loadTrasferte} onClose={() => (showForm = false)} />
        {/if}
        {#if loading}
        <p class="state">Caricamento...</p>
        {:else if items.length === 0}
        <p class="state">Nessuna trasferta trovata</p>
        {:else}
        <ul class="list">
            {#each items as item (item.id)}
            <TrasferteCard trasf={item} onClick={openTrasferta} />
            {/each}
        </ul>
        {/if}
    </main>
    </div>

    {#if dossierError}
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        on:click={() => (dossierError = null)}
      >
        <div on:click|stopPropagation>
          <ErrorCard message={dossierError} onClose={() => (dossierError = null)} />
        </div>
      </div>
    {/if}

    <style>
    .page {
        background: #f5f6f8;
    }

    .topbar {
        top: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        color: #000000;
        border-bottom: 1px solid #1f2937;
    }

    .topbar h1 {
        margin: 0;
        font-size: 1.1rem;
        letter-spacing: 0.02em;
    }

    .refresh {
        appearance: none;
        border: 1px solid #374151;
        background: #1f2937;
        color: #fff;
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 0.9rem;
        cursor: pointer;
    }

    .refresh :global(svg) {
        display: block;
    }

    .actions {
        display: flex;
        gap: 8px;
    }

    .ghost {
        appearance: none;
        border: 1px solid #374151;
        background: transparent;
        color: #000000;
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 0.9rem;
        cursor: pointer;
    }

    .content {
        padding: 16px;
        display: grid;
        gap: 12px;
    }

    .dossier-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        justify-content: space-between;
        gap: 10px;
        border: 1px solid #d1d5db;
        border-radius: 12px;
        background: #ffffff;
        padding: 10px;
    }

    .dossier-fields {
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        gap: 10px;
    }

    .field {
        display: grid;
        gap: 4px;
        min-width: 200px;
    }

    .field span {
        font-size: 0.82rem;
        color: #4b5563;
        font-weight: 600;
    }

    .field input,
    .field select {
        width: 100%;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 0.9rem;
        background: #fff;
    }

    .field input:focus,
    .field select:focus {
        outline: 2px solid rgba(31, 41, 55, 0.12);
        outline-offset: 1px;
        border-color: #6b7280;
    }

    .state {
        text-align: center;
        color: #6b7280;
        padding: 24px 8px;
    }

    .state.error {
        color: #b91c1c;
        padding: 8px;
    }

    .list {
        overflow: hidden;
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 12px;
    }
    @media (max-width: 520px) {
        .topbar {
        padding: 12px;
        }
        .content {
        padding: 12px;
        }
    }
</style>
