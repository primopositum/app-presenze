<script lang="ts">
  import { Motion } from 'svelte-motion';
  import { createEventDispatcher } from 'svelte';
  import type { UpdateAccountPayload, User } from '$lib/services/users';
  import { useCreateSignatureApi, useLatestSignatureApi } from '$lib/hooks/useSignatureApi';
  import { getJiraTokenStatus, overwriteJiraToken } from '$lib/services/jiraCredentials';
  import ErrorCard from '$lib/components/ErrorCard.svelte';

  export let user: User;
  /**
   * Utente loggato.
   * - is_staff / is_superuser  → può modificare qualsiasi profilo
   * - id === user.id           → può modificare solo il proprio
   */
  export let currentUser: {
    id?: number;
    is_staff?: boolean;
    is_superuser?: boolean;
  } = {};

  export let onSave: ((payload: UpdateAccountPayload) => void | Promise<void>) | null = null;
  export let onDelete: ((userId: number) => void | Promise<void>) | null = null;

  const dispatch = createEventDispatcher<{ save: UpdateAccountPayload }>();

  // ── permessi ─────────────────────────────────────────────────────────

  

  $: isAdmin = currentUser?.is_staff === true || currentUser?.is_superuser === true;
  $: isOwnProfile = !!currentUser?.id && Number(currentUser.id) === Number(user.id);
  $: canEdit = isAdmin || isOwnProfile;
  $: canDelete = isAdmin && !isSuperProfile && Number(currentUser?.id) !== Number(user.id);
  $: canManageSignature = isAdmin || isOwnProfile;

  // ── computed view ─────────────────────────────────────────────────────


  $: fullName       = `${user.nome ?? ''} ${user.cognome ?? ''}`.trim();
  $: initials       = `${user.nome?.[0] ?? ''}${user.cognome?.[0] ?? ''}`.toUpperCase();
  $: activeContract = user.contratti?.find((c) => c.is_active);
  $: roleLabel      = activeContract?.tipologia ?? 'Dipendente';
  $: isSuperProfile = user?.is_superuser === true;
  $: contractOreSett = activeContract?.ore_sett ?? user.contratti?.[0]?.ore_sett ?? [];
  $: contractWeeklyHours = (contractOreSett ?? []).reduce((sum, value) => sum + toHours(value), 0);

  // ── edit state ────────────────────────────────────────────────────────


  let editing      = false;
  let saving       = false;
  let deleting     = false;
  let showDeleteConfirm = false;
  let signatureLoading = false;
  let signatureUploading = false;
  let showSignatureModal = false;
  let signaturePreviewUrl = '';
  let saveError    = '';
  let signatureError = '';
  let signatureRequestError: string | null = null;
  let signatureUploadError: string | null = null;
  let signatureFileInput: HTMLInputElement | null = null;

  let editNome      = '';
  let editCognome   = '';
  let editEmail     = '';
  let editSaldo     = 0;
  let editIsActive  = false;
  let editTipologia = '';
  let jiraTokenLoading = false;
  let jiraTokenDraft = '';
  let jiraTokenMask = '';
  let jiraTokenError = '';
  let jiraTokenHasToken = false;
  let jiraTokenIsValid: boolean | null = null;
  let lastJiraTokenLoadedForUserId: number | null = null;
  const TARGET_WIDTH_CM = 5;
  const TARGET_HEIGHT_CM = 2.5;
  const TARGET_DPI = 300;
  const SIGNATURE_WIDTH = Math.round((TARGET_WIDTH_CM / 2.54) * TARGET_DPI);
  const SIGNATURE_HEIGHT = Math.round((TARGET_HEIGHT_CM / 2.54) * TARGET_DPI);

  function isSupportedSignatureFile(file: File) {
    const allowed = new Set([
      'image/png',
      'image/jpeg',
      'image/jpg',
      'image/webp',
      'image/bmp',
      'image/gif',
    ]);
    return allowed.has((file.type || '').toLowerCase());
  }

  function loadImageFromFile(file: File): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve(img);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Impossibile leggere l\'immagine firma.'));
      };
      img.src = url;
    });
  }

  function canvasToPngFile(canvas: HTMLCanvasElement, originalName: string): Promise<File> {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('Errore conversione immagine firma.'));
          return;
        }
        const base = originalName.replace(/\.[^/.]+$/, '') || 'signature';
        resolve(new File([blob], `${base}_600x300.png`, { type: 'image/png' }));
      }, 'image/png');
    });
  }

  async function normalizeSignature(file: File): Promise<File> {
    const img = await loadImageFromFile(file);
    const canvas = document.createElement('canvas');
    canvas.width = SIGNATURE_WIDTH;
    canvas.height = SIGNATURE_HEIGHT;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas non disponibile per la firma.');

    // Disegna su area fissa 600x300 (stretch controllato richiesto dal flusso).
    ctx.clearRect(0, 0, SIGNATURE_WIDTH, SIGNATURE_HEIGHT);
    ctx.drawImage(img, 0, 0, SIGNATURE_WIDTH, SIGNATURE_HEIGHT);
    return canvasToPngFile(canvas, file.name);
  }

  function fillEditFields() {
    editNome      = user.nome      ?? '';
    editCognome   = user.cognome   ?? '';
    editEmail     = user.email     ?? '';
    editSaldo     = Number(user.saldo?.valore_saldo_validato) || 0;
    editIsActive  = activeContract?.is_active ?? false;
    editTipologia = activeContract?.tipologia ?? '';
  }

  function startEdit() {
    if (!canEdit) return;
    fillEditFields();
    saveError = '';
    editing = true;
  }

  function cancelEdit() {
    editing  = false;
    saving   = false;
    saveError = '';
  }

  function openSignaturePicker() {
    if (!canManageSignature || signatureUploading) return;
    signatureFileInput?.click();
  }

  async function onSignatureFileSelected(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input?.files?.[0];
    if (!file) return;
    signatureError = '';
    signatureUploadError = null;
    signatureUploading = true;
    try {
      if (!isSupportedSignatureFile(file)) {
        throw new Error('Formato firma non supportato. Usa PNG, JPG/JPEG, WEBP, BMP o GIF.');
      }
      const normalizedFile = await normalizeSignature(file);
      const result = await useCreateSignatureApi({
        file: normalizedFile,
        user_id: user.id,
      });
      if (result.error) throw new Error(result.error);
      signaturePreviewUrl = result.signature?.preview_data_url ?? '';
      showSignatureModal = true;
    } catch (e) {
      signatureUploadError = e instanceof Error ? e.message : 'Errore caricamento firma';
    } finally {
      signatureUploading = false;
      input.value = '';
    }
  }

  async function viewLatestSignature() {
    if (!canManageSignature || signatureLoading) return;
    signatureError = '';
    signatureRequestError = null;
    signatureLoading = true;
    try {
      const result = await useLatestSignatureApi(user.id);
      if (result.error) throw new Error(result.error);
      if (!result.signature?.preview_data_url) {
        signatureError = 'Nessuna firma caricata per questo utente';
        return;
      }
      signaturePreviewUrl = result.signature.preview_data_url;
      showSignatureModal = true;
    } catch (e) {
      signatureRequestError = 'firma non caricata correttamente';
    } finally {
      signatureLoading = false;
    }
  }

  async function deleteProfile() {
    if (!canDelete || deleting || !onDelete) return;
    showDeleteConfirm = true;
  }

  async function confirmDeleteProfile() {
    if (!canDelete || deleting || !onDelete) return;

    deleting = true;
    saveError = '';
    try {
      await onDelete(user.id);
      showDeleteConfirm = false;
    } catch (e) {
      saveError = e instanceof Error ? e.message : 'Errore durante l\'eliminazione';
    } finally {
      deleting = false;
    }
  }

  async function saveEdit() {
    if (!canEdit || saving) return;

    const payload: UpdateAccountPayload = { id: user.id, user_id: user.id };

    const trimmedNome = editNome.trim();
    const trimmedCognome = editCognome.trim();
    const trimmedEmail = editEmail.trim();

    // Invia solo i campi effettivamente modificati
    if (trimmedNome !== (user.nome ?? '')) payload.nome = trimmedNome;
    if (trimmedCognome !== (user.cognome ?? '')) payload.cognome = trimmedCognome;

    // Email: confronto case-insensitive, in linea con il backend
    if (trimmedEmail.toLowerCase() !== (user.email ?? '').trim().toLowerCase()) {
      payload.email = trimmedEmail;
    }

    if (isAdmin) {
      if (user.saldo) {
        const saldoOriginale = Number(user.saldo.valore_saldo_validato) || 0;
        if (editSaldo !== saldoOriginale) {
          payload.saldo = {
            valore_saldo_validato: String(editSaldo),
            valore_saldo_sospeso: String(Number(user.saldo?.valore_saldo_sospeso) || 0)
          };
        }
      }
      if (activeContract) {
        if (editTipologia !== (activeContract.tipologia ?? '') || editIsActive !== activeContract.is_active) {
          payload.contratti = [{
            is_active: editIsActive,
            tipologia: editTipologia
          }];
        }
      }
    }

    const nextJiraToken = jiraTokenDraft.trim();
    const shouldOverwriteJiraToken = isOwnProfile && nextJiraToken.length > 0;
    const hasProfileChanges = Object.keys(payload).some((key) => key !== 'id' && key !== 'user_id');
    if (!hasProfileChanges && !shouldOverwriteJiraToken) {
      editing = false;
      return;
    }

    saving    = true;
    saveError = '';

    try {
      if (hasProfileChanges) {
        if (onSave) {
          await onSave(payload);
        } else {
          dispatch('save', payload);
        }
      }
      if (shouldOverwriteJiraToken) {
        await overwriteJiraToken(nextJiraToken);
        await loadJiraTokenStatus();
      }

      editing = false;
    } catch (e) {
      saveError = e instanceof Error ? e.message : 'Errore durante il salvataggio';
    } finally {
      saving = false;
    }
  }

  async function loadJiraTokenStatus() {
    if (!isOwnProfile) {
      jiraTokenLoading = false;
      jiraTokenMask = '';
      jiraTokenError = '';
      jiraTokenHasToken = false;
      jiraTokenIsValid = null;
      return;
    }

    jiraTokenLoading = true;
    jiraTokenError = '';
    try {
      const data = await getJiraTokenStatus();
      jiraTokenHasToken = !!data.token_present;
      jiraTokenIsValid = data.token_valid;
      jiraTokenMask = data.token_valid ? (data.masked_token || '*****') : '';
      jiraTokenError = data.token_present && data.token_valid === false ? (data.error || 'Token Jira non valido') : '';
    } catch (e) {
      jiraTokenHasToken = false;
      jiraTokenIsValid = null;
      jiraTokenMask = '';
      jiraTokenError = e instanceof Error ? e.message : 'Errore verifica token Jira';
    } finally {
      jiraTokenLoading = false;
    }
  }

  $: if (isOwnProfile && user?.id && lastJiraTokenLoadedForUserId !== Number(user.id)) {
    lastJiraTokenLoadedForUserId = Number(user.id);
    void loadJiraTokenStatus();
  }

  // ── 3-D tilt ─────────────────────────────────────────────────────────


  let rotateX = 0, rotateY = 0;
  let glowX = 50, glowY = 50;
  let isHover = false;

  function onMouseMove(e: MouseEvent) {
    const r  = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const dx = (e.clientX - r.left) / r.width;
    const dy = (e.clientY - r.top)  / r.height;
    rotateY  =  (dx - 0.5) * 6;
    rotateX  = -(dy - 0.5) * 6;
    glowX    = dx * 100;
    glowY    = dy * 100;
  }
  function onEnter() { isHover = true; }
  function onLeave() {
    isHover = false;
    rotateX = rotateY = 0;
    glowX = glowY = 50;
  }

  const fmtSaldo = (n: unknown) =>
    `${new Intl.NumberFormat('it-IT', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number(n) || 0)} h`;

  const fmtHours = (n: unknown) =>
    `${new Intl.NumberFormat('it-IT', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number(n) || 0)} h`;

  function toHours(value: unknown): number {
    if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
    const parsed = Number(String(value ?? '').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  }

</script>

<input
  bind:this={signatureFileInput}
  type="file"
  accept=".png,.jpg,.jpeg,.webp,.bmp,.gif,image/png,image/jpeg,image/webp,image/bmp,image/gif"
  class="hidden"
  on:change={onSignatureFileSelected}
/>

<div style="perspective: 900px;" class="mx-auto w-full max-w-[420px]">
  <Motion
    initial={{ opacity: 0, y: 32, scale: 0.94 }}
    animate={{ opacity: 1, y: 0,  scale: 1    }}
    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    let:motion
  >
    <div
      use:motion
      style="
        transform: rotateX({rotateX}deg) rotateY({rotateY}deg);
        transition: transform {isHover ? '0.14s' : '0.5s'} cubic-bezier(0.22,1,0.36,1);
        transform-style: preserve-3d;
        will-change: transform;
      "
      on:mousemove={onMouseMove}
      on:mouseenter={onEnter}
      on:mouseleave={onLeave}
      role="article"
      aria-label="Profilo di {fullName}"
    >

      <div class="
        relative w-full rounded-2xl overflow-visible
        bg-white border {isSuperProfile ? 'border-fuchsia-200 shadow-[0_4px_6px_-1px_rgba(217,70,239,.08),0_20px_50px_-8px_rgba(217,70,239,.18),0_2px_4px_rgba(0,0,0,.06)]' : 'border-orange-100 shadow-[0_4px_6px_-1px_rgba(249,115,22,.08),0_20px_50px_-8px_rgba(249,115,22,.15),0_2px_4px_rgba(0,0,0,.06)]'}
      ">

        <div
          class="absolute inset-0 pointer-events-none z-10 rounded-2xl overflow-hidden"
          style="background: radial-gradient(circle at {glowX}% {glowY}%, rgba(251,146,60,.035) 0%, transparent 65%);"
        ></div>

        <!-- ── BANNER ──────────────────────────────────────── -->


        <div class="relative h-28 overflow-hidden rounded-t-2xl {isSuperProfile ? 'banner-bg-super' : 'banner-bg'}">
          <div class="absolute inset-0 banner-grid"></div>
          <div class="absolute -top-8 -left-6  w-44 h-32 rounded-full {isSuperProfile ? 'bg-fuchsia-400' : 'bg-orange-400'} blur-3xl opacity-40"></div>
          <div class="absolute -top-6 -right-6 w-40 h-28 rounded-full {isSuperProfile ? 'bg-pink-300' : 'bg-amber-300'}  blur-3xl opacity-30"></div>
          <div class="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent {isSuperProfile ? 'via-fuchsia-300' : 'via-orange-300'} to-transparent"></div>

          <div class="absolute top-3 right-4">
            {#if editing && isAdmin}
              <input
                bind:value={editTipologia}
                class="edit-input text-[0.62rem] font-bold tracking-widest uppercase font-mono w-32 text-center"
                placeholder="Tipologia"
              />
            {:else}
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 text-white text-[0.62rem] font-bold tracking-widest uppercase font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                {editing ? editTipologia || roleLabel : roleLabel}
              </span>
            {/if}
          </div>

          {#if canEdit || canDelete || canManageSignature}
            <div class="absolute top-3 left-4 action-buttons">
              {#if canEdit}
                <button
                  type="button"
                  class="pencil-btn {editing ? 'pencil-btn--active' : ''}"
                  title={editing ? 'Stai modificando…' : 'Modifica profilo'}
                  aria-label="Modifica profilo"
                  on:click={() => !editing && startEdit()}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
                    <path d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L7.5 19.213l-4 1 1-4 12.362-12.726z"/>
                    <path d="M15 5l3 3"/>
                  </svg>
                </button>
              {/if}
              {#if canManageSignature}
                <button
                  type="button"
                  class="pen-btn"
                  title={signatureUploading ? 'Caricamento firma…' : 'Carica/Sovrascrivi firma'}
                  aria-label="Carica o sovrascrivi firma"
                  on:click={openSignaturePicker}
                  disabled={signatureUploading}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
                    <path d="M12 20h9"/>
                    <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>
                  </svg>
                </button>
                <button
                  type="button"
                  class="view-sign-btn {signatureLoading ? 'view-sign-btn--active' : ''}"
                  title="Visualizza ultima firma"
                  aria-label="Visualizza ultima firma"
                  on:click={viewLatestSignature}
                  disabled={signatureLoading}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              {/if}
              {#if canDelete}
                <button
                  type="button"
                  class="trash-btn {deleting ? 'trash-btn--active' : ''}"
                  title={deleting ? 'Eliminazione…' : 'Elimina account'}
                  aria-label="Elimina account"
                  on:click={deleteProfile}
                  disabled={deleting}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
                    <path d="M3 6h18"/>
                    <path d="M8 6V4h8v2"/>
                    <path d="M19 6l-1 14H6L5 6"/>
                    <path d="M10 11v6M14 11v6"/>
                  </svg>
                </button>
              {/if}
            </div>
          {/if}
        </div>

        <!-- ── AVATAR ROW ───────────────────────────────────── -->


        <div class="relative flex items-end justify-between px-5 -mt-9 z-30">
          <div class="relative w-[72px] h-[72px]">
            <div class="absolute -inset-[3px] rounded-full {isSuperProfile ? 'avatar-ring-super' : 'avatar-ring'}"></div>
            <div class="w-[72px] h-[72px] rounded-full bg-white border-[3px] border-white flex items-center justify-center select-none shadow-md">
              <span class="text-xl font-black {isSuperProfile ? 'text-fuchsia-500' : 'text-orange-500'} tracking-tighter leading-none">
                {#if editing}
                  {`${editNome[0] ?? ''}${editCognome[0] ?? ''}`.toUpperCase() || initials}
                {:else}
                  {initials}
                {/if}
              </span>
            </div>
          </div>
          <span class="mb-1 px-2.5 py-1 rounded-lg {isSuperProfile ? 'bg-fuchsia-50 border-fuchsia-200 text-fuchsia-500' : 'bg-orange-50 border-orange-200 text-orange-500'} border text-[0.65rem] font-black font-mono tracking-wider">
            #{String(user.id ?? '—').padStart(4, '0')}
          </span>
        </div>

        <!-- ── BODY ────────────────────────────────────────── -->


        <div class="px-5 pb-5 pt-3 relative z-20">

          <div class="flex items-center gap-1.5 mt-2">
            {#if editing}
              <input bind:value={editNome}    class="edit-input w-[45%]" placeholder="Nome"    />
              <input bind:value={editCognome} class="edit-input w-[45%]" placeholder="Cognome" />
            {:else}
              <h2 class="text-lg font-black tracking-tight text-zinc-900 leading-tight">{fullName}</h2>
              <svg viewBox="0 0 20 20" fill="none" class="w-[18px] h-[18px] shrink-0">
                <circle cx="10" cy="10" r="9" fill="#f97316"/>
                <path d="M6 10l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            {/if}
          </div>

          <div class="h-px bg-gradient-to-r {isSuperProfile ? 'from-fuchsia-200 via-fuchsia-100' : 'from-orange-200 via-orange-100'} to-transparent mt-3 mb-4"></div>

          <!-- ── INFO ROWS ─────────────────────────────────── -->


          <div class="flex flex-col gap-2.5">
            {#if editing && isAdmin}
              <div class="flex items-center justify-between px-3.5 py-3 rounded-xl bg-zinc-50 border border-zinc-100">
                <span class="text-xs text-zinc-500 font-semibold tracking-wide">Tipologia</span>
                <input
                  bind:value={editTipologia}
                  class="edit-input w-40 text-center text-[0.72rem] font-bold tracking-wide"
                  placeholder="Tipologia"
                />
              </div>
            {/if}

            <div class="flex items-center justify-between px-3.5 py-3 rounded-xl {isSuperProfile ? 'bg-fuchsia-50 border-fuchsia-100 hover:bg-fuchsia-100 hover:border-fuchsia-200' : 'bg-orange-50 border-orange-100 hover:bg-orange-100 hover:border-orange-200'} border transition-all duration-200">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg {isSuperProfile ? 'bg-fuchsia-100' : 'bg-orange-100'} flex items-center justify-center shrink-0">
                  <svg viewBox="0 0 20 20" fill="none" class="w-3.5 h-3.5 {isSuperProfile ? 'text-fuchsia-500' : 'text-orange-500'}">
                    <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.8"/>
                    <path d="M10 6.5V10L12.8 11.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <span class="text-xs text-zinc-500 font-semibold tracking-wide">Saldo ore</span>
              </div>
              {#if editing && isAdmin}
                <input
                  bind:value={editSaldo}
                  type="number"
                  step="0.5"
                  class="edit-input w-24 text-right font-mono text-sm"
                  placeholder="0"
                />
              {:else}
                <span class="text-sm font-black {isSuperProfile ? 'text-fuchsia-600' : 'text-orange-600'} font-mono tabular-nums">
                  {fmtSaldo(editing ? editSaldo : user.saldo?.valore_saldo_validato)}
                </span>
              {/if}
            </div>

            <div class="flex items-center justify-between px-3.5 py-3 rounded-xl bg-zinc-50 border border-zinc-100">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                  <svg viewBox="0 0 20 20" fill="none" class="w-3.5 h-3.5 text-zinc-400">
                    <path d="M4 5.8h12M4 10h12M4 14.2h12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
                  </svg>
                </div>
                <span class="text-xs text-zinc-500 font-semibold tracking-wide">Contratto</span>
              </div>
              <span class="text-sm font-black text-zinc-700 font-mono tabular-nums">
                {fmtHours(contractWeeklyHours)}
              </span>
            </div>
            <!-- jira token row -->
            <div class="flex items-center justify-between px-3.5 py-3 rounded-xl bg-zinc-50 border border-zinc-100">
              <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                  <svg viewBox="0 0 20 20" fill="none" class="w-3.5 h-3.5 text-zinc-400">
                    <rect x="4.5" y="9" width="11" height="7.5" rx="1.6" stroke="currentColor" stroke-width="1.6" />
                    <path d="M7.5 9V7.6a2.5 2.5 0 015 0V9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                  </svg>
                </div>
                <span class="text-xs text-zinc-500 font-semibold tracking-wide">Token Jira</span>
              </div>
              {#if isOwnProfile && editing}
                <div class="flex items-center gap-1.5">
                  <input
                    bind:value={jiraTokenDraft}
                    type="password"
                    class="edit-input w-36 text-right font-mono text-xs"
                    placeholder="Sovrascrivi token"
                    autocomplete="new-password"
                    disabled={saving}
                  />
                </div>
              {:else}
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-zinc-700 truncate max-w-[110px]">
                    {#if jiraTokenLoading}
                      Verifica...
                    {:else if jiraTokenHasToken && jiraTokenIsValid === true}
                      {jiraTokenMask || '*****'}
                    {:else}
                      {' '}
                    {/if}
                  </span>
                </div>
              {/if}
            </div>
            {#if !editing && isOwnProfile && jiraTokenHasToken && jiraTokenIsValid === false && jiraTokenError}
              <p class="text-[0.72rem] text-red-500 font-medium px-1">{jiraTokenError}</p>
            {/if}

            <!-- contratto attivo toggle — solo admin in edit -->
            {#if editing && isAdmin}
              <div class="flex items-center justify-between px-3.5 py-3 rounded-xl bg-zinc-50 border border-zinc-100">
                <div class="flex items-center gap-2.5">
                  <div class="w-7 h-7 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                    <svg viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5 text-zinc-400">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                  <span class="text-xs text-zinc-500 font-semibold tracking-wide">Contratto attivo</span>
                </div>
                <button
                  type="button"
                  class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none {editIsActive ? (isSuperProfile ? 'bg-fuchsia-500' : 'bg-orange-500') : 'bg-zinc-300'}"
                  on:click={() => (editIsActive = !editIsActive)}
                  aria-checked={editIsActive}
                  role="switch"
                >
                  <span class="inline-block h-4 w-4 rounded-full bg-white shadow-sm transform transition-transform duration-200 {editIsActive ? 'translate-x-6' : 'translate-x-1'}"></span>
                </button>
              </div>
            {/if}

          </div>

          <!-- ── FOOTER / AZIONI ─────────────────────────────── -->
           
          {#if signatureError}
            <p class="mt-2 text-[0.72rem] text-red-500 font-medium">{signatureError}</p>
          {/if}

          {#if editing}
            {#if saveError}
              <p class="mt-3 text-[0.72rem] text-red-500 font-medium">{saveError}</p>
            {/if}
            <div class="mt-4 pt-3.5 border-t {isSuperProfile ? 'border-fuchsia-50' : 'border-orange-50'} flex items-center gap-2">
              <button
                type="button"
                class="flex-1 py-2.5 rounded-xl text-white text-xs font-bold tracking-wide transition-all duration-150
                       {saving
                         ? (isSuperProfile ? 'bg-fuchsia-300 cursor-not-allowed' : 'bg-orange-300 cursor-not-allowed')
                         : (isSuperProfile ? 'bg-fuchsia-500 hover:bg-fuchsia-600 active:scale-95' : 'bg-orange-500 hover:bg-orange-600 active:scale-95')}"
                disabled={saving}
                on:click={saveEdit}
              >
                {#if saving}
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
                    Salvataggio…
                  </span>
                {:else}
                  ✓ Salva modifiche
                {/if}
              </button>
              <button
                type="button"
                class="px-4 py-2.5 rounded-xl bg-zinc-100 hover:bg-zinc-200 active:scale-95 text-zinc-500 text-xs font-bold tracking-wide transition-all duration-150"
                disabled={saving}
                on:click={cancelEdit}
              >
                Annulla
              </button>
            </div>
          {:else}
            <Motion
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
              let:motion
            >
              <div use:motion class="mt-4 pt-3.5 border-t {isSuperProfile ? 'border-fuchsia-50' : 'border-orange-50'} flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full {isSuperProfile ? 'bg-fuchsia-400 shadow-[0_0_6px_rgba(217,70,239,.6)]' : 'bg-orange-400 shadow-[0_0_6px_rgba(251,146,60,.6)]'} animate-pulse"></span>
                  <span class="text-[0.7rem] text-zinc-400 font-medium tracking-wide">
                    {activeContract?.is_active ? 'Attivo' : 'Non attivo'}
                  </span>
                </div>
                {#if canEdit}
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg {isSuperProfile ? 'bg-fuchsia-100 hover:bg-fuchsia-200 text-fuchsia-700' : 'bg-orange-100 hover:bg-orange-200 text-orange-700'} text-[0.68rem] font-semibold transition-colors"
                    on:click={startEdit}
                  >
                    Modifica profilo
                  </button>
                {:else}
                  <span class="text-[0.68rem] text-zinc-400 font-medium">{fullName}</span>
                {/if}
              </div>
            </Motion>
          {/if}

        </div>
      </div>
    </div>
  </Motion>
</div>

{#if showSignatureModal}
  <div class="sign-backdrop" on:click={() => (showSignatureModal = false)} />
  <div class="sign-modal" role="dialog" aria-modal="true" on:click|stopPropagation>
    <div class="sign-modal-header">
      <h3 class="text-sm font-bold text-zinc-800">Firma Utente</h3>
      <button type="button" class="modal-close-btn" on:click={() => (showSignatureModal = false)} aria-label="Chiudi">×</button>
    </div>
    {#if signaturePreviewUrl}
      <div class="sign-preview">
        <img src={signaturePreviewUrl} alt="Firma utente" class="sign-preview-image" />
      </div>
    {:else}
      <p class="text-sm text-zinc-500">Nessuna firma disponibile.</p>
    {/if}
  </div>
{/if}

{#if signatureRequestError}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    on:click={() => (signatureRequestError = null)}
  >
    <div on:click|stopPropagation>
      <ErrorCard message={signatureRequestError} onClose={() => (signatureRequestError = null)} />
    </div>
  </div>
{/if}

{#if signatureUploadError}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    on:click={() => (signatureUploadError = null)}
  >
    <div on:click|stopPropagation>
      <ErrorCard message={signatureUploadError} onClose={() => (signatureUploadError = null)} />
    </div>
  </div>
{/if}

{#if showDeleteConfirm}
  <div class="confirm-backdrop" on:click={() => !deleting && (showDeleteConfirm = false)} />
  <div class="confirm-modal" role="dialog" aria-modal="true" on:click|stopPropagation>
    <h3 class="confirm-title">Conferma eliminazione</h3>
    <p class="confirm-text">
      Vuoi eliminare definitivamente l'account <strong>#{user.id}</strong> ({fullName})?
    </p>
    <div class="confirm-actions">
      <button
        type="button"
        class="confirm-cancel"
        on:click={() => (showDeleteConfirm = false)}
        disabled={deleting}
      >
        Annulla
      </button>
      <button
        type="button"
        class="confirm-delete"
        on:click={confirmDeleteProfile}
        disabled={deleting}
      >
        {deleting ? 'Eliminazione...' : 'Elimina'}
      </button>
    </div>
  </div>
{/if}

<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
  :global(body) { font-family: 'Sora', sans-serif; }
  .banner-bg { background: linear-gradient(135deg, #f0b799 0%, #f97316 50%, #fb923c 100%); }
  .banner-bg-super { background: linear-gradient(135deg, #f5b6ff 0%, #d946ef 50%, #ec4899 100%); }
  .banner-grid {
    background-image:
      linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
    background-size: 24px 24px;
  }
  .avatar-ring {
    background: conic-gradient(#f97316, #fbbf24, #fb923c, #f97316);
    animation: spin 5s linear infinite;
    -webkit-mask: radial-gradient(circle, transparent 50%, black 52%);
            mask: radial-gradient(circle, transparent 50%, black 52%);
  }
  .avatar-ring-super {
    background: conic-gradient(#d946ef, #f472b6, #ec4899, #d946ef);
    animation: spin 5s linear infinite;
    -webkit-mask: radial-gradient(circle, transparent 50%, black 52%);
            mask: radial-gradient(circle, transparent 50%, black 52%);
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .pencil-btn {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px;
    background: rgba(255,255,255,.22); backdrop-filter: blur(4px);
    border: 1px solid rgba(255,255,255,.35); color: #fff;
    cursor: pointer; transition: background .18s, transform .12s;
  }
  .pencil-btn:hover { background: rgba(255,255,255,.3); transform: scale(1.03); }
  .pencil-btn:active { transform: scale(.98); }
  .pencil-btn--active { background: rgba(255,255,255,.15); cursor: default; opacity: .55; }
  .pen-btn, .view-sign-btn {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px;
    background: rgba(255,255,255,.22); backdrop-filter: blur(4px);
    border: 1px solid rgba(255,255,255,.35); color: #fff;
    cursor: pointer; transition: background .18s, transform .12s;
  }
  .pen-btn:hover, .view-sign-btn:hover { background: rgba(255,255,255,.3); transform: scale(1.03); }
  .pen-btn:active, .view-sign-btn:active { transform: scale(.98); }
  .view-sign-btn--active { opacity: .7; cursor: default; }
  .trash-btn {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px;
    background: rgba(255,255,255,.22); backdrop-filter: blur(4px);
    border: 1px solid rgba(255,255,255,.35); color: #fff;
    cursor: pointer; transition: background .18s, transform .12s;
  }
  .trash-btn:hover { background: rgba(248,113,113,.35); transform: scale(1.03); }
  .trash-btn:active { transform: scale(.98); }
  .trash-btn--active { background: rgba(248,113,113,.25); cursor: default; opacity: .65; }

  .action-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .edit-input {
    background: rgba(249,115,22,.06); border: 1px solid rgba(249,115,22,.3);
    border-radius: 8px; padding: 5px 9px;
    font-family: 'Sora', sans-serif; font-size: 0.82rem; font-weight: 600;
    color: #18181b; outline: none; transition: border-color .15s, box-shadow .15s;
  }
  .edit-input:focus { border-color: #f97316; box-shadow: 0 0 0 3px rgba(249,115,22,.15); }
  .edit-input::placeholder { color: #a1a1aa; font-weight: 400; }
  .sign-backdrop {
    position: fixed;
    inset: 0;
    z-index: 3000;
    background: rgba(0, 0, 0, 0.45);
  }
  .sign-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 3001;
    width: min(560px, 92vw);
    background: white;
    border: 1px solid #e4e4e7;
    border-radius: 12px;
    padding: 14px;
  }
  .sign-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .modal-close-btn {
    border: none;
    background: transparent;
    font-size: 20px;
    line-height: 1;
    color: #71717a;
    cursor: pointer;
  }
  .sign-preview {
    border: 1px solid #e4e4e7;
    border-radius: 10px;
    padding: 12px;
    min-height: 120px;
    max-height: 320px;
    overflow: auto;
  }
  .sign-preview-image {
    display: block;
    max-width: 100%;
    height: auto;
    object-fit: contain;
  }

  @media (max-width: 640px) {
    .action-buttons {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, max-content));
      gap: 8px;
    }
  }

  .confirm-backdrop {
    position: fixed;
    inset: 0;
    z-index: 3200;
    background: rgba(0, 0, 0, 0.45);
  }
  .confirm-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 3201;
    width: min(420px, 92vw);
    background: #fff;
    border: 1px solid #e4e4e7;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  }
  .confirm-title {
    margin: 0 0 8px;
    font-size: 1rem;
    font-weight: 800;
    color: #27272a;
  }
  .confirm-text {
    margin: 0;
    font-size: 0.9rem;
    color: #52525b;
    line-height: 1.4;
  }
  .confirm-actions {
    margin-top: 14px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .confirm-cancel {
    border: 1px solid #d4d4d8;
    background: #fff;
    color: #3f3f46;
    border-radius: 10px;
    padding: 7px 12px;
    font-weight: 600;
    cursor: pointer;
  }
  .confirm-delete {
    border: 1px solid #ef4444;
    background: #ef4444;
    color: #fff;
    border-radius: 10px;
    padding: 7px 12px;
    font-weight: 700;
    cursor: pointer;
  }
  .confirm-cancel:disabled,
  .confirm-delete:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>




