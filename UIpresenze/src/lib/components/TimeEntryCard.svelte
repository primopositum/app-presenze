<script context="module" lang="ts">
  export type TimeEntry = {
    id: number;
    utente: string;
    type: number;
    ore_tot: string;           // es "8.00"
    data: string;              // YYYY-MM-DD
    validation_level: number;  // 0/1/2
    note?: string | null;
    data_creaz?: string;
    data_upd?: string;
  };
  
</script>

<script lang="ts">
  import { FontAwesomeIcon } from '@fortawesome/svelte-fontawesome';
  import { faLock, faPenToSquare, faTrash } from '@fortawesome/free-solid-svg-icons';
  import { useTimeEntryFormContext } from '$lib/context/timeEntryForm';
  import { timeEntryUser } from '$lib/stores/timeEntryUser';
  export let timeEntries: TimeEntry[] = [];
  export let dateParam: string;          
  import { useDeleteHours } from '$lib/hooks/useSubmitHours';
  import { timeEntryReload } from '$lib/stores/timeEntryReload';
	import TimeEntriesCalendar from './TimeEntriesCalendar.svelte';

  // default per il "+"
  export let defaultType = 1;
  export let defaultValidationLevel = 0;
  export let defaultHours = 8;
  
  const { openForm } = useTimeEntryFormContext();
  function parseYmd(dateStr: string) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return { y, m, d };
  }

  function dayLabel(dateStr: string) {
    const { y, m, d } = parseYmd(dateStr);
    return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
  }

  function weekdayShort(dateStr: string) {
    const { y, m, d } = parseYmd(dateStr);
    const dt = new Date(y, m - 1, d);
    return dt.toLocaleDateString('it-IT', { weekday: 'short' });
  }

  function vBadge(level: number) {
    if (level === 2) return { text: 'VALIDATO', cls: 'bg-green-100 text-green-800' };
    if (level === 1) return { text: 'INVIATO', cls: 'bg-yellow-100 text-yellow-800' };
    return { text: 'BOZZA', cls: 'bg-yellow-100 text-yellow-800' };
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

  function toHoursNumber(h: string) {
    const n = Number(h);
    return Number.isFinite(n) ? n : 0;
  }

  // ---------- grouping ----------
  $: grouped = timeEntries.reduce<Record<string, TimeEntry[]>>((acc, te) => {
    const key = te.data || (te.data_creaz ? te.data_creaz.slice(0, 10) : 'Senza data');
    (acc[key] ||= []).push(te);
    return acc;
  }, {});

  $: datesSorted = Object.keys(grouped)
    .filter((d) => d !== 'Senza data')
    .sort(); // YYYY-MM-DD si ordina bene

  // ---------- handlers ----------
  function handleAdd(dateStr: string) {
    openForm({
      mode: 'create',
      date: dateStr,
      utenteId: $timeEntryUser.user?.id ?? null,
      type: defaultType,
      oreTot: defaultHours
    });
  }
  function handleUpdate(te: TimeEntry) { 
    openForm({
      mode: 'update',
      date: te.data,
      utenteId: $timeEntryUser.user?.id ?? null,
      type: te.type,
      oreTot: Number(te.ore_tot),
      note: te.note ?? '',
      teId: te.id
    });
  }

  async function handleDelete(te: TimeEntry) {
    let loading = false;
    let error: string | null = null;
    //if (te.validation_level === 2) return; already 50k control on this
    try {
      loading = true;
      const deleteHours = useDeleteHours({ TimeEntryId: te.id });
      await deleteHours();
      timeEntryReload.bump();
    } catch (e: any) {
      error = e?.message || 'Errore cancellazione';
    } finally {
      loading = false;
    }
    timeEntryReload.bump();

  }
</script>
<div>
{#if datesSorted.length === 0}
      <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">

  <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <div class="flex flex-col">
              <div class="text-sm text-slate-500">{weekdayShort(dateParam)}</div>
              <div class="text-base sm:text-lg font-semibold text-slate-900">{dayLabel(dateParam)}</div>
            </div>

            <button
              type="button"
              class="w-8 h-8 sm:w-9 sm:h-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center text-base sm:text-lg"
              on:click={() => handleAdd(dateParam)}
              aria-label="Aggiungi time entry"
              title="Aggiungi"
            >
              +
            </button>
          </div>
        <div class="  bg-white p-4 text-sm text-slate-500">
    Nessun TimeEntry registrato per ora.
  </div>
</div>
{:else}
  <div class="space-y-4">
    {#each datesSorted as dateStr (dateStr)}
      <div class="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <div class="flex flex-col">
            <div class="text-sm text-slate-500">{weekdayShort(dateStr)}</div>
            <div class="text-base sm:text-lg font-semibold text-slate-900">{dayLabel(dateStr)}</div>
          </div>

          <button
            type="button"
            class="w-8 h-8 sm:w-9 sm:h-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center text-base sm:text-lg"
            on:click={() => handleAdd(dateStr)}
            aria-label="Aggiungi time entry"
            title="Aggiungi"
          >
            +
          </button>
        </div>

        <ul class="divide-y divide-slate-100">
          {#each grouped[dateStr] as te (te.id)}
            {@const badge = vBadge(te.validation_level)}
            {@const locked = te.validation_level === 2}

            <li>
              {#if locked}
                <div class="w-full px-4 py-3 flex items-center gap-3 bg-green-50">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold text-slate-900">{typeLabel(te.type)}  {te.ore_tot}h</span>

                      <span class={`text-[11px] px-2 py-0.5 rounded-full ${badge.cls}`}>
                        {badge.text}
                      </span>

                      <span class="text-xs text-slate-500">
                        <FontAwesomeIcon icon={faLock} class="text-sm text-slate-600" />
                      </span>
                    </div>

                    <div class="text-xs text-slate-500 mt-0.5">
                      {te.utente}
                    </div>
                  </div>
                </div>
              {:else}
                <div
                  role="button"
                  tabindex="0"
                  class="w-full px-4 py-3 hover:bg-slate-50 transition flex items-center gap-3 cursor-pointer"
                >
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold text-slate-900">{typeLabel(te.type)}  {te.ore_tot}h</span>

                      <span class={`text-[11px] px-2 py-0.5 rounded-full ${badge.cls}`}>
                        {badge.text}
                      </span>
                    </div>

                    <div class="text-xs text-slate-500 mt-0.5">
                      {te.utente} 
                    </div>
                  </div>
                  <button
                      type="button"
                      class="shrink-0 w-8 h-8 sm:w-9 sm:h-9 rounded-lg border border-slate-200 hover:bg-blue-50 hover:border-blue-200 flex items-center justify-center"
                      on:click|stopPropagation={() => handleUpdate(te)}
                      aria-label="Modifica time entry"
                      title="Modifica"
                    >
                      <FontAwesomeIcon icon={faPenToSquare} class="text-sm text-slate-600" />
                  </button>
                  <button
                    type="button"
                    class="shrink-0 w-8 h-8 sm:w-9 sm:h-9 rounded-lg border border-slate-200 hover:bg-red-50 hover:border-red-200 flex items-center justify-center"
                    on:click|stopPropagation={() => handleDelete(te)}
                    aria-label="Elimina time entry"
                    title="Elimina"
                  >
                    <FontAwesomeIcon icon={faTrash} class="text-sm text-slate-600" />
                  </button>
                </div>
              {/if}
            </li>
          {/each}
        </ul>
      </div>
    {/each}
  </div>
{/if}
</div>
