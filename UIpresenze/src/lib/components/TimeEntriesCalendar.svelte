<script context="module" lang="ts">
  export type TimeEntryData = {
    id: number;
    date: string;
    type: number;
    type_display?: string;
    ore_tot: number;
    validation_level: number;
    note?: string | null;
  };

  export type DayHours = {
    date: string;
    hours: number;
    validation_level?: number;
    entries?: TimeEntryData[];
  };
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let year: number;
  export let month: number; // 1-12
  export let dayHours: DayHours[] = [];
  export let maxVisibleEntries: number = 2; // Numero massimo di entries da mostrare

  const dispatch = createEventDispatcher<{
    selectDay: { date: string; locked: boolean };
  }>();

  $: first = new Date(year, month - 1, 1);
  $: firstWeekday = (first.getDay() + 6) % 7; // Monday = 0
  $: last = new Date(year, month, 0);
  $: daysInMonth = last.getDate();

  // ore per data
  $: byDate = dayHours.reduce<Record<string, number>>((acc, entry) => {
    acc[entry.date] = entry.hours;
    return acc;
  }, {});

  // validation per data
  $: byValidation = dayHours.reduce<Record<string, number>>((acc, entry) => {
    if (entry.validation_level !== undefined && entry.validation_level !== null) {
      acc[entry.date] = entry.validation_level;
    }
    return acc;
  }, {});

  // entries per data
  $: byEntries = dayHours.reduce<Record<string, TimeEntryData[]>>((acc, entry) => {
    if (entry.entries && entry.entries.length > 0) {
      acc[entry.date] = entry.entries;
    }
    return acc;
  }, {});

  function iso(y: number, m: number, d: number) {
    const mm = String(m).padStart(2, '0');
    const dd = String(d).padStart(2, '0');
    return `${y}-${mm}-${dd}`;
  }

  function formatHours(hours: number) {
    return `${hours}h`;
  }

  function isWeekend(y: number, m: number, d: number) {
    const date = new Date(y, m - 1, d);
    const day = date.getDay();
    return day === 0 || day === 6;
  }

  function isLockedByValidation(dateStr: string) {
    return byValidation[dateStr] === 2;
  }

  function validationBg(level: number | undefined) {
    if (level === 0) return 'bg-red-100';
    if (level === 1) return 'bg-yellow-100';
    if (level === 2) return 'bg-green-100';
    return '';
  }

  // Colori per tipo di entry
  function getEntryTypeColor(type: number) {
    const colors: Record<number, string> = {
      1: 'bg-blue-500 text-white',           // Lavoro ordinario
      2: 'bg-yellow-500 text-white',         // Ferie
      3: 'bg-green-500 text-white',          // Versamento banca ore
      4: 'bg-purple-500 text-white',         // Prelievo banca ore
      5: 'bg-red-500 text-white',            // Malattia
      6: 'bg-orange-500 text-white',         // Permesso ordinario
      7: 'bg-orange-500 text-white',         // Permesso studio
      8: 'bg-orange-500 text-white',         // Permesso 104
      9: 'bg-teal-500 text-white',           // Permesso ex festività
      10: 'bg-orange-500 text-white',        // Permesso ROL
      11: 'bg-violet-500 text-white',        // Congedo mat/pat
      12: 'bg-gray-600 text-white',          // Sciopero
      13: 'bg-emerald-500 text-white',       // Festività
    };
    return colors[type] || 'bg-gray-400 text-white';
  }

  // Label abbreviate per tipo
  function getEntryTypeShort(type: number) {
    const labels: Record<number, string> = {
      1: 'LAV',
      2: 'FER',
      3: 'B+',
      4: 'B-',
      5: 'MAL',
      6: 'PER',
      7: 'STU',
      8: '104',
      9: 'EXF',
      10: 'ROL',
      11: 'MAT',
      12: 'SCI',
      13: 'FES',
    };
    return labels[type] || 'N/A';
  }

  function handleDay(day: number) {
    const isoDate = iso(year, month, day);
    const locked = isLockedByValidation(isoDate);

    dispatch('selectDay', { date: isoDate, locked });
  }
</script>

<div class="w-full">
  <div class="grid grid-cols-7 mb-1">
    {#each ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'] as wd}
      <div class="text-center font-semibold text-[10px] sm:text-sm py-1 text-gray-600">
        {wd}
      </div>
    {/each}
  </div>

  <div class="grid grid-cols-7 gap-1" aria-label="Calendario ore lavorate">
    {#each Array(firstWeekday) as _}
      <div class="min-h-20 border border-dashed border-gray-200 rounded-md"></div>
    {/each}

    {#each Array(daysInMonth) as _, idx}
      {@const day = idx + 1}
      {@const dstr = iso(year, month, day)}
      {@const today = new Date()}
      {@const isToday = today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === day}
      {@const hours = byDate[dstr]}
      {@const entries = byEntries[dstr] || []}
      {@const hasNotes = entries.some((entry) => !!entry.note?.trim())}
      {@const visibleEntries = entries.slice(0, maxVisibleEntries)}
      {@const hiddenCount = Math.max(0, entries.length - maxVisibleEntries)}
      {@const weekend = isWeekend(year, month, day)}
      {@const locked = isLockedByValidation(dstr)}
      {@const isDisabled = locked}
      {@const vLevel = byValidation[dstr]}
      {@const vBg = validationBg(vLevel)}
      {@const weekendEmpty = weekend && hours === undefined}

      <div
        role="button"
        tabindex={isDisabled ? -1 : 0}
        aria-disabled={isDisabled}
        class={`flex flex-col items-center border-2 gap-0.5 sm:gap-1 h-20 sm:h-24 overflow-hidden rounded-md p-1 sm:p-1.5
          relative
          transition-colors
          ${isDisabled ? `${vBg || 'bg-gray-50'} opacity-60` : `cursor-pointer ${vBg || (weekendEmpty ? 'bg-blue-100' : weekend ? 'bg-gray-50' : 'bg-gray-100')} hover:opacity-90`}
          ${isToday ? 'outline outline-2 outline-green-500 border-none' : 'border-gray-400'}
        `}
        on:click={() => handleDay(day)}
        on:keydown={(e) => {
          if (isDisabled) return;
          if (e.key === 'Enter' || e.key === ' ') handleDay(day);
        }}
      >
        {#if hasNotes}
          <span
            class="absolute top-1 right-1 w-2 h-2 rounded-full bg-orange-500"
            title="Presente almeno una nota in questo giorno"
            aria-label="Giorno con nota"
          ></span>
        {/if}

        <!-- Numero giorno -->
        <div class="text-[10px] sm:text-xs font-medium text-gray-500 mb-0.5">
          {String(day).padStart(2, '0')}
        </div>

        {#if entries.length > 0}
          <!-- Container entries con altezza fissa -->
          <div class="flex flex-col gap-0.5 w-full flex-shrink-0">
            {#each visibleEntries as entry}
              <div 
                class={`text-[8px] sm:text-[9px] font-semibold px-1 py-0.5 rounded flex justify-between items-center ${getEntryTypeColor(entry.type)}`}
                title={entry.type_display || `Tipo ${entry.type}`}
              >
                <span class="truncate">{getEntryTypeShort(entry.type)}</span>
                <span class="ml-1">{formatHours(entry.ore_tot)}</span>
              </div>
            {/each}
            
            {#if hiddenCount > 0}
              <div 
                class="text-[7px] sm:text-[8px] font-bold px-1 py-0.5 rounded bg-gray-400 text-white text-center"
                title={`Altre ${hiddenCount} voci - clicca per vedere tutto`}
              >
                +{hiddenCount}
              </div>
            {/if}
          </div>
          
          <!-- Totale -->
          <div class="text-[10px] sm:text-xs font-bold text-gray-900 border-t border-gray-300 pt-0.5 w-full text-center mt-auto">
            {formatHours(hours)}
          </div>
        {:else if hours !== undefined}
          <!-- Fallback: mostra solo il totale se non ci sono entries dettagliate -->
          <div class="text-base sm:text-lg font-bold text-gray-900 my-auto">
            {formatHours(hours)}
          </div>
        {:else}
          <div class="text-base sm:text-lg font-normal text-gray-400 my-auto">-</div>
        {/if}

        {#if locked}
          <div class="text-[7px] sm:text-[8px] font-semibold text-gray-500 mt-auto">
            VALIDATO
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>
