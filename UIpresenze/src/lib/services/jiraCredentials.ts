import { apiBase, authFetch } from '$lib/api';

const BASE = apiBase();

type Opts = RequestInit & { json?: unknown };

function extractErrorMessage(data: unknown): string | null {
  if (!data) return null;
  if (typeof data === 'string') return data;
  if (typeof data === 'object' && data !== null) {
    const obj = data as Record<string, unknown>;
    if (typeof obj.error === 'string') return obj.error;
    if (typeof obj.detail === 'string') return obj.detail;
  }
  return null;
}

async function request(path: string, opts: Opts = {}) {
  const url = path.startsWith('http') ? path : `${BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = new Headers(opts.headers || {});
  if (opts.json !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await authFetch(
    url,
    {
      ...opts,
      headers,
      body: opts.json !== undefined ? JSON.stringify(opts.json) : opts.body,
    },
    true
  );
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const message = isJson ? extractErrorMessage(data) : null;
    throw new Error(message || 'Request failed');
  }
  return data as any;
}

export type JiraTokenStatusResponse = {
  configured: boolean;
  token_present: boolean;
  token_valid: boolean | null;
  masked_token?: string;
  error?: string;
};

export function getJiraTokenStatus() {
  return request('/jira/credentials/token/', { method: 'GET' }) as Promise<JiraTokenStatusResponse>;
}

export function overwriteJiraToken(token: string) {
  return request('/jira/credentials/token/', {
    method: 'POST',
    json: { token },
  }) as Promise<{ ok: boolean; configured: boolean; jira_email?: string }>;
}
