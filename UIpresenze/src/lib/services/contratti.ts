import { apiBase, authFetch } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';
// import { Contratto } from './users';
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
 * - non superuser -> u_id = $auth.user.id (ma attenzione: i contratti sono SOLO superuser lato backend)
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
//   const uId = resolveUId(params.u_id);
//   if (uId === undefined) {
//     // In pratica: se sei superuser devi passare u_id esplicitamente.
//     throw new Error('u_id è obbligatorio per aggiornare un contratto');
//   }
//   const payload: ContrattoUpdateOre = { ore_sett: params.ore_sett };
  const payload: ContrattoUpdateOre = { ore_sett };
  return request(`/contratti/${u_id}/ore/`, { method: 'PATCH', json: payload });
}

/**
 * POST crea NUOVO contratto per utente (u_id nel path).
 * Backend: disattiva eventuale contratto attivo e crea nuovo is_active=true
 * Solo superuser.
 *
 * Endpoint atteso: POST /contratti/<u_id>/
 * Body: { data_ass, data_fine?, tipologia, ore_sett }
 */
export function createContratto(u_id: number, contratto: ContrattoCreate ) {
  return request(`/contratti/${u_id}/`, { method: 'POST', json: contratto });
}
