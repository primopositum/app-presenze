import { apiBase, getAuthToken } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

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

export type TimeEntry = {
  id: number;
  utente: string;
  type: number;
  ore_tot: string;
  data: string; // YYYY-MM-DD
  validation_level: number;
  note?: string | null;
};

export type TimeEntryCreate = {
  utente_id: number;
  data: string; // YYYY-MM-DD
  type: number;
  ore_tot: number | string;
  validation_level?: number;
  note?: string;
};
export type TimeEntryUpdate = {
  utente_id: number;
  data: string; // YYYY-MM-DD
  type: number;
  ore_tot: number | string;
  note?: string;
};
export type TimeEntryRangeOverrideCreate = {
  utente_id: number;
  dataS: string; // YYYY-MM-DD
  dataE: string; // YYYY-MM-DD
  type: number;
};
export type BulkValidationUpdate = {
  u_id?: number;
  data: string; // YYYY-MM-DD
};
/**
 * Regola sessione:
 * - superuser -> NON passa u_id
 * - non superuser -> passa u_id = $auth.user.id
 * - se params.utenteId è passato esplicitamente, lo rispetta (utile per superuser che filtra)
 */
function resolveUId(explicitUId?: number) {
  if (explicitUId !== undefined && explicitUId !== null) return explicitUId;

  const a = get(auth);
  const isSuperuser = !!a?.user?.is_superuser;
  if (isSuperuser) return undefined;

  const id = a?.user?.id;
  return id ?? undefined;
}

export function getTimeEntriesFromMonth(params: {
  date: Date;
  utenteId?: number; // opzionale: se superuser vuole filtrare un utente specifico
}) {
  const qs = new URLSearchParams();

  const y = params.date.getFullYear();
  const m = String(params.date.getMonth() + 1).padStart(2, '0');
  const d = String(params.date.getDate()).padStart(2, '0');
  qs.set('data', `${y}-${m}-${d}`);

  const uId = resolveUId(params.utenteId);
  if (uId !== undefined) {
    qs.set('u_id', String(uId));
  }

  return request(`/time-entries/from-month/?${qs.toString()}`);
}

export function createTimeEntry(entry: TimeEntryCreate) {
  return request('/time-entries/', { method: 'POST', json: entry });
}

export function updateTimeEntry(teId: number, entry: Partial<TimeEntryCreate>) {
  return request(`/time-entries/${teId}/`, { method: 'PUT', json: entry });
}

export function deleteTimeEntry(teId: number) {
  return request(`/time-entries/${teId}/`, { method: 'DELETE' });
}

export function createTimeEntryRangeOverride(entry: TimeEntryRangeOverrideCreate) {
  return request('/time-entries/range-override/', { method: 'POST', json: entry });
}


export async function getMeseScorsoPdf(params: { u_id?: number; date?: string; note?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.u_id !== undefined) qs.set('u_id', String(params.u_id));
  if (params.date) qs.set('data', params.date);
  if (params.note !== undefined) qs.set('note', params.note);
  const url = `${BASE}/pdf/${qs.toString() ? `?${qs.toString()}` : ''}`;
  const headers = new Headers();
  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const message = res.statusText || 'Request failed';
    throw new Error(message);
  }
  return res.blob(); 
}


export function updateTimeEntryValidation(entry: BulkValidationUpdate) {
    return request(`/time-entries/bulk-validate-month/`, { method: 'PATCH', json : entry});
}
