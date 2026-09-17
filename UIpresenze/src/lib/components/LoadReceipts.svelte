<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { browser } from '$app/environment';
  import { fly, fade } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  import { usePdfAutoCurrentMonthList, useScontrini, useUploadPdfAuto } from '$lib/hooks/useTrasferte';
  import type { AutoPdfCurrentMonthItem } from '$lib/services/automobili';
  import type { ScontrinoFile } from '$lib/services/trasferte';

  interface UploadedFile {
    id: string;
    file: File;
    name: string;
    size: number;
    type: string;
    preview: string | null;
  }

  interface UploadComplete {
    success: boolean;
    message: string;
    files: number;
  }
 
  const dispatch = createEventDispatcher<{ upload: UploadedFile[]; uploadComplete: UploadComplete }>();

  export let mode: 'trasferta' | 'auto' = 'trasferta';
  export let userId: number | null = null;
  export let tId: number | string | null = null;
  export let autoId: number | string | null = null;
  export let meseAnno: string | undefined = undefined;
  export let onSavedFileClick: ((filename: string) => void | Promise<void>) | null = null;
  export let onSavedFileDelete: ((filename: string) => void | Promise<void>) | null = null;
  export let disableSavedFileDelete = false;
  export let disabled = false;
  // Blocca solo l'upload (dropzone/input), lasciando attivi lista e download:
  // usata per i visualizzatori in sola lettura (es. staff su trasferte altrui).
  export let disableUpload = false;

  $: resolvedUserId = userId ?? $timeEntryUser.user?.id ?? 0;
  $: uploadBlocked = disabled || disableUpload;

  let isDragging = false;
  let fileInput: HTMLInputElement;
  let allFiles: Array<ScontrinoFile | AutoPdfCurrentMonthItem> = [];
  let fileCounter = 1;
  let loadingFiles = false;
  let uploading = false;
  let uploadError: string | null = null;
  let lastLoadKey = '';
  let scontriniByTrasferta: ScontrinoFile[] = [];
  let autoPdfByCurrentMonth: AutoPdfCurrentMonthItem[] = [];
  let visibleFiles: Array<ScontrinoFile | AutoPdfCurrentMonthItem> = [];
  let selectedAutoMonth = '';
  let selectedAutoDate = '';

  function todayIsoMonth(): string {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    return `${yyyy}-${mm}`;
  }

  function meseAnnoToMonthValue(value?: string): string {
    const safe = (value || '').trim();
    if (!/^\d{2}_\d{4}$/.test(safe)) return '';
    const [mm, yyyy] = safe.split('_');
    return `${yyyy}-${mm}`;
  }

  function monthValueToIsoDate(value: string): string {
    const safe = (value || '').trim();
    if (!/^\d{4}-\d{2}$/.test(safe)) return '';
    return `${safe}-01`;
  }

  function monthValueToMeseAnno(value: string): string {
    const safe = (value || '').trim();
    if (!/^\d{4}-\d{2}$/.test(safe)) return '';
    const [yyyy, mm] = safe.split('-');
    return `${mm}_${yyyy}`;
  }

  function monthValueToMonthLabel(value: string): string {
    const safe = (value || '').trim();
    if (!/^\d{4}-\d{2}$/.test(safe)) return '';
    const [yyyy, mm] = safe.split('-');
    return `${mm}/${yyyy}`;
  }

  $: autoMonthDefault = meseAnnoToMonthValue(meseAnno) || todayIsoMonth();
  $: if (mode === 'auto' && !selectedAutoMonth) {
    selectedAutoMonth = autoMonthDefault;
  }
  $: selectedAutoDate = monthValueToIsoDate(selectedAutoMonth) || monthValueToIsoDate(todayIsoMonth());
  $: selectedAutoMeseAnno = monthValueToMeseAnno(selectedAutoMonth) || monthValueToMeseAnno(todayIsoMonth());
  $: selectedAutoMonthLabel = monthValueToMonthLabel(selectedAutoMonth) || monthValueToMonthLabel(todayIsoMonth());

  $: acceptedTypes = mode === 'auto' ? ['application/pdf'] : ['image/jpeg', 'image/png', 'application/pdf'];
  $: acceptAttr = mode === 'auto' ? '.pdf,application/pdf' : '.jpg,.jpeg,.png,.pdf,application/pdf';
  $: savedTitle = mode === 'auto' ? `PDF auto salvati (${selectedAutoMonthLabel})` : 'Scontrini salvati';
  $: emptyMessage = mode === 'auto'
    ? `Nessun PDF auto presente per ${selectedAutoMonthLabel}.`
    : 'Nessun file presente per questa trasferta.';
  $: loadingMessage = mode === 'auto'
    ? 'Aggiornamento lista PDF auto...'
    : 'Aggiornamento lista scontrini...';

  $: if (mode === 'trasferta') {
    scontriniByTrasferta = tId === null ? [] : (allFiles as ScontrinoFile[]);
    autoPdfByCurrentMonth = [];
  } else {
    scontriniByTrasferta = [];
    const source = Array.isArray(allFiles) ? (allFiles as AutoPdfCurrentMonthItem[]) : [];
    autoPdfByCurrentMonth = autoId === null
      ? source
      : source.filter((f) => String(resolveAutoIdFromFile(f) ?? '') === String(autoId));
  }

  $: visibleFiles = mode === 'auto' ? autoPdfByCurrentMonth : scontriniByTrasferta;
  $: loadKey = `${mode}:${tId ?? 'null'}:${autoId ?? 'null'}:${mode === 'auto' ? selectedAutoDate : '-'}`;
  $: if (browser && !disabled && loadKey !== lastLoadKey) {
    lastLoadKey = loadKey;
    void loadFiles();
  }

  function resolveAutoIdFromFile(file: AutoPdfCurrentMonthItem): number | string | null {
    return (
      file.auto_id ??
      (file as any).automobile_id ??
      (file as any).automobile ??
      (file as any).car_id ??
      (file as any).a_id ??
      (file as any).A_ID ??
      (file as any).id ??
      null
    );
  }

  async function loadFiles(): Promise<void> {
    if (disabled) return;
    loadingFiles = true;
    uploadError = null;
    try {
      if (mode === 'auto') {
        const listPdf = usePdfAutoCurrentMonthList(selectedAutoDate);
        const result = await listPdf();
        const payload = result.payload;
        allFiles = Array.isArray(payload)
          ? payload
          : Array.isArray((payload as any)?.files)
            ? (payload as any).files
          : Array.isArray((payload as any)?.results)
            ? (payload as any).results
            : Array.isArray((payload as any)?.items)
              ? (payload as any).items
              : [];
      } else {
        if (tId === null) {
          allFiles = [];
          return;
        }
        const { listScontrini } = useScontrini({ tId });
        const result = await listScontrini();
        const payload = result.payload;
        allFiles = Array.isArray(payload) ? payload : [];
      }
    } catch (e: unknown) {
      uploadError = e instanceof Error
        ? e.message
        : mode === 'auto'
          ? 'Errore caricamento PDF auto'
          : 'Errore caricamento scontrini';
    } finally {
      loadingFiles = false;
    }
  }

  function renameFile(file: File, index: number): File {
    const extByType: Record<string, string> = {
      'image/png': 'png',
      'image/jpeg': 'jpg',
      'application/pdf': 'pdf'
    };
    const ext = extByType[file.type] ?? 'bin';
    const idChunk = resolvedUserId;
    const userName = ($timeEntryUser.user?.nome ?? 'utente')
      .toLowerCase()
      .replace(/\s+/g, '-');
    const ymd = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const seq = String(idChunk + fileCounter + index).padStart(3, '0');
    const newName = `scontrino_${userName}_${ymd}_${seq}.${ext}`;
    return new File([file], newName, { type: file.type });
  }

  function safeRandomId(): string {
    const cryptoObj = (globalThis as any)?.crypto;
    if (cryptoObj?.randomUUID && typeof cryptoObj.randomUUID === 'function') {
      return cryptoObj.randomUUID();
    }
    if (cryptoObj?.getRandomValues && typeof cryptoObj.getRandomValues === 'function') {
      const bytes = new Uint8Array(16);
      cryptoObj.getRandomValues(bytes);
      return Array.from(bytes, (b: number) => b.toString(16).padStart(2, '0')).join('');
    }
    return `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  async function processFiles(rawFiles: FileList | null): Promise<void> {
    if (uploadBlocked || !rawFiles) return;
    const filtered = Array.from(rawFiles).filter((f) =>
      acceptedTypes.includes(f.type) || (mode === 'auto' && f.name.toLowerCase().endsWith('.pdf'))
    );
    if (!filtered.length) return;

    const processed: UploadedFile[] = filtered.map((file, i) => {
      const renamed = mode === 'trasferta' ? renameFile(file, i) : file;
      return {
        id: safeRandomId(),
        file: renamed,
        name: renamed.name,
        size: file.size,
        type: file.type,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null
      };
    });

    if (mode === 'trasferta') {
      fileCounter += filtered.length;
    }
    dispatch('upload', processed);

    uploading = true;
    uploadError = null;
    try {
      if (mode === 'auto') {
        if (autoId === null) {
          const message = 'Automobile non disponibile per il caricamento.';
          uploadError = message;
          dispatch('uploadComplete', { success: false, message, files: processed.length });
          return;
        }
        const effectiveMeseAnno = selectedAutoMeseAnno;
        const uploadPdf = useUploadPdfAuto({ auto_id: autoId });
        for (const file of processed) {
          await uploadPdf(file.file, effectiveMeseAnno);
        }
      } else {
        if (tId === null) {
          const message = 'Trasferta non disponibile per il caricamento.';
          uploadError = message;
          dispatch('uploadComplete', { success: false, message, files: processed.length });
          return;
        }
        const { uploadScontrino } = useScontrini({ tId });
        for (const file of processed) {
          await uploadScontrino(file.file);
        }
      }
      await loadFiles();
      dispatch('uploadComplete', {
        success: true,
        message: mode === 'auto' ? 'PDF auto caricati correttamente.' : 'Giustificativi caricati correttamente.',
        files: processed.length
      });
    } catch (e: unknown) {
      const message = e instanceof Error
        ? e.message
        : mode === 'auto'
          ? 'Errore upload PDF auto'
          : 'Errore upload scontrino';
      uploadError = message;
      dispatch('uploadComplete', { success: false, message, files: processed.length });
    } finally {
      uploading = false;
    }
  }

  function handleClick(): void {
    if (uploadBlocked) return;
    fileInput.click();
  }

  const autoMonthNames = [
    'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
  ];

  function buildAutoYearOptions(): number[] {
    const current = new Date().getFullYear();
    const years: number[] = [];
    for (let y = current - 5; y <= current + 1; y++) years.push(y);
    return years;
  }
  const autoYearOptions = buildAutoYearOptions();

  $: autoMonthParts = /^\d{4}-\d{2}$/.test(selectedAutoMonth)
    ? selectedAutoMonth.split('-')
    : todayIsoMonth().split('-');
  $: selectedAutoYear = autoMonthParts[0];
  $: selectedAutoMonthNum = autoMonthParts[1];

  function handleAutoMonthChange(e: Event): void {
    if (disabled) return;
    const mm = (e.target as HTMLSelectElement).value;
    selectedAutoMonth = `${selectedAutoYear}-${mm}`;
  }

  function handleAutoYearChange(e: Event): void {
    if (disabled) return;
    const yyyy = (e.target as HTMLSelectElement).value;
    selectedAutoMonth = `${yyyy}-${selectedAutoMonthNum}`;
  }

  function handleFileInput(e: Event): void {
    if (uploadBlocked) return;
    const input = e.target as HTMLInputElement;
    void processFiles(input.files);
    input.value = '';
  }

  function handleDrop(e: DragEvent): void {
    e.preventDefault();
    if (uploadBlocked) return;
    isDragging = false;
    void processFiles(e.dataTransfer?.files ?? null);
  }

  function handleDragOver(e: DragEvent): void {
    e.preventDefault();
    if (uploadBlocked) return;
    isDragging = true;
  }

  function handleDragLeave(): void {
    if (uploadBlocked) return;
    isDragging = false;
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function displayName(path: string): string {
    const chunks = path.split(/[\\/]/);
    return chunks[chunks.length - 1] ?? path;
  }

  function getFileName(file: ScontrinoFile | AutoPdfCurrentMonthItem): string {
    const rec = file as any;
    if (typeof rec.filename === 'string' && rec.filename.trim()) return rec.filename;
    if (typeof rec.path === 'string' && rec.path.trim()) return displayName(rec.path);
    if (typeof rec.url === 'string' && rec.url.trim()) return displayName(rec.url);
    return 'file';
  }

  function getFileSizeLabel(file: ScontrinoFile | AutoPdfCurrentMonthItem): string {
    const rec = file as any;
    const size = Number(rec.size_bytes ?? rec.size ?? 0);
    return Number.isFinite(size) && size > 0 ? formatSize(size) : '-';
  }

  function getFileKey(file: ScontrinoFile | AutoPdfCurrentMonthItem, idx: number): string {
    const rec = file as any;
    return String(rec.path ?? rec.url ?? rec.filename ?? rec.id ?? idx);
  }

  function shortenFileName(name: string, maxLen = 30): string {
    if (name.length <= maxLen) return name;
    const dotIndex = name.lastIndexOf('.');
    if (dotIndex > 0 && dotIndex < name.length - 1) {
      const ext = name.slice(dotIndex);
      const base = name.slice(0, dotIndex);
      const room = Math.max(6, maxLen - ext.length - 1);
      return `${base.slice(0, room)}...${ext}`;
    }
    return `${name.slice(0, Math.max(6, maxLen - 3))}...`;
  }

  async function handleSavedFileClick(file: ScontrinoFile | AutoPdfCurrentMonthItem) {
    if (mode !== 'trasferta' || !onSavedFileClick) return;
    const name = getFileName(file);
    await onSavedFileClick(name);
  }

  async function handleSavedFileDelete(file: ScontrinoFile | AutoPdfCurrentMonthItem) {
    if (mode !== 'trasferta' || !onSavedFileDelete || disableSavedFileDelete) return;
    const name = getFileName(file);
    await onSavedFileDelete(name);
    await loadFiles();
  }
</script>

<div class="mx-auto flex w-full max-w-[360px] flex-col gap-2.5 font-sans">
  {#if mode === 'auto'}
    <div class="flex items-center justify-between gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2">
      <span class="text-xs font-medium text-gray-600">Periodo PDF auto</span>
      <div class="flex items-center gap-1.5">
        <select
          class="rounded-lg border border-gray-300 bg-white py-2 pl-2.5 pr-8 text-xxs font-medium leading-normal text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          on:change={handleAutoMonthChange}
          disabled={disabled}
          aria-label="Mese PDF auto"
        >
          {#each autoMonthNames as name, i}
            {@const mm = String(i + 1).padStart(2, '0')}
            <option value={mm} selected={mm === selectedAutoMonthNum}>{name}</option>
          {/each}
        </select>
        <select
          class="rounded-lg border border-gray-300 bg-white py-2 pl-2.5 pr-8 text-xxs font-medium leading-normal text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          on:change={handleAutoYearChange}
          disabled={disabled}
          aria-label="Anno PDF auto"
        >
          {#each autoYearOptions as year}
            <option value={String(year)} selected={String(year) === selectedAutoYear}>{year}</option>
          {/each}
        </select>
      </div>
    </div>
  {/if}

  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    on:click={handleClick}
    on:drop={handleDrop}
    on:dragover={handleDragOver}
    on:dragleave={handleDragLeave}
    class="relative flex cursor-pointer select-none flex-col items-center justify-center gap-2.5 rounded-2xl border-2 border-dashed px-5 py-7 transition-all duration-300 ease-out
      {uploadBlocked ? 'cursor-not-allowed border-orange-200 bg-orange-50 opacity-70' : isDragging ? 'border-indigo-400 bg-indigo-50 shadow-[0_0_0_3px_rgba(99,102,241,0.16)]' : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100 hover:shadow-sm'}"
  >
    <input
      bind:this={fileInput}
      type="file"
      multiple
      accept={acceptAttr}
      class="hidden"
      on:change={handleFileInput}
      disabled={uploadBlocked}
    />

    <div
      class="mb-1 flex h-11 w-11 items-center justify-center rounded-xl transition-all duration-300
        {isDragging ? 'bg-indigo-200 -translate-y-0.5 scale-105' : 'bg-indigo-100'}"
    >
      <svg
        class="h-5 w-5 transition-colors duration-200 {isDragging ? 'text-indigo-700' : 'text-indigo-500'}"
        viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"
      >
        <path stroke-linecap="round" stroke-linejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
    </div>

    {#if uploadBlocked}
      <p class="text-sm font-semibold text-orange-700">
        Caricamento bloccato in modifica
      </p>
    {:else if isDragging}
      <p class="text-sm font-semibold text-indigo-600" in:fade={{ duration: 120 }}>
        Rilascia i file qui
      </p>
    {:else}
      <p class="text-sm font-medium text-gray-500 text-center">
        <span class="font-semibold text-indigo-600 underline decoration-indigo-300 underline-offset-2">
          Clicca per caricare
        </span>
        o trascina qui
      </p>
      <p class="text-xs text-gray-400">{mode === 'auto' ? 'PDF' : 'JPG, PNG, PDF'}</p>
    {/if}
  </div>

  {#if uploading || loadingFiles}
    <div class="px-1 text-xs text-gray-500">
      {uploading ? 'Caricamento in corso...' : loadingMessage}
    </div>
  {/if}

  {#if uploadError}
    <div class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
      {uploadError}
    </div>
  {/if}

  <div
    class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm"
    in:fly={{ y: 8, duration: 280, easing: cubicOut }}
  >
    <div class="flex items-center justify-between border-b border-gray-100 px-3 py-2.5">
      <span class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">{savedTitle}</span>
      <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-500">
        {visibleFiles.length}
      </span>
    </div>

    {#if visibleFiles.length === 0}
      <div class="px-3 py-2.5 text-sm text-gray-500">{emptyMessage}</div>
    {:else}
      <ul class="max-h-44 divide-y divide-gray-50 overflow-y-auto">
        {#each visibleFiles as file, idx (getFileKey(file, idx))}
          {@const fullName = getFileName(file)}
          {@const shortName = shortenFileName(fullName)}
          <li class="flex items-center justify-between gap-2 px-3 py-2 transition-colors duration-150 hover:bg-gray-50">
            <div class="min-w-0 flex-1">
              {#if mode === 'trasferta' && onSavedFileClick}
                <button
                  type="button"
                  class="block w-full truncate text-left text-sm font-medium text-gray-800 underline-offset-2 hover:underline"
                  title={fullName}
                  on:click={() => handleSavedFileClick(file)}
                >
                  {shortName}
                </button>
              {:else}
                <p class="truncate text-sm font-medium text-gray-800" title={fullName}>{shortName}</p>
              {/if}
            </div>
            {#if mode === 'trasferta' && onSavedFileDelete}
              <button
                type="button"
                class="inline-flex h-5 w-5 items-center justify-center rounded text-xs font-bold text-gray-300 transition hover:bg-red-50 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-40"
                on:click={() => handleSavedFileDelete(file)}
                disabled={disableSavedFileDelete}
                aria-label="Elimina scontrino"
                title="Elimina scontrino"
              >
                x
              </button>
            {/if}
            <p class="whitespace-nowrap text-xs text-gray-400">{getFileSizeLabel(file)}</p>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

</div>
