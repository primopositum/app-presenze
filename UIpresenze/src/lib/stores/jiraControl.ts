import { get, writable } from 'svelte/store';
import { jiraFiltersGet } from '$lib/services/jira';

type JiraControlState = {
  enabled: boolean;
  loaded: boolean;
  loading: boolean;
  error: string;
};

const initialState: JiraControlState = {
  enabled: true,
  loaded: false,
  loading: false,
  error: '',
};

const { subscribe, set } = writable<JiraControlState>(initialState);

let inFlight: Promise<boolean> | null = null;

export const jiraControl = {
  subscribe,
};

export function resetJiraControl() {
  inFlight = null;
  set(initialState);
}

export async function ensureJiraControlLoaded(force = false): Promise<boolean> {
  const current = get(jiraControl);
  if (!force && current.loaded) {
    return current.enabled;
  }
  if (!force && inFlight) {
    return inFlight;
  }

  set({
    enabled: current.enabled,
    loaded: current.loaded,
    loading: true,
    error: '',
  });

  inFlight = (async () => {
    try {
      const payload = await jiraFiltersGet();
      const enabled = payload?.JiraControl !== false;
      set({
        enabled,
        loaded: true,
        loading: false,
        error: '',
      });
      return enabled;
    } catch (err) {
      const fallbackEnabled = current.enabled;
      set({
        enabled: fallbackEnabled,
        loaded: true,
        loading: false,
        error: err instanceof Error ? err.message : 'Errore caricamento JiraControl',
      });
      return fallbackEnabled;
    } finally {
      inFlight = null;
    }
  })();

  return inFlight;
}

export function isJiraRoute(pathname: string) {
  const path = String(pathname || '');
  return path.startsWith('/JiraBoard') || path.startsWith('/JiraHistory');
}
