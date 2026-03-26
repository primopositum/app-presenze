<script lang="ts">
  type TimeEntry = {
    id: number;
    utente: string;
    data: string;
    ore_tot: string;
    type: number;
    validation_level: number;
    note?: string | null;
  };
  interface CustomState {
    userId: number;
  }
  import HippoSign from '$lib/components/HippoSign.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import TimeEntriesCalendar from '$lib/components/TimeEntriesCalendar.svelte';
  import type { DayHours } from '$lib/components/TimeEntriesCalendar.svelte'; 
  import { getTimeEntriesFromMonth, updateTimeEntry } from '$lib/services/timeEntries';
  import { refreshProfileUser } from '$lib/services/users';
  import ChangeMonth from '$lib/components/ChangeMonth.svelte';
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faArrowLeft, faRotate, faCheck, faFilePdf } from '@fortawesome/free-solid-svg-icons';
  import palette from '../../theme/palette.js';
  import LoaderOverlay from '$lib/components/loader/LoaderOverlay.svelte';
  import { auth } from '$lib/stores/auth';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  import { timeEntryReload } from '$lib/stores/timeEntryReload';
  import { goto } from '$app/navigation';
  import TimeEntryCard from '$lib/components/TimeEntryCard.svelte';
  import { useGeneratePDF, useUpdateValidationLevel } from '$lib/hooks/useSubmitHours';
  import type { User } from '$lib/services/users';
	import PreSetWeek from '$lib/components/PreSetWeek.svelte';
  import TimeEntryFormProvider from '$lib/components/ctx/TimeEntryFormProvider.svelte';
  import ErrorCard from '$lib/components/ErrorCard.svelte';
  import { hourBalanceExtra } from '$lib/stores/hourBalanceExtra';
  import { useOneUserApi } from '$lib/hooks/useUserApi.js';
  let loading = false;
  let error: string | null = null;

  const today = new Date(); 
  let year = today.getFullYear();
  let month = today.getMonth() + 1; // 1-12 
  let userId: number | null = null;
  let user: User | null = null;
  let entries: TimeEntry[] = [];
  let dayHours: DayHours[] = [];
  let selectedDate: string | null = null;
  let selectedEntries: TimeEntry[] = [];
  let updatingValidation = false;
  let confirmValidateOpen = false;
  let updateValidationLevel = useUpdateValidationLevel({ date: '' });
  let generatePdf = useGeneratePDF({ date: '' });
  let generatingPdf = false;
  let totalMonthHours = 0;
  let expectedMonthHours = 0;
  let noteDraft = '';
  let noteInitial = '';
  let noteSaving = false;
  let noteError: string | null = null;
  let canEditSelectedNotes = false;
  let noteSyncKey = '';
  let noteCursor = 0;
  let noteTouchStartX: number | null = null;
  let editableNoteEntries: TimeEntry[] = [];
  let currentNoteEntry: TimeEntry | null = null;
  let saldoVisuale = 0;
  let saldoValidatoVisuale = 0;
  let saldoValidatoOrig: number | string | null = null;
  let saldoTimeEntryVisuale: number | string | null = null;
  let saldoPersistenteVisuale: number | string | null = null;

  function splitYmd(dateStr: string) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return { y, m, d };
  }

  function toNumber(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  function typeLabel(t: number) {
    if (t === 1) return 'Lavoro';
    if (t === 2) return 'Ferie';
    if (t === 3) return 'Versamento Banca Ore';
    if (t === 4) return 'Prelievo Banca Ore';
    if (t === 5) return 'Malattia';
    if (t === 6) return 'Permesso Ordinario';
    if (t === 7) return 'Permesso Studio';
    if (t === 8) return 'Permesso 104';
    if (t === 9) return 'Permesso Ex fest';
    if (t === 10) return 'Permesso R.O.L.';
    if (t === 11) return 'Congedo di maternita';
    if (t === 12) return 'Sciopero';
    if (t === 13) return 'Festivita';
    return `Tipo ${t}`;
  }

  function getActiveOreSett(contratti?: Array<any>) {
    if (!contratti?.length) return null;
    const active = contratti.find((c) => c?.is_active) ?? contratti[0];
    return (active?.ore_sett as Array<any> | undefined) ?? null;
  }

  function calcExpectedMonthHours(yearNum: number, monthNum: number, oreSett: Array<any> | null) {
    if (!oreSett?.length) return 0;
    const daysInMonth = new Date(yearNum, monthNum, 0).getDate(); // monthNum: 1-12
    let total = 0;
    for (let day = 1; day <= daysInMonth; day += 1) {
      const weekday = new Date(yearNum, monthNum - 1, day).getDay(); // 0 dom, 1 lun...
      if (weekday >= 1 && weekday <= 5) {
        total += toNumber(oreSett[weekday - 1]);
      }
    }
    return total;
  }

  onMount(() => {
    timeEntryUser.init();
  });

  $: if ($auth.user && !$auth.user?.is_superuser) {
    timeEntryUser.setUser($auth.user);
  }

  $: if ($auth.user?.is_superuser && ($page.state as CustomState)?.userId && !$timeEntryUser.user) {
    timeEntryUser.setUser({ id: ($page.state as CustomState).userId } as User);
  }

  $: user = $timeEntryUser.user ?? null;
  $: userId = user?.id ?? null;
  $: {
    const monthStr = String(month).padStart(2, '0');
    const dateStr = `${year}-${monthStr}-01`;
    updateValidationLevel = useUpdateValidationLevel({
      date: dateStr,
      ...(userId ? { u_id: userId } : {})
    });
    generatePdf = useGeneratePDF({
      date: dateStr,
      ...(userId ? { u_id: userId } : {})
    });
  }

export const loadData = async () => {
    loading = true; error = null;
    try {
      const data = await getTimeEntriesFromMonth({
        date: new Date(year, month - 1, 1),
        utenteId: userId ?? undefined
      });
      entries = (data?.results || []) as TimeEntry[];      
      const groupedByDate = entries.reduce<Record<string, { hours: number; validation_level: number; entries: TimeEntry[] }>>((acc, entry) => {
        const { y, m } = splitYmd(entry.data);
        if (y !== year || m !== month) return acc;
        
        if (!acc[entry.data]) {
          acc[entry.data] = {
            hours: 0,
            validation_level: 0,
            entries: []
          };
        }
        
        const hours = Number(entry.ore_tot) || 0;
        const level = Number(entry.validation_level) || 0;
        
        acc[entry.data].hours += hours;
        acc[entry.data].validation_level = Math.max(acc[entry.data].validation_level, level);
        acc[entry.data].entries.push(entry);
        
        return acc;
      }, {});
      
      dayHours = Object.entries(groupedByDate).map(([date, data]) => ({
        date,
        hours: data.hours,
        validation_level: data.validation_level,
        entries: data.entries.map(e => ({
          id: e.id,
          date: e.data,
          type: e.type,
          ore_tot: Number(e.ore_tot),
          validation_level: e.validation_level
        }))
      }));
      await refreshProfileUser();
      await useOneUserApi($timeEntryUser.user?.id)
    } catch (e: any) {
      error = e?.message || 'Errore caricamento';
    } finally {
      loading = false;
    }
  }

  function prevMonth() {
    if (month === 1) { month = 12; year -= 1; } else { month -= 1; }
    selectedDate = null;
    loadData();
  }

  function nextMonth() {
    if (month === 12) { month = 1; year += 1; } else { month += 1; }
    selectedDate = null;
    loadData();
  }

  async function handleValidateMonth() {
    if (!entries.length) return;
    updatingValidation = true;
    error = null;
    try {
      await updateValidationLevel();
      await loadData();
    } catch (e: any) {
      error = e?.message || 'Errore validazione';
    } finally {
      updatingValidation = false;
    }
  }

  function openValidateConfirm() {
    if (!entries.length || loading || updatingValidation) return;
    confirmValidateOpen = true;
  }

  function closeValidateConfirm() {
    if (updatingValidation) return;
    confirmValidateOpen = false;
  }

  async function confirmValidateMonth() {
    await handleValidateMonth();
    confirmValidateOpen = false;
  }

  async function handleGeneratePdf() {
    if (generatingPdf || !userId) return;
    generatingPdf = true;
    error = null;
    try {
      const { payload } = await generatePdf();
      const url = URL.createObjectURL(payload);
      const link = document.createElement('a');
      link.href = url;
      link.download = `presenze-${year}-${String(month).padStart(2, '0')}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      error = e?.message || 'Errore generazione PDF';
    } finally {
      generatingPdf = false;
    }
  }

  function goToNoteIndex(nextIndex: number) {
    if (noteSaving || !editableNoteEntries.length) return;
    if (noteDraft !== noteInitial) {
      noteError = 'Salva la nota corrente prima di cambiare.';
      return;
    }
    const clamped = Math.max(0, Math.min(nextIndex, editableNoteEntries.length - 1));
    noteCursor = clamped;
    noteError = null;
  }

  function goPrevNote() {
    if (editableNoteEntries.length < 2) return;
    const next = noteCursor <= 0 ? editableNoteEntries.length - 1 : noteCursor - 1;
    goToNoteIndex(next);
  }

  function goNextNote() {
    if (editableNoteEntries.length < 2) return;
    const next = noteCursor >= editableNoteEntries.length - 1 ? 0 : noteCursor + 1;
    goToNoteIndex(next);
  }

  function handleNoteTouchStart(event: TouchEvent) {
    if (editableNoteEntries.length < 2) return;
    noteTouchStartX = event.touches[0]?.clientX ?? null;
  }

  function handleNoteTouchEnd(event: TouchEvent) {
    if (noteTouchStartX === null || editableNoteEntries.length < 2) return;
    const endX = event.changedTouches[0]?.clientX ?? noteTouchStartX;
    const delta = endX - noteTouchStartX;
    noteTouchStartX = null;
    if (Math.abs(delta) < 40) return;
    if (delta > 0) goPrevNote();
    else goNextNote();
  }

  async function saveSelectedDateNotes() {
    if (!selectedDate || !canEditSelectedNotes || noteDraft === noteInitial || !currentNoteEntry) return;
    const selectedEntry = currentNoteEntry;

    noteSaving = true;
    noteError = null;
    const nextNote = noteDraft;

    try {
      await updateTimeEntry(selectedEntry.id, {
        ...(userId ? { utente_id: userId } : {}),
        data: selectedEntry.data,
        type: selectedEntry.type,
        ore_tot: selectedEntry.ore_tot,
        note: nextNote
      });
      entries = entries.map((entry) =>
        entry.id === selectedEntry.id ? { ...entry, note: nextNote } : entry
      );
      noteInitial = nextNote;
    } catch (e: any) {
      noteError = e?.message || 'Errore salvataggio note';
    } finally {
      noteSaving = false;
    }
  }

  function handleNoteInput() {
    if (!selectedDate) return;
    noteError = null;
  }

  $: if (userId) {
    $timeEntryReload;
    loadData();
  }

  $: if (selectedDate) {
    selectedEntries = entries.filter((entry) => entry.data === selectedDate);
  } else {
    selectedEntries = [];
  }

  $: editableNoteEntries = selectedEntries.filter((entry) => entry.validation_level !== 2);
  $: canEditSelectedNotes = editableNoteEntries.length > 0;
  $: if (noteCursor >= editableNoteEntries.length) {
    noteCursor = Math.max(0, editableNoteEntries.length - 1);
  }
  $: currentNoteEntry = editableNoteEntries[noteCursor] ?? null;

  $: if (selectedDate) {
    const nextKey = currentNoteEntry
      ? `${selectedDate}|${currentNoteEntry.id}:${currentNoteEntry.note ?? ''}|${noteCursor}`
      : `${selectedDate}|none`;
    if (nextKey !== noteSyncKey && !noteSaving) {
      const nextNote = currentNoteEntry?.note ?? '';
      noteDraft = nextNote;
      noteInitial = nextNote;
      noteError = null;
      noteSyncKey = nextKey;
    }
  } else {
    noteDraft = '';
    noteInitial = '';
    noteError = null;
    noteSyncKey = '';
  }

  let saldoPeriodo = 0;
  $: saldoPeriodo = entries.reduce((acc, entry) => {
    const { y, m } = splitYmd(entry.data);
    if (y !== year || m !== month) return acc;
    const hours = Number(entry.ore_tot) || 0;
    if(entry.validation_level !== 2){
      if (entry.type === 3) return acc + hours;
      if (entry.type === 4) return acc - hours;
    }
    return acc;
  }, 0);

  $: hourBalanceExtra.set({
    title: 'saldo mese',
    saldo: saldoPeriodo,
    color: ['#EAFF3B', '#88FF78']
  });
  $: saldoValidatoOrig = $auth.user?.saldo?.valore_saldo_validato ?? null;
  $: saldoTimeEntryVisuale = $timeEntryUser.user?.saldo?.valore_saldo_validato ?? null;
  $: saldoPersistenteVisuale = $auth.user?.is_superuser ? saldoTimeEntryVisuale : saldoValidatoOrig;
  $: saldoValidatoVisuale = toNumber(saldoPersistenteVisuale);
  $: saldoVisuale = toNumber(saldoPersistenteVisuale) + toNumber(saldoPeriodo);

  $: totalMonthHours = entries.reduce((acc, entry) => {
    const { y, m } = splitYmd(entry.data);
    if (y !== year || m !== month) return acc;
    if (entry.type === 3) return acc;
    return acc + (Number(entry.ore_tot) || 0);
  }, 0);
  $: activeOreSett = getActiveOreSett(($timeEntryUser.user as any)?.contratti);
  $: expectedMonthHours = calcExpectedMonthHours(year, month, activeOreSett);
</script>


<TimeEntryFormProvider>
  {#key $timeEntryReload}
  <div class="w-full max-w-7xl mx-auto px-3 sm:px-4 relative">
    <div class="pointer-events-auto absolute left-3 top-2 z-30 max-sm:hidden">
      <HippoSign
        phrase1={`Ore svolte nel mese corrente: ${totalMonthHours} h`}
        phrase2={`Ore da dare questo mese: ${expectedMonthHours} h`}
        phrase3={`Ore rimanenti da fare: ${expectedMonthHours - totalMonthHours} h`}
      />
    </div>

  <div class="w-full flex justify-center my-2">
    <div class="flex w-full max-w-4xl flex-wrap items-center justify-center gap-3 px-2 max-sm:flex-nowrap max-sm:justify-start max-sm:overflow-x-auto">
      {#if $auth.user?.is_superuser}
        <div class="flex items-center justify-center gap-2">
          <div class="text-sm font-infinity tracking-[3px]">
            {user?.nome} {user?.cognome}
          </div>

          <button
            type="button"
            on:click={() => goto('/preMenu', { state: { route: 'presences' } })}
            aria-label="Torna al pre-menu presenze"
          >
            <FontAwesomeIcon
              icon={faArrowLeft}
              class="text-[150%]"
              style={`color: ${palette.secondary.main};`}
            />
          </button>
        </div>
      {/if}

      {#if !loading}
        <button type="button" on:click={loadData} disabled={loading} aria-label="Ricarica dati">
          <FontAwesomeIcon
            icon={faRotate}
            class="text-[150%]"
            style={`color: ${palette.secondary.main};`}
          />
        </button>
      {/if}

      <button
        type="button"
        on:click={openValidateConfirm}
        disabled={loading || updatingValidation || !entries.length}
        aria-label="Valida mese corrente"
      >
        <FontAwesomeIcon
          icon={faCheck}
          class="text-[150%]"
          style={`color: ${palette.secondary.main};`}
        />
      </button>

      <button
        type="button"
        on:click={handleGeneratePdf}
        disabled={loading || generatingPdf || !userId}
        aria-label="Scarica PDF mese corrente"
      >
        <FontAwesomeIcon
          icon={faFilePdf}
          class="text-[150%]"
          style={`color: ${palette.secondary.main};`}
        />
      </button>

      <LoaderOverlay show={loading} />
    </div>
  </div>
  <div class="my-2 rounded-xl border border-orange-100 bg-white/95 p-2 shadow-sm sm:hidden">
    <div class="mb-2 rounded-lg border border-slate-200 bg-slate-50 px-2 py-1.5 text-[clamp(0.68rem,2.8vw,0.9rem)] font-semibold text-slate-700">
      <div class="whitespace-nowrap overflow-hidden text-ellipsis">Saldo: {saldoVisuale}h</div>
      <div class="whitespace-nowrap overflow-hidden text-ellipsis text-[clamp(0.62rem,2.5vw,0.82rem)] text-slate-600">
        Saldo validato: {saldoValidatoVisuale}h
      </div>
    </div>
    <HippoSign
      alwaysOpen={true}
      inlinePanel={true}
      phrase1={`Ore svolte nel mese corrente: ${totalMonthHours} h`}
      phrase2={`Ore da dare questo mese: ${expectedMonthHours} h`}
      phrase3={`Ore rimanenti da fare: ${expectedMonthHours - totalMonthHours} h`}
    />
  </div>

  <br>
  <ChangeMonth 
    {year} 
    {month} 
    {loading} 
    onprev={prevMonth} 
    onnext={nextMonth} 
  />

  {#if error}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      on:click={() => (error = null)}
    >
      <div on:click|stopPropagation>
        <ErrorCard message={error} onClose={() => (error = null)} />
      </div>
    </div>
  {/if}

  <div class="flex gap-6 mt-4 flex-col lg:flex-row">
    <div class="flex-1 min-w-0">
      <TimeEntriesCalendar
        {year}
        {month}
        {dayHours}
        maxVisibleEntries={2}
        on:selectDay={(e) => {
          selectedDate = e.detail.date;
        }}
      />
    </div>
    <div class="w-full lg:w-[320px] lg:flex-shrink-0">
      {#if selectedDate}
        <TimeEntryCard timeEntries={selectedEntries} dateParam={selectedDate} />
        {#if selectedEntries.length > 0}
          <div class="mt-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm transition-all duration-200">
          <div class="mb-1 flex items-center justify-between gap-2">
            <label for="day-note" class="block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Note giorno
            </label>
            <span class="text-[11px] font-semibold text-slate-500">
              {#if currentNoteEntry}
                {typeLabel(currentNoteEntry.type)}
              {:else}
                -
              {/if}
            </span>
          </div>
          <textarea
            id="day-note"
            class="min-h-[92px] w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none transition-all duration-200 focus:border-orange-300 focus:bg-white focus:ring-2 focus:ring-orange-200 disabled:cursor-not-allowed disabled:opacity-60"
            bind:value={noteDraft}
            on:input={handleNoteInput}
            on:touchstart|passive={handleNoteTouchStart}
            on:touchend={handleNoteTouchEnd}
            disabled={!canEditSelectedNotes || noteSaving}
            placeholder={canEditSelectedNotes ? 'Scrivi una nota per il giorno selezionato' : 'Nessuna entry modificabile'}
          ></textarea>
          <div class="mt-2 grid grid-cols-[1fr_auto_auto] items-center gap-2 text-xs">
            <span class="text-slate-500">
              {#if noteSaving}
                Salvataggio note...
              {:else if noteError}
                <span class="text-red-600">{noteError}</span>
              {:else if noteDraft !== noteInitial}
                Modifiche non salvate
              {:else}
                Note salvate
              {/if}
            </span>

            <div class="flex items-center justify-center gap-1.5 justify-self-center">
              <button
                type="button"
                class="hidden h-6 w-6 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 sm:inline-flex"
                on:click={goPrevNote}
                disabled={!canEditSelectedNotes || noteSaving || editableNoteEntries.length < 2}
                aria-label="Nota precedente"
              >
                ‹
              </button>
              <div class="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-1">
                {#if editableNoteEntries.length === 0}
                  <span class="h-2 w-2 rounded-full bg-slate-300"></span>
                {:else}
                  {#each editableNoteEntries as entry, idx (entry.id)}
                    <button
                      type="button"
                      class={`h-2 w-2 rounded-full transition ${idx === noteCursor ? 'bg-orange-500' : 'bg-slate-300 hover:bg-slate-400'}`}
                      on:click={() => goToNoteIndex(idx)}
                      disabled={noteSaving}
                      aria-label={`Apri nota ${idx + 1} di ${editableNoteEntries.length}`}
                    ></button>
                  {/each}
                {/if}
              </div>
              <button
                type="button"
                class="hidden h-6 w-6 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 sm:inline-flex"
                on:click={goNextNote}
                disabled={!canEditSelectedNotes || noteSaving || editableNoteEntries.length < 2}
                aria-label="Nota successiva"
              >
                ›
              </button>
            </div>

            <button
              type="button"
              class="rounded-lg border border-slate-300 bg-white px-2.5 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
              on:click={() => void saveSelectedDateNotes()}
              disabled={!canEditSelectedNotes || noteSaving || noteDraft === noteInitial}
            >
              Salva
            </button>
          </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
  </div>
    <div><PreSetWeek/>   </div>
  {/key}
</TimeEntryFormProvider>

{#if confirmValidateOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" on:click={closeValidateConfirm}>
    <div
      class="w-full max-w-[350px] rounded-[22px] bg-[linear-gradient(163deg,#00ff75_0%,#3700ff_100%)] transition-all duration-300 hover:shadow-[0_0_30px_1px_rgba(0,255,117,0.3)]"
      on:click|stopPropagation
    >
      <div class="rounded-[20px] bg-[#171717] transition-all duration-200 hover:scale-[0.98]">
        <div class="flex flex-col gap-3 p-[1.4em] sm:p-[2em]">
          <p class="mb-4 text-center text-[1.2em] font-bold text-white">Conferma validazione</p>
          <p class="text-center text-[0.95em] font-medium text-[#00ff75]">Sei sicuro di validare questo mese?</p>

          <div class="mt-4 flex flex-col justify-center gap-2 sm:flex-row sm:gap-[10px]">
            <button
              class="flex w-full items-center justify-center gap-2 rounded-[10px] border-none bg-[#252525] px-[1.4em] py-[0.7em] text-[0.85em] font-bold text-white transition duration-300 sm:w-auto"
              type="button"
              on:click={closeValidateConfirm}
              disabled={updatingValidation}
            >
              Annulla
            </button>
            <button
              class="flex w-full items-center justify-center gap-2 rounded-[10px] border-none bg-[#00ff75] px-[1.4em] py-[0.7em] text-[0.85em] font-bold text-[#171717] transition duration-300 hover:enabled:bg-white hover:enabled:shadow-[0_0_15px_rgba(0,255,117,0.6)] sm:w-auto"
              type="button"
              on:click={confirmValidateMonth}
              disabled={updatingValidation}
            >
              Conferma
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
