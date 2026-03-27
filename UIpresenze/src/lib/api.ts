import { PUBLIC_API_BASE } from '$env/static/public';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

const DEFAULT_API_BASE = '/presenze';
const BASE = `${(PUBLIC_API_BASE || DEFAULT_API_BASE).replace(/\/$/, '')}/api`;
const AUTO_REFRESH_MS = 14 * 60 * 1000;

export function getAuthToken() {
  return get(auth).token;
}

type Opts = RequestInit & { json?: any; formData?: FormData };
let refreshingPromise: Promise<void> | null = null;
let refreshTimer: ReturnType<typeof setInterval> | null = null;

function withJsonBody(opts: Opts) {
  const headers = new Headers(opts.headers || {});
  const hasFormData = opts.formData instanceof FormData;
  if (opts.json !== undefined && !hasFormData) {
    headers.set('Content-Type', 'application/json');
  }
  return {
    ...opts,
    headers,
    credentials: 'include' as RequestCredentials,
    body: hasFormData ? opts.formData : opts.json !== undefined ? JSON.stringify(opts.json) : opts.body
  };
}

async function refreshSession(): Promise<void> {
  if (!refreshingPromise) {
    refreshingPromise = (async () => {
      const res = await fetch(`${BASE}/refresh/`, {
        method: 'POST',
        credentials: 'include'
      });
      if (!res.ok) {
        auth.logout({ redirect: false });
        throw new Error('Sessione scaduta');
      }
    })().finally(() => {
      refreshingPromise = null;
    });
  }
  return refreshingPromise;
}

export function startAutoRefresh() {
  if (refreshTimer || typeof window === 'undefined') return;
  refreshTimer = setInterval(() => {
    refreshSession().catch(() => {
      stopAutoRefresh();
      auth.logout({ redirect: false });
      window.location.href = '/login';
    });
  }, AUTO_REFRESH_MS);
}

export function stopAutoRefresh() {
  if (!refreshTimer) return;
  clearInterval(refreshTimer);
  refreshTimer = null;
}

export async function authFetch(url: string, opts: Opts = {}, allowRefresh = true): Promise<Response> {
  let res = await fetch(url, withJsonBody(opts));
  if (res.status === 401 && allowRefresh && !url.endsWith('/refresh/') && !url.endsWith('/login/')) {
    await refreshSession();
    res = await fetch(url, withJsonBody(opts));
  }
  return res;
}

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const res = await authFetch(url, opts, true);
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

export function apiLogout() {
  return request('/logout/', { method: 'POST' });
}
