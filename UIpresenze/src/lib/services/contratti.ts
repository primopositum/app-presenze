import { apiBase, authFetch } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

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

/**
 * Regola sessione:
 * - superuser -> NON forza u_id
 * - non superuser -> u_id = $auth.user.id
 */
export function resolveUId(explicitUId?: number) {
  if (explicitUId !== undefined && explicitUId !== null) return explicitUId;

  const a = get(auth);
  const isSuperuser = !!a?.user?.is_superuser;
  if (isSuperuser) return undefined;

  const id = a?.user?.id;
  return id ?? undefined;
}

export type ContrattoCreate = {
  data_ass: string; // YYYY-MM-DD
  data_fine?: string | null;
  tipologia: string;
  ore_sett: Array<number | string>; // len 5
};

export type ContrattoUpdateOre = {
  ore_sett: Array<number | string>; // len 5
};

export function updateContrattoOre(u_id: number, ore_sett: Array<number | string>) {
  const payload = {
    id: u_id,
    user_id: u_id,
    contratti: [{ ore_sett }]
  };
  // Backend reale: aggiornamento contratto via profilo.
  return request(`/profile/?id=${u_id}`, { method: 'PUT', json: payload });
}

/**
 * Crea/aggiorna contratto utente usando l'endpoint profilo.
 * Lato backend: se esiste un contratto attivo viene aggiornato, altrimenti viene creato.
 */
export function createContratto(u_id: number, contratto: ContrattoCreate) {
  const payload = {
    id: u_id,
    user_id: u_id,
    contratti: [contratto]
  };
  return request(`/profile/?id=${u_id}`, { method: 'PUT', json: payload });
}
