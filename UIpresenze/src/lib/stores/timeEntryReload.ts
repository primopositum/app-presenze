import { writable } from 'svelte/store';

function createTimeEntryReload() {
  const { subscribe, update } = writable(0);

  function bump() {
    update((n) => n + 1);
  }

  return { subscribe, bump };
}

export const timeEntryReload = createTimeEntryReload();
