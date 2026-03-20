import { writable } from 'svelte/store';
import type { User } from '$lib/services/users';

type TimeEntryUserState = {
  user: User | null;
};

function createTimeEntryUser() {
  const { subscribe, set } = writable<TimeEntryUserState>({ user: null });
  const STORAGE_KEY = 'time_entry_user';
  let hydrated = false;

  if (typeof window !== 'undefined') {
    subscribe((value) => {
      if (!hydrated) return;
      try {
        if (value.user?.id) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(value.user));
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        // ignore storage errors
      }
    });
  }

  function init() {
    if (typeof window === 'undefined') return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw) as User | null;
      if (!data?.id) return;
      set({ user: data });
    } catch {
      // ignore invalid storage
    } finally {
      hydrated = true;
    }
  }

  function setUser(user: User | null) {
    set({ user });
  }

  return { subscribe, init, setUser };
}

export const timeEntryUser = createTimeEntryUser();
