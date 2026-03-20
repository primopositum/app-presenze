import { apiBase, getAuthToken } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';
import { timeEntryUser } from '$lib/stores/timeEntryUser';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers(opts.headers || {});
  if (opts.json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getAuthToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const res = await fetch(url, {
    ...opts,
    headers,
    body: opts.json !== undefined ? JSON.stringify(opts.json) : opts.body
  });
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const message = (isJson && (data?.error || data?.detail)) || res.statusText;
    throw new Error(message || 'Request failed');
  }
  return data as any;
}
export type DecimalString = `${number}` | string; 


export type Saldo = {
  data: string;
  valore_saldo_sospeso: DecimalString;   
  valore_saldo_validato: DecimalString;
};


export type OreSett = [
  DecimalString, // lun
  DecimalString, // mar
  DecimalString, // mer
  DecimalString, // gio
  DecimalString  // ven
];
export type Contratto = {
  data_ass: string;             
  data_fine: string | null;      
  is_active: boolean;
  tipologia: string;             
  ore_sett: OreSett;
};


export type User = {
  id: number;
  nome: string;
  cognome?: string;
  email?: string;
  is_superuser?: boolean;
  saldo: Saldo;
  contratti: Contratto[]
};

export type PassChanger = {
  old_password: string,
  new_password: string,
}

export function fetchUsers(): Promise<User[]> {
  return request('/users/');
}

export function fetchProfiles(): Promise<User[]> {
  return request('/profile/');
}

function pickProfileUser(payload: unknown): User | null {
  if (!payload) return null;
  if (Array.isArray(payload)) return (payload[0] as User) ?? null;
  return payload as User;
}

export async function refreshProfileUser() {
  const profile = await fetchProfiles();
  const user = pickProfileUser(profile);
  if (!user?.id) return null;

  const authState = get(auth);
  if (authState?.user?.id === user.id) {
    auth.setUser(user);
  }

  const teUser = get(timeEntryUser).user;
  if (teUser?.id === user.id) {
    timeEntryUser.setUser(user);
  }

  return user;
}

export function changePassword(entry: PassChanger) {
  return request('/change-password/', { method: 'POST', json: entry });
}

// Backwards compatibility: keep the old name if it is used elsewhere.
export const createTimeEntry = changePassword;
