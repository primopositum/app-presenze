import { apiBase, authFetch } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';
import { timeEntryUser } from '$lib/stores/timeEntryUser';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

function extractErrorMessage(data: any): string | null {
  if (!data) return null;
  if (typeof data === 'string') return data;
  if (typeof data.error === 'string') return data.error;
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data.errors === 'string') return data.errors;

  const walk = (value: any): string | null => {
    if (value == null) return null;
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      for (const item of value) {
        const msg = walk(item);
        if (msg) return msg;
      }
      return null;
    }
    if (typeof value === 'object') {
      for (const key of Object.keys(value)) {
        const msg = walk(value[key]);
        if (msg) return msg;
      }
      return null;
    }
    return null;
  };

  return walk(data.errors) || walk(data);
}

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const message = isJson ? extractErrorMessage(data) : null;
    throw new Error(message || 'Request failed');
  }
  return data as any;
}
export type DecimalString = `${number}` | string; 


export type Saldo = {
  id?: number;
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
  id?: number;
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
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  saldo: Saldo;
  contratti: Contratto[]
};

export type SaldoUpdatePayload = Partial<Pick<Saldo, 'valore_saldo_validato' | 'valore_saldo_sospeso'>>;
export type ContrattoUpdatePayload = Partial<
  Pick<Contratto, 'data_ass' | 'data_fine' | 'is_active' | 'tipologia' | 'ore_sett'>
>;

export type UpdateAccountPayload = Partial<
  Pick<User, 'email' | 'nome' | 'cognome' | 'is_active'>
> & {
  id?: number;
  user_id?: number;
  dati_anagrafici?: Record<string, unknown> | string | null;
  saldo?: SaldoUpdatePayload;
  contratti?: ContrattoUpdatePayload | ContrattoUpdatePayload[];
};

export type PassChanger = {
  old_password: string,
  new_password: string,
}

export type DeleteAccountResponse = {
  message: string;
  deleted_user_id: number;
};

export function fetchUsers(): Promise<User[]> {
  return request('/users/');
}

export function fetchProfiles(): Promise<User[]> {
  return request('/profile/');
}

export function normalizeUsersPayload(payload: unknown): User[] {
  if (Array.isArray(payload)) return payload as User[];
  if (!payload || typeof payload !== 'object') return [];

  const data = payload as Record<string, unknown>;
  if (Array.isArray(data.results)) return data.results as User[];
  if (Array.isArray(data.users)) return data.users as User[];
  if (typeof data.id === 'number') return [data as unknown as User];
  return [];
}

function pickProfileUser(payload: unknown): User | null {
  return normalizeUsersPayload(payload)[0] ?? null;
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

export function updateAccount(entry: UpdateAccountPayload) {
  const targetFromPayload = entry.id ?? entry.user_id;
  const parsedTargetUserId = Number(targetFromPayload);
  const hasTargetUserId = Number.isFinite(parsedTargetUserId);
  const path = hasTargetUserId
    ? `/profile/?id=${parsedTargetUserId}`
    : '/profile/';

  const payload: UpdateAccountPayload = hasTargetUserId
    ? { ...entry, id: parsedTargetUserId, user_id: parsedTargetUserId }
    : { ...entry };

  return request(path, { method: 'PUT', json: payload }) as Promise<User>;
}

export function deleteAccountById(userId: number) {
  const parsedUserId = Number(userId);
  if (!Number.isFinite(parsedUserId)) {
    throw new Error('ID utente non valido');
  }
  return request(`/delete-account/?id=${parsedUserId}`, { method: 'DELETE' }) as Promise<DeleteAccountResponse>;
}

// Backwards compatibility: keep the old name if it is used elsewhere.
export const createTimeEntry = changePassword;
