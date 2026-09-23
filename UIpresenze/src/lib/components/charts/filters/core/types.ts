/**
 * Forma dei filtri delle schermate del cubo.
 *
 * Le definizioni vivono nel `filters.json` della cartella di ogni schermata: il
 * pannello le disegna senza sapere niente del dominio, la schermata legge i
 * valori per id e decide lei come applicarli.
 */

export type FilterOption = { value: string; label: string; hint?: string };

/**
 * Sorgenti delle opzioni calcolate sui dati caricati: i progetti, le persone,
 * i clienti non si possono scrivere in un JSON.
 */
export type FilterOptionSource =
  | 'projects'
  | 'authors'
  | 'issueTypes'
  | 'statuses'
  | 'clients'
  | 'contracts'
  | 'issues'
  | 'cmIssues';

type FilterBase = {
  id: string;
  label: string;
  /** Riga di aiuto sotto al controllo: come si legge il filtro. */
  help?: string;
  /** Filtro tecnico: nascosto finche' non si attiva la vista avanzata. */
  technical?: boolean;
};

export type MultiselectFilter = FilterBase & {
  type: 'multiselect';
  options?: FilterOption[];
  source?: FilterOptionSource;
  /** Lista vuota = nessun filtro. */
  default?: string[];
};

/** Una sola voce, scelta da un elenco con ricerca. Stringa vuota = nessuna scelta. */
export type SelectFilter = FilterBase & {
  type: 'select';
  options?: FilterOption[];
  source?: FilterOptionSource;
  placeholder?: string;
};

export type SegmentedFilter = FilterBase & {
  type: 'segmented';
  options: FilterOption[];
  default?: string;
};

export type RangeFilter = FilterBase & {
  type: 'range';
  unit?: string;
  step?: number;
  min?: number;
  max?: number;
};

export type NumberFilter = FilterBase & {
  type: 'number';
  unit?: string;
  step?: number;
  min?: number;
  max?: number;
  placeholder?: string;
  /** null = usa il valore di default della schermata. */
  default?: number | null;
};

export type TextFilter = FilterBase & {
  type: 'text' | 'regex';
  placeholder?: string;
  default?: string;
};

export type DateFilter = FilterBase & { type: 'date' };
export type DateRangeFilter = FilterBase & { type: 'dateRange' };

export type ToggleFilter = FilterBase & { type: 'toggle'; default?: boolean };

export type FilterDef =
  | MultiselectFilter
  | SelectFilter
  | SegmentedFilter
  | RangeFilter
  | NumberFilter
  | TextFilter
  | DateFilter
  | DateRangeFilter
  | ToggleFilter;

export type FilterGroup = {
  id: string;
  label: string;
  description?: string;
  filters: FilterDef[];
};

export type FilterScreen = {
  id: string;
  title: string;
  description?: string;
  groups: FilterGroup[];
};

export type NumberRange = { min: number | null; max: number | null };
export type DateSpan = { from: string; to: string };

export type FilterValue = string[] | string | number | boolean | null | NumberRange | DateSpan;
export type FilterValues = Record<string, FilterValue>;
