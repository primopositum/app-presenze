import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const message = (isJson && (data?.error || data?.detail || data?.errors)) || res.statusText;
    throw new Error(message || 'Request failed');
  }
  return data as any;
}

export type SaldoRecord = {
  periodo: string;
  saldo: number;
  aggiornatoIl?: string;
  validazioni?: number;
};

export type Saldo = {
  utente_id?: number;
  saldo: SaldoRecord[];
};

export type SaldoPatchPayload = {
  periodo: string;
  saldo: number;
};

export function getSaldoByUserId(userId: number): Promise<Saldo> {
  return request(`/saldo/${userId}/`) as Promise<Saldo>;
}

export function patchSaldoByUserId(userId: number, payload: SaldoPatchPayload): Promise<Saldo> {
  return request(`/saldo/${userId}/`, { method: 'PATCH', json: payload }) as Promise<Saldo>;
}
