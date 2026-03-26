import { apiBase, getAuthToken } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

function extractErrorMessage(data: any): string | null {
  if (!data) return null;
  if (typeof data === 'string') return data;
  if (typeof data.error === 'string') return data.error;
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data.errors === 'string') return data.errors;
  return null;
}

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
    throw new Error((isJson && extractErrorMessage(data)) || 'Request failed');
  }
  return data as any;
}

export type Signature = {
  id: string;
  svg: string;
  width?: number | null;
  height?: number | null;
  created_at: string;
};

export type SignaturePayload = {
  svg: string;
  width?: number;
  height?: number;
  user_id?: number;
};

export function normalizeSignaturePayload(payload: unknown): Signature | null {
  if (!payload) return null;
  if (Array.isArray(payload)) return (payload[0] as Signature) ?? null;
  if (typeof payload === 'object') {
    const data = payload as Record<string, unknown>;
    if (data.signature === null) return null;
    if (typeof data.id === 'string' && typeof data.svg === 'string') return data as unknown as Signature;
    if (data.signature && typeof data.signature === 'object') return data.signature as Signature;
  }
  return null;
}

export function createSignature(payload: SignaturePayload): Promise<Signature> {
  return request('/signatures/', { method: 'POST', json: payload });
}

export function getLatestSignature(userId?: number): Promise<Signature | { signature: null }> {
  const query = Number.isFinite(Number(userId)) ? `?user_id=${Number(userId)}` : '';
  return request(`/showSignatures/${query}`, { method: 'GET' });
}
