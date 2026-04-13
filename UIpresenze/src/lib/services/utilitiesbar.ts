import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts);

  let data: any = null;
  const contentType = res.headers.get('content-type');
  if (res.status !== 204 && res.status !== 205) {
    data = contentType?.includes('application/json') ? JSON.parse((await res.text()) || 'null') : await res.text();
  }

  if (!res.ok) {
    const message = (data?.errors || data?.error || data?.detail) || res.statusText || 'Request failed';
    throw new Error(message);
  }

  return data;
}

export type UtilitiesBarItem = {
  id: number;
  link: string;
  colore: string;
  icon: string;
  posizione: number;
};

export function getUtilitiesBar() {
  return request('/utilitiesbar/') as Promise<UtilitiesBarItem[]>;
}
