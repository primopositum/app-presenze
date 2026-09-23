/**
 * Valori dei filtri, per schermata.
 *
 * Come `chartsData` vive solo in memoria: al reload i grafici ripartono senza
 * filtri, cosi' nessuno si ritrova una vista ridotta senza sapere perche'.
 */
import { writable } from 'svelte/store';
import type {
  DateSpan,
  FilterDef,
  FilterScreen,
  FilterValue,
  FilterValues,
  NumberRange
} from './types';

const store = writable<Record<string, FilterValues>>({});

export const chartFilters = { subscribe: store.subscribe };

export function defaultValue(def: FilterDef): FilterValue {
  switch (def.type) {
    case 'multiselect':
      return [...(def.default ?? [])];
    case 'select':
      return '';
    case 'segmented':
      return def.default ?? def.options[0]?.value ?? '';
    case 'range':
      return { min: null, max: null };
    case 'number':
      return def.default ?? null;
    case 'text':
    case 'regex':
      return def.default ?? '';
    case 'date':
      return '';
    case 'dateRange':
      return { from: '', to: '' };
    case 'toggle':
      return def.default ?? false;
  }
}

export function screenFilters(screen: FilterScreen): FilterDef[] {
  return screen.groups.flatMap((group) => group.filters);
}

export function screenDefaults(screen: FilterScreen): FilterValues {
  return Object.fromEntries(screenFilters(screen).map((def) => [def.id, defaultValue(def)]));
}

/** Valori salvati sopra i default: un filtro aggiunto al JSON parte sempre dal suo default. */
export function resolveValues(screen: FilterScreen, stored?: FilterValues): FilterValues {
  return { ...screenDefaults(screen), ...(stored ?? {}) };
}

export function isDefault(def: FilterDef, value: FilterValue | undefined) {
  if (value === undefined) return true;
  const fallback = defaultValue(def);
  if (Array.isArray(value) && Array.isArray(fallback)) {
    return value.length === fallback.length && value.every((item) => fallback.includes(item));
  }
  return JSON.stringify(value) === JSON.stringify(fallback);
}

export function activeCount(screen: FilterScreen, values: FilterValues | undefined) {
  if (!values) return 0;
  return screenFilters(screen).filter((def) => !isDefault(def, values[def.id])).length;
}

export function setFilterValue(screenId: string, id: string, value: FilterValue) {
  store.update((state) => ({ ...state, [screenId]: { ...(state[screenId] ?? {}), [id]: value } }));
}

export function resetFilter(screen: FilterScreen, id: string) {
  const def = screenFilters(screen).find((item) => item.id === id);
  if (def) setFilterValue(screen.id, id, defaultValue(def));
}

export function resetFilters(screenId: string) {
  store.update((state) => {
    const next = { ...state };
    delete next[screenId];
    return next;
  });
}

/* -------------------------------------------------------------------------- */
/* Letture tipizzate: la schermata sa che tipo aspettarsi per ciascun id       */
/* -------------------------------------------------------------------------- */

export function readList(values: FilterValues, id: string): string[] {
  const value = values[id];
  return Array.isArray(value) ? value : [];
}

export function readText(values: FilterValues, id: string): string {
  const value = values[id];
  return typeof value === 'string' ? value : '';
}

export function readNumber(values: FilterValues, id: string): number | null {
  const value = values[id];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function readBool(values: FilterValues, id: string): boolean {
  return values[id] === true;
}

export function readRange(values: FilterValues, id: string): NumberRange {
  const value = values[id] as Partial<NumberRange> | undefined;
  const pick = (item: unknown) =>
    typeof item === 'number' && Number.isFinite(item) ? item : null;
  return { min: pick(value?.min), max: pick(value?.max) };
}

export function readDates(values: FilterValues, id: string): DateSpan {
  const value = values[id] as Partial<DateSpan> | undefined;
  return { from: String(value?.from ?? ''), to: String(value?.to ?? '') };
}
