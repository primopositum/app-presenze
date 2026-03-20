import { PUBLIC_API_BASE } from '$env/static/public';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

const BASE = (PUBLIC_API_BASE + '/api').replace(/\/$/, '');

export function getAuthToken() {
  return get(auth).token;
}

type Opts = RequestInit & { json?: any };

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers(opts.headers || {});
  if (opts.json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getAuthToken();
  // Attach Authorization header if token available (unless explicitly provided)
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

export function apiBase() {
  return BASE;
}

// Auth
export async function getToken(email: string, password: string) {
  const resp = await request('/login/', { method: 'POST', json: { email, password } });
  return resp;
}

// Profilo
export function getProfile() {
  return request('/profile/');
}
