import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: any; formData?: FormData };

function extractErrorMessage(data: any): string | null {
  if (!data) return null;
  if (typeof data === 'string') return data;
  if (typeof data.error === 'string') return data.error;
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data.errors === 'string') return data.errors;
  if (Array.isArray(data)) {
    for (const item of data) {
      const nested = extractErrorMessage(item);
      if (nested) return nested;
    }
  }
  if (typeof data === 'object') {
    for (const value of Object.values(data)) {
      const nested = extractErrorMessage(value);
      if (nested) return nested;
    }
  }
  return null;
}

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);

  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    throw new Error((isJson && extractErrorMessage(data)) || 'Request failed');
  }
  return data as any;
}

export type Signature = {
  id: string;
  // backward-compatibility for older call sites/payloads
  svg?: string;
  mime_type: string;
  file_name: string;
  preview_data_url: string | null;
  created_at: string;
  updated_at?: string;
};

export type SignaturePayload = {
  file: File;
  user_id?: number;
};

export function normalizeSignaturePayload(payload: unknown): Signature | null {
  if (!payload) return null;
  if (Array.isArray(payload)) return (payload[0] as Signature) ?? null;
  if (typeof payload === 'object') {
    const data = payload as Record<string, unknown>;
    if (data.signature === null) return null;
    if (typeof data.id === 'string' && typeof data.mime_type === 'string') return data as unknown as Signature;
    if (data.signature && typeof data.signature === 'object') return data.signature as Signature;
  }
  return null;
}

export function createSignature(payload: SignaturePayload): Promise<Signature> {
  const formData = new FormData();
  formData.append('file', payload.file);
  if (payload.user_id !== undefined) {
    formData.append('user_id', String(payload.user_id));
  }
  return request('/signatures/', { method: 'POST', formData });
}

export function getLatestSignature(userId?: number): Promise<Signature | { signature: null }> {
  const query = Number.isFinite(Number(userId)) ? `?user_id=${Number(userId)}` : '';
  return request(`/showSignatures/${query}`, { method: 'GET' });
}
