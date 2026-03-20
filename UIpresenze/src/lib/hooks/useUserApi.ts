import type { User } from '$lib/services/users';
import { fetchUsers, fetchProfiles } from '$lib/services/users';
import { auth } from '$lib/stores/auth';
import { get } from 'svelte/store';
import { timeEntryUser } from '$lib/stores/timeEntryUser';

async function waitForToken(timeoutMs = 3000) {
  const existing = get(auth).token;
  if (existing) return existing;
  return new Promise<string | null>((resolve) => {
    const timer = setTimeout(() => {
      unsub();
      resolve(null);
    }, timeoutMs);
    const unsub = auth.subscribe((value) => {
      if (value.token) {
        clearTimeout(timer);
        unsub();
        resolve(value.token);
      }
    });
  });
}


export async function useUsersApi(): Promise<{
  users: User[];
  error: string | null;
}> {
  try {
    const token = await waitForToken();
    if (!token) {
      throw new Error('Token non disponibile');
    }
    const users = await fetchUsers();
    return { users, error: null };
  } catch (e) {
    return {
      users: [],
      error: (e as Error).message ?? 'Errore caricando utenti'
    };
  }
}


export async function useOneUserApi(uId?: number){
  let users: User[] = [];
  let error: string | null = null;
  if (!uId) {
    return;
  }
  try {
    const result = await useUsersApi();
    const payload = result.users as unknown;
    const list = Array.isArray(payload)
      ? payload
      : Array.isArray((payload as any)?.results)
        ? (payload as any).results
        : Array.isArray((payload as any)?.users)
          ? (payload as any).users
          : [];
    users = list;
    error = result.error;
  } catch (e) {
    error = 'Impossibile caricare gli utenti';
    console.error(e);
  }
  if (error) return;
  const user = users.find((u) => u.id === uId);
  if (user) {
    timeEntryUser.setUser(user);
  }
  // return user
}


export async function useUserProfile(): Promise<{
  users: User[];
  error: string | null;
}> {
  try {
    const token = await waitForToken();
    if (!token) {
      throw new Error('Token non disponibile');
    }
    const data = (await fetchProfiles()) as unknown;
    const users = Array.isArray(data)
      ? data
      : Array.isArray((data as any)?.users)
        ? (data as any).users
        : Array.isArray((data as any)?.results)
          ? (data as any).results
          : [];
    return { users, error: null };
  } catch (e) {
    return {
      users: [],
      error: (e as Error).message ?? 'Errore caricando profili'
    };
  }
}
