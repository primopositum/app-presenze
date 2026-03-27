import { apiBase, authFetch } from '$lib/api';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

const BASE = apiBase();
const API_ROOT = BASE.replace(/\/api\/?$/, '');

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);

  let data: any = null;
  const contentType = res.headers.get('content-type');
  if (res.status !== 204 && res.status !== 205) {
    data = contentType?.includes('application/json') ? JSON.parse(await res.text() || 'null') : await res.text();
  }

  if (!res.ok) {
    const message = (data?.errors || data?.error || data?.detail) || res.statusText || 'Request failed';
    throw new Error(message);
  }

  return data;
}


export type ValidationLevel = 1 | 2;

export type Trasferta = {
  id: number;
  utente_id: number;
  utente_nome: string;
  utente_cognome: string;
  automobile?: number | string | null;
  A_ID?: number | null;
  data: string; // YYYY-MM-DD
  azienda: string;
  indirizzo: string | null;
  note: string | null;
  validation_level: ValidationLevel;
};

export type TrasfertaCreate = {
  utente_email?: string;
  data: string; // YYYY-MM-DD
  azienda: string;
};

export type TrasfertaUpdate = Partial<Trasferta> & {
  A_ID?: number | null;
  automobile?: number | string | null;
};

export type Spesa = {
  id: number;
  t_id: number;
  type: number;
  importo: string | number;
};

export type SpesaCreate = {
  type: number;
  importo: number | string;
};

export type SpesaUpdate = Partial<SpesaCreate>;

export type ScontrinoFile = {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: number;
  modified_at: number;
};

export type ScontrinoUploadResponse = {
  message: string;
  filename: string;
  path: string;
};

/**
 * Regola sessione:
 * - superuser -> NON passa uId
 * - non superuser -> passa uId = $auth.user.id
 * - se params.uId è passato esplicitamente, lo rispetta (utile per superuser che filtra)
 */
function resolveUId(explicitUId?: number) {
  if (explicitUId !== undefined && explicitUId !== null) return explicitUId;

  const a = get(auth);
  const isSuperuser = !!a?.user?.is_superuser;
  if (isSuperuser) return undefined;

  const id = a?.user?.id;
  return id ?? undefined;
}

export type TrasferteListParams = {
  limit?: number;
  date?: string; // YYYY-MM-DD
  uId?: number;
  validation?: number; // 1 | 2
  azienda?: string;
};

export function getTrasferte(params: TrasferteListParams = {}) {
  const qs = new URLSearchParams();

  if (params.limit !== undefined) qs.set('limit', String(params.limit));
  if (params.date) qs.set('date', params.date);
  if (params.validation !== undefined) qs.set('validation', String(params.validation));
  if (params.azienda) qs.set('azienda', params.azienda);

  const uId = resolveUId(params.uId);
  if (uId !== undefined) qs.set('uId', String(uId));

  const tail = qs.toString();
  return request(`/trasferte/${tail ? `?${tail}` : ''}`) as Promise<Trasferta[]>;
}

export function createTrasferta(payload: TrasfertaCreate) {
  return request('/trasferte/create/', { method: 'POST', json: payload }) as Promise<Trasferta>;
}

export function updateTrasferta(tId: number, payload: TrasfertaUpdate) {
  return request(`/trasferte/${tId}/`, { method: 'PUT', json: payload }) as Promise<Trasferta>;
}

export function validateTrasferta(trId: number | string) {
  return request(`/trasferte/${trId}/validation/`, { method: 'PATCH' }) as Promise<Trasferta>;
}

export function deleteTrasferta(tId: number | string) {
  return request(`/trasferte/${tId}/delete/`, { method: 'DELETE' }) as Promise<{ message?: string }>;
}

export function getSpeseByTrasferta(tId: number | string) {
  return request(`/trasferte/${tId}/spese/`) as Promise<Spesa[]>;
}

export async function fetchTrasfertaDossier(uId: number | string, data: string): Promise<Response> {
  const url = `${BASE}/trasferte/${uId}/${data}/dossier/`;
  const res = await authFetch(url, { method: 'GET' });
  if (!res.ok) {
    let message = res.statusText || 'Request failed';
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json().catch(() => null);
      message = data?.errors || data?.error || data?.detail || message;
    } else {
      const text = await res.text().catch(() => '');
      if (text) message = text;
    }
    throw new Error(message);
  }
  return res;
}

export async function getTrasfertaDossier(uId: number | string, data: string) {
  const res = await fetchTrasfertaDossier(uId, data);
  return res.blob();
}

export function createSpesa(tId: number | string, payload: SpesaCreate) {
  return request(`/trasferte/${tId}/spese/create/`, { method: 'POST', json: payload }) as Promise<Spesa>;
}

export function updateSpesa(sId: number | string, payload: SpesaUpdate) {
  return request(`/spese/${sId}/`, { method: 'PUT', json: payload }) as Promise<Spesa>;
}

export function deleteSpesa(sId: number | string) {
  return request(`/spese/${sId}/`, { method: 'DELETE' }) as Promise<{ message?: string }>;
}

export function getScontriniByTrasferta(tId: number | string) {
  return request(`/trasferte/${tId}/scontrini/`)
    .catch(() => request(`${API_ROOT}/trasferte/${tId}/scontrini/`)) as Promise<ScontrinoFile[]>;
}

export function uploadScontrinoByTrasferta(tId: number | string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return request(`/trasferte/${tId}/scontrini/`, { method: 'POST', body: form })
    .catch(() => request(`${API_ROOT}/trasferte/${tId}/scontrini/`, { method: 'POST', body: form })) as Promise<ScontrinoUploadResponse>;
}

export async function getScontrinoByTrasferta(tId: number | string, filename: string) {
  const encoded = encodeURIComponent(filename);
  const paths = [
    `${BASE}/trasferte/${tId}/scontrini/${encoded}/`,
    `${API_ROOT}/trasferte/${tId}/scontrini/${encoded}/`
  ];

  let lastError: Error | null = null;
  for (const url of paths) {
    try {
      const res = await authFetch(url, { method: 'GET' });
      if (!res.ok) {
        let message = res.statusText || 'Request failed';
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await res.json().catch(() => null);
          message = data?.errors || data?.error || data?.detail || message;
        } else {
          const text = await res.text().catch(() => '');
          if (text) message = text;
        }
        throw new Error(message);
      }
      return res.blob();
    } catch (e: any) {
      lastError = e instanceof Error ? e : new Error(String(e));
    }
  }

  throw lastError ?? new Error('Errore download scontrino');
}

export function deleteScontrinoByTrasferta(tId: number | string, filename: string) {
  const encoded = encodeURIComponent(filename);
  return request(`/trasferte/${tId}/scontrini/${encoded}/delete/`, { method: 'DELETE' })
    .catch(() => request(`${API_ROOT}/trasferte/${tId}/scontrini/${encoded}/delete/`, { method: 'DELETE' })) as Promise<{ message?: string }>;
}
