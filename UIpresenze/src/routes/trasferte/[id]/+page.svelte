<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faArrowLeft, faRotate, faCheck, faBroom, faFlag, faCalculator, faCar, faLocationDot } from '@fortawesome/free-solid-svg-icons';
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';
  import palette from '../../../theme/palette.js';
  import {
    getSpeseByTrasferta,
    getTrasferte,
    updateTrasferta,
    type Spesa,
    type SpesaCreate,
    type Trasferta
  } from '$lib/services/trasferte';
  import { getAutomobili, updateAutomobileCoeff, type Automobile } from '$lib/services/automobili';
  import { useCreateSpese, useScontrini, useValidateTrasferta } from '$lib/hooks/useTrasferte';
  import type { User } from '$lib/services/users';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import SpeseCard from '$lib/components/SpeseCard.svelte';
  import FormSpesa from '$lib/components/FormSpesa.svelte';
  import ErrorCard from '$lib/components/ErrorCard.svelte';
  import MapsPlugin from '$lib/components/MapsPlugin.svelte';
  import LoadReceipts from '$lib/components/LoadReceipts.svelte';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  let item: Trasferta | null = null;
  let spese: Spesa[] = [];
  let token: string | null = null;
  let loading = false;
  let showSpesaForm = false;
  let creatingSpesa = false;
  let createSpesaError: string | null = null;
  let error: string | null = null;
  let mapRef: { calcolaDistanza: (a1?: string, a2?: string) => Promise<number | null> } | null = null;
  let distanzaKm: number | null = null;
  const DEFAULT_PARTENZA = 'Via Broseta 58, Bergamo';
  let partenza = DEFAULT_PARTENZA;
  let arrivo = '';
  let costoKmInput = '';
  let kmError: string | null = null;
  let coefficienteSaving = false;
  let autoError: string | null = null;
  let autoLoading = false;
  let autoSaving = false;
  let autoUpdateSeq = 0;
  let automobili: Automobile[] = [];
  let autoOptions: Array<{ id: number; label: string }> = [];
  let selectedAutoId = '';
  let isLocked = false;
  let isSuperuser = false;
  let refreshKey = 0;
  let isKmBandieraRossa = false;

  $: token = $auth.token;
  $: isSuperuser = !!$auth.user?.is_superuser;

  function getAutoId(auto: Automobile): number | null {
    return auto.id ?? auto.a_id ?? auto.A_ID ?? null;
  }

  function getAutoLabel(auto: Automobile): string {
    const parts = [auto.marca, auto.alimentazione].filter(Boolean);
    return parts.join(' • ');
  }

  function getTrasfertaAutoRawValue(trasferta: Trasferta | null): number | string | null {
    if (!trasferta) return null;
    return trasferta.A_ID ?? trasferta.automobile ?? null;
  }

  function resolveSelectedAutoId(value: number | string | null, list: Automobile[]): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);

    const raw = String(value).trim();
    if (!raw) return '';

    if (/^\d+$/.test(raw)) {
      const exists = list.some((auto) => String(getAutoId(auto)) === raw);
      return exists ? raw : '';
    }

    const byBrand = list.find((auto) => auto.marca?.trim().toLowerCase() === raw.toLowerCase());
    const id = byBrand ? getAutoId(byBrand) : null;
    return id !== null ? String(id) : '';
  }

  function syncKmRateFromSelectedAuto() {
    if (!selectedAutoId) {
      costoKmInput = '';
      return;
    }

    const selected = automobili.find((auto) => String(getAutoId(auto)) === selectedAutoId);
    costoKmInput = selected ? String(selected.coefficiente ?? '') : '';
  }

  async function handleCoefficienteChange(event: Event) {
    if (!item || isLocked) return;

    const value = (event.currentTarget as HTMLInputElement).value.trim();
    costoKmInput = value;

    if (!selectedAutoId) {
      kmError = 'Seleziona prima una automobile';
      return;
    }

    if (!value) {
      kmError = 'Inserisci un coefficiente valido';
      return;
    }

    const coeff = Number(value.replace(',', '.'));
    if (Number.isNaN(coeff) || coeff < 0) {
      kmError = 'Inserisci un coefficiente numerico valido';
      return;
    }

    kmError = null;
    coefficienteSaving = true;
    try {
      const updatedAuto = await updateAutomobileCoeff(selectedAutoId, coeff);
      const updatedAutoId = getAutoId(updatedAuto);
      if (updatedAutoId !== null) {
        automobili = automobili.map((auto) =>
          String(getAutoId(auto)) === String(updatedAutoId) ? updatedAuto : auto
        );
      }
      costoKmInput = String(updatedAuto.coefficiente ?? coeff);
    } catch (e: any) {
      kmError = e?.message || 'Errore aggiornamento coefficiente automobile';
    } finally {
      coefficienteSaving = false;
    }
  }

  async function loadAutomobili() {
    autoLoading = true;
    autoError = null;
    try {
      const list = await getAutomobili({ is_active: true });
      automobili = list.length ? list : await getAutomobili();
    } catch (e: any) {
      autoError = e?.message || 'Errore caricamento automobili';
      automobili = [];
    } finally {
      autoLoading = false;
    }
  }

  async function handleAutomobileChange(event: Event) {
    if (!item || isLocked) return;

    const nextAutoId = (event.currentTarget as HTMLSelectElement).value;
    const previousAutoId = selectedAutoId;
    selectedAutoId = nextAutoId;
    autoError = null;
    const seq = ++autoUpdateSeq;
    autoSaving = true;

    void updateTrasferta(item.id, {
      automobile: nextAutoId ? Number(nextAutoId) : null
    })
      .then((updated) => {
        if (seq !== autoUpdateSeq) return;
        item = updated;
        selectedAutoId = resolveSelectedAutoId(getTrasfertaAutoRawValue(updated), automobili);
        syncKmRateFromSelectedAuto();
      })
      .catch((e: any) => {
        if (seq !== autoUpdateSeq) return;
        selectedAutoId = previousAutoId;
        syncKmRateFromSelectedAuto();
        autoError = e?.message || 'Errore aggiornamento automobile della trasferta';
      })
      .finally(() => {
        if (seq !== autoUpdateSeq) return;
        autoSaving = false;
      });
  }

  async function handleReloadActions() {
    if (loading) return;

    showSpesaForm = false;
    createSpesaError = null;
    kmError = null;
    autoError = null;
    distanzaKm = null;
    partenza = DEFAULT_PARTENZA;
    arrivo = '';

    await loadDetail();
    refreshKey += 1;
  }

  async function handleValidateAction() {
    if (!item || loading) return;

    loading = true;
    error = null;
    try {
      const validate = useValidateTrasferta({ tId: item.id });
      const res = await validate();
      item = res.payload;
      await loadDetail();
    } catch (e: any) {
      error = e?.message || 'Errore validazione trasferta';
    } finally {
      loading = false;
    }
  }

  async function handleScontrinoGet(filename: string) {
    if (!item?.id) return;
    try {
      const { getScontrino } = useScontrini({ tId: item.id });
      const res = await getScontrino(filename);
      const url = URL.createObjectURL(res.payload);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e: any) {
      error = e?.message || 'Errore download scontrino';
    }
  }

  async function handleScontrinoDelete(filename: string) {
    if (!item?.id || isLocked) return;
    try {
      const { deleteScontrino } = useScontrini({ tId: item.id });
      await deleteScontrino(filename);
      refreshKey += 1;
    } catch (e: any) {
      error = e?.message || 'Errore eliminazione scontrino';
    }
  }

  async function loadDetail() {
    loading = true;
    error = null;
    try {
      const routeId = Number($page.params.id);
      const stateTrasf = ($page.state as any)?.trasf as Trasferta | undefined;
      item = stateTrasf?.id === routeId ? stateTrasf : null;

      if (!item) {
        const list = await getTrasferte();
        item = list.find((t) => Number(t.id) === routeId) ?? null;
      }

      if (!item) {
        throw new Error('Trasferta non trovata');
      }

      await loadAutomobili();
      selectedAutoId = resolveSelectedAutoId(getTrasfertaAutoRawValue(item), automobili);
      syncKmRateFromSelectedAuto();
      spese = await getSpeseByTrasferta(item.id);
    } catch (e: any) {
      error = e?.message || 'Errore caricamento dettaglio trasferta';
    } finally {
      loading = false;
    }
  }

  async function handleCreateSpesa(payload: SpesaCreate) {
    if (!item || creatingSpesa || isLocked) return;

    creatingSpesa = true;
    createSpesaError = null;

    try {
      const { addSpesa } = useCreateSpese({ tId: item.id });
      const created = await addSpesa(payload);
      spese = [created.payload, ...spese];
      showSpesaForm = false;
    } catch (e: any) {
      createSpesaError = e?.message || 'Errore creazione spesa';
    } finally {
      creatingSpesa = false;
    }
  }

  async function handleCalcolaDistanza() {
    if (isLocked) return;
    distanzaKm = await mapRef?.calcolaDistanza(partenza, arrivo) ?? null;
  }

  function handleRouteInputsEnter(event: KeyboardEvent) {
    if (event.key !== 'Enter') return;
    if (!partenza.trim() || !arrivo.trim()) return;
    handleCalcolaDistanza();
  }

  async function handleCreateKmSpesa() {
    if (!item || creatingSpesa || isLocked) return;

    const costoKm = Number(costoKmInput);
    if (distanzaKm === null || Number.isNaN(costoKm) || costoKm <= 0) {
      kmError = 'dati chilometrici mancanti';
      return;
    }

    creatingSpesa = true;
    kmError = null;
    try {
      const baseImporto = Number((distanzaKm * costoKm).toFixed(2));
      const importo = isKmBandieraRossa ? Number((baseImporto * 2).toFixed(2)) : baseImporto;
      const { addSpesa } = useCreateSpese({ tId: item.id });
      const created = await addSpesa({ type: 2, importo });
      spese = [created.payload, ...spese];
    } catch (e: any) {
      kmError = e?.message || 'Errore creazione spesa chilometrica';
    } finally {
      creatingSpesa = false;
    }
  }

  function handleClearRouteInputs() {
    if (isLocked) return;
    partenza = DEFAULT_PARTENZA;
    arrivo = '';
  }

  onMount(() => {
    partenza = DEFAULT_PARTENZA;
  });

  $: if (item?.utente_id) {
    timeEntryUser.setUser({ id: item.utente_id } as User);
  }

  $: if (token) {
    $page.params.id;
    loadDetail();
  }

  $: isLocked = item?.validation_level === 2;
  $: if (isLocked && showSpesaForm) {
    showSpesaForm = false;
  }

  $: autoOptions = automobili
    .map((auto) => {
      const id = getAutoId(auto);
      return id === null ? null : { id, label: getAutoLabel(auto) };
    })
    .filter((option): option is { id: number; label: string } => option !== null);
</script>

<div class=" p-4 grid gap-3">
  <LoaderOverlay show={loading} />
  {#key refreshKey}

  <div>
    {#if item}
      <h1 class="text-xl font-infinity tracking-[3px] font-semibold m-0">
        Trasferta a {item.azienda}
        <br />
        <span class="text-base font-medium">del {item.data}</span>
      </h1>
      <div class="font-semibold">
        {item.utente_nome} {item.utente_cognome}
      </div>
    {/if}
    <div class="flex justify-center items-center gap-3 mt-2">
      <button type="button" on:click={() => goto('/trasferte')} aria-label="Indietro">
        <FontAwesomeIcon
          icon={faArrowLeft}
          class="text-[150%]"
          style={`color: ${palette.secondary.main};`}
        />
      </button>

      <button type="button" on:click={handleReloadActions} aria-label="Ricarica dati">
        <FontAwesomeIcon
          icon={faRotate}
          class="text-[150%]"
          style={`color: ${palette.secondary.main};`}
        />
      </button>

      {#if isSuperuser}
        <button type="button" on:click={handleValidateAction} aria-label="Valida mese corrente">
          <FontAwesomeIcon
            icon={faCheck}
            class="text-[150%]"
            style={`color: ${palette.secondary.main};`}
          />
        </button>
      {/if}

    </div>
    
    <div
      class="relative mt-[14px] mx-auto grid w-full max-w-[1200px] grid-cols-1 gap-[14px] rounded-2xl border border-[#4f4f50] bg-[#e7e3e3] p-2.5 shadow-[0_10px_25px_-5px_rgba(0,0,0,0.05),0_8px_10px_-6px_rgba(0,0,0,0.05)] md:grid-cols-[minmax(320px,1fr)_minmax(420px,1.1fr)]"
      class:locked-block={isLocked}
      class:validated-surface={isLocked}
    >
      <div class="min-h-[320px] rounded-xl bg-white p-3" class:locked-block={isLocked}>
        <LoadReceipts
          userId={$timeEntryUser.user?.id ?? null}
          tId={item?.id ?? null}
          onSavedFileClick={handleScontrinoGet}
          onSavedFileDelete={handleScontrinoDelete}
          disableSavedFileDelete={isLocked}
        />
      </div>
      <div class="grid gap-2.5">
        <div class="map-corner relative z-0 mx-auto h-[320px] w-full overflow-hidden rounded-xl bg-white shadow-[0_14px_36px_rgba(0,0,0,0.22)] max-sm:h-[220px]">
          <MapsPlugin bind:this={mapRef} />
        </div>
        <div class="mx-auto mt-3 grid w-full max-w-[760px] gap-2.5 rounded-xl border border-gray-300 bg-white px-2.5 py-2">
          <div class="flex flex-nowrap items-center gap-2.5 max-sm:flex-wrap">
            <button
              class="cursor-pointer rounded-[10px] border border-gray-300 bg-white px-3 py-2 text-[0.9rem] font-semibold transition hover:bg-gray-50"
              on:click={handleCalcolaDistanza}
              disabled={isLocked}
            >
              Calcola
            </button>
            <div class="rounded-[10px] bg-slate-50 px-2.5 py-2 text-[0.85rem] text-gray-900">
              {#if distanzaKm !== null}
                Km percorsi: {distanzaKm.toFixed(1)} km
              {:else}
                Km percorsi: -
              {/if}
            </div>
            <div class="flex items-center gap-2">
              <a
                class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border border-gray-300 bg-white text-[1rem] leading-none no-underline transition hover:bg-gray-50"
                href="https://iam.aci.it/auth/realms/Cittadini/protocol/openid-connect/auth?client_id=CostiChilometrici_WEB&redirect_uri=https%3A%2F%2Fcostikm.aci.it&state=503cec0d-8574-43f6-84f4-d5191b331511&response_mode=fragment&response_type=code&scope=openid&nonce=dbc044a4-b191-41e7-80aa-666e9a58ff19"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Apri costi chilometrici ACI"
                title="Costi chilometrici ACI"
              >
                <FontAwesomeIcon icon={faCar} />
              
              </a>
              <a
                class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border border-gray-300 bg-white text-[1rem] leading-none no-underline transition hover:bg-gray-50"
                href="https://www.google.com/maps"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Apri Google Maps"
                title="Google Maps"
              >
                <FontAwesomeIcon icon={faLocationDot} style="color: #f97316;" />
              
              </a>
              <button
                type="button"
                class="inline-flex h-[34px] w-[34px] items-center justify-center rounded-[9px] border text-[1rem] leading-none transition"
                class:border-gray-300={!isKmBandieraRossa}
                class:bg-white={!isKmBandieraRossa}
                class:hover:bg-gray-50={!isKmBandieraRossa}
                class:text-gray-700={!isKmBandieraRossa}
                class:border-red-600={isKmBandieraRossa}
                class:bg-red-500={isKmBandieraRossa}
                class:text-white={isKmBandieraRossa}
                aria-label="Raddoppia importo chilometrico"
                aria-pressed={isKmBandieraRossa}
                title="Andata e Ritorno"
                on:click={() => (isKmBandieraRossa = !isKmBandieraRossa)}
                disabled={isLocked}
              >
                <FontAwesomeIcon icon={faFlag} />
              </button>
            </div>
            <div class="ml-auto inline-grid min-w-[180px] grid-cols-[minmax(110px,1fr)_auto] items-center gap-2 max-sm:ml-0 max-sm:min-w-full max-sm:grid-cols-[1fr_auto]">
              <input
                class="w-[160px] max-sm:w-full rounded-[10px] border border-gray-300 bg-white px-2 py-2 text-[0.8rem] outline-none focus:border-gray-400 focus:shadow-[0_0_0_2px_rgba(156,163,175,0.18)]"
                type="text"
                placeholder="Coeff. auto selezionata"
                value={costoKmInput}
                on:change={handleCoefficienteChange}
                disabled={isLocked}
              />
              <button
                class="min-w-[44px] cursor-pointer rounded-[10px] border border-gray-300 bg-white px-3 py-2 text-[1rem] font-bold transition hover:bg-gray-50"
                type="button"
                on:click={handleCreateKmSpesa}
                disabled={creatingSpesa || coefficienteSaving || isLocked}
                aria-label="Crea spesa chilometrica"
              >
                <FontAwesomeIcon icon={faCalculator} />
              </button>
            </div>
          </div>
	          <div class="grid grid-cols-[1fr_1fr_auto] items-center gap-2.5 max-sm:grid-cols-[1fr_auto]">
	            <input
	              class="w-full rounded-[10px] border border-gray-300 bg-white px-3 py-2.5 text-[0.9rem] outline-none focus:border-gray-400 focus:shadow-[0_0_0_2px_rgba(156,163,175,0.18)] max-sm:col-span-2"
              type="text"
              placeholder="Inserisci partenza"
              bind:value={partenza}
              on:keydown={handleRouteInputsEnter}
              disabled={isLocked}
            />
            <input
              class="w-full rounded-[10px] border border-gray-300 bg-white px-3 py-2.5 text-[0.9rem] outline-none focus:border-gray-400 focus:shadow-[0_0_0_2px_rgba(156,163,175,0.18)]"
              type="text"
              placeholder="Inserisci arrivo"
              bind:value={arrivo}
              on:keydown={handleRouteInputsEnter}
              disabled={isLocked}
            />
            <button
              class="inline-flex h-[42px] w-[42px] cursor-pointer items-center justify-center rounded-[10px] border border-gray-300 bg-white transition hover:bg-gray-50"
              type="button"
              on:click={handleClearRouteInputs}
              disabled={isLocked}
              aria-label="Pulisci partenza e arrivo"
              title="Pulisci campi"
            >
              <FontAwesomeIcon
                icon={faBroom}
                class="text-[120%]"
                style={`color: ${palette.secondary.main};`}
	              />
	            </button>
	          </div>
	          <section class="grid gap-2.5 rounded-xl border border-gray-200 bg-gray-50 p-3" class:validated-surface={isLocked}>
	            <h2 class="m-0 text-base font-semibold">Automobile Trasferta</h2>

	            <div class="grid gap-1.5">
	              <select
	                id="trasferta-auto-select"
	                class="w-full rounded-[10px] border border-gray-300 bg-white px-3 py-2.5 text-[0.95rem] outline-none focus:border-gray-400 focus:shadow-[0_0_0_2px_rgba(156,163,175,0.18)]"
	                bind:value={selectedAutoId}
	                on:change={handleAutomobileChange}
	                disabled={autoLoading || isLocked}
	              >
	                <option value="">Nessuna automobile</option>
	                {#each autoOptions as option (option.id)}
	                  <option value={String(option.id)}>{option.label}</option>
	                {/each}
	              </select>
	            </div>

	            {#if autoLoading}
	              <p class="text-sm text-gray-500">Caricamento automobili...</p>
	            {:else if autoSaving}
	              <p class="text-sm text-gray-500">Aggiornamento automobile...</p>
	            {/if}

	            {#if autoError}
	              <p class="text-sm text-red-700">{autoError}</p>
	            {/if}
	          </section>
	        </div>
	      </div>
	    </div>

  </div>

  {#if kmError}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      on:click={() => (kmError = null)}
    >
      <div on:click|stopPropagation>
        <ErrorCard message={kmError} onClose={() => (kmError = null)} />
      </div>
    </div>
  {/if}

  {#if loading}
    <p class="text-center text-gray-500">Caricamento...</p>

  {:else if error}
    <p class="text-center text-red-700">{error}</p>

  {:else if item}

	    <!-- CARD SPESE -->
	    <section class="bg-white border border-gray-200 rounded-xl p-4 grid gap-2 shadow-sm" class:validated-surface={isLocked}>
      <div class="mb-2 flex items-center justify-between">
        <h2 class="text-lg font-semibold">Spese di trasferta</h2>
        <button
          class="h-8 w-8 rounded-full border border-gray-300 bg-white text-lg leading-none transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          on:click={() => (showSpesaForm = !showSpesaForm)}
          disabled={creatingSpesa || isLocked}
          aria-label="Aggiungi spesa"
        >
          +
        </button>
      </div>

      {#if showSpesaForm}
        <FormSpesa
          saving={creatingSpesa}
          error={createSpesaError}
          on:submit={(e) => handleCreateSpesa(e.detail)}
          on:cancel={() => {
            showSpesaForm = false;
            createSpesaError = null;
          }}
        />
      {/if}
      
      {#if spese.length === 0}
        <p class="text-center text-gray-500">Nessuna spesa trovata</p>
      {:else}
        <div class="grid gap-2">
          {#each spese as s (s.id)}
            <SpeseCard spesa={s} readonly={isLocked} />
          {/each}
        </div>
      {/if}
    </section>

    {#if isLocked}
      <p class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
        Trasferta con validation level 2: modifiche, upload file e inserimenti disabilitati.
      </p>
    {/if}
  {/if}
  {/key}
</div>

<style>
  .validated-surface {
    position: relative;
    overflow: hidden;
    background: #dcfce7 !important;
    border-color: #86efac !important;
  }

  .validated-surface::before {
    content: 'VALIDATE';
    position: absolute;
    left: -8%;
    top: 50%;
    width: 116%;
    font-family: 'infinity', sans-serif;
    font-size: clamp(2.4rem, 7vw, 5.5rem);
    line-height: 1;
    text-align: center;
    letter-spacing: 0.08em;
    color: rgba(22, 101, 52, 0.14);
    transform: translateY(-50%) rotate(-16deg);
    pointer-events: none;
    user-select: none;
    z-index: 0;
    white-space: nowrap;
  }

  .validated-surface > * {
    position: relative;
    z-index: 1;
  }

  .locked-block {
    pointer-events: none;
    user-select: none;
    opacity: 0.65;
  }

  .map-corner :global(.wrapper) {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }

  .map-corner :global(.panel) {
    display: none !important;
  }

  .map-corner :global(.map-wrap),
  .map-corner :global(.map) {
    height: 100% !important;
  }
</style>

