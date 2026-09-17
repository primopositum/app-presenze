import { getContext, setContext } from 'svelte';
import { writable, type Writable } from 'svelte/store';

export type TimeEntryFormMode = 'create' | 'update';

export type TimeEntryFormOpenArgs = {
  mode?: TimeEntryFormMode;
  teId?: number;
  date: string;             // YYYY-MM-DD
  utenteId?: number | null;
  type: number;            
  oreTot: number;
  note?: string;
  forbiddenTypes?: number[];
};

export type TimeEntryFormState = {
  open: boolean;
  args: TimeEntryFormOpenArgs | null;
};

export type TimeEntryFormContext = {
  state: Writable<TimeEntryFormState>;
  openForm: (args: TimeEntryFormOpenArgs) => void;
  closeForm: () => void;
};

const KEY = Symbol('timeEntryForm');

export function initTimeEntryFormContext(): TimeEntryFormContext {
  const state = writable<TimeEntryFormState>({
    open: false,
    args: null
  });

  function openForm(args: TimeEntryFormOpenArgs) {
    const normalized: TimeEntryFormOpenArgs = {
      mode: args.mode ?? 'create',
      ...args
    };

    if (normalized.mode === 'update' && (normalized.teId === undefined || normalized.teId === null)) {
      throw new Error('openForm: mode="update" richiede teId');
    }

    state.set({ open: true, args: normalized });
  }

  function closeForm() {
    state.set({ open: false, args: null });
  }

  const ctx: TimeEntryFormContext = { state, openForm, closeForm };
  setContext(KEY, ctx);
  return ctx;
}

export function useTimeEntryFormContext(): TimeEntryFormContext {
  const ctx = getContext<TimeEntryFormContext>(KEY);
  if (!ctx) {
    throw new Error('timeEntryForm context not found. Wrap your page in <TimeEntryFormProvider>.');
  }
  return ctx;
}
