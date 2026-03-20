import type { HandleFetch } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';
import { goto } from '$app/navigation';

export const handleFetch: HandleFetch = async ({ request, fetch }) => {
  const token = get(auth).token;
  if (token) {
    const headers = new Headers(request.headers);
    // don't overwrite existing Authorization if present
    if (!headers.has('authorization')) {
      headers.set('authorization', `Bearer ${token}`);
    }
    const req = new Request(request, { headers });
    const res = await fetch(req);
    if (res.status === 401) {
      // token non valido: esegui logout centralizzato e redirect
      auth.logout({ redirect: false });
      try {
        await goto('/login');
      } catch {
        // fallback
        if (typeof window !== 'undefined') window.location.href = '/login';
      }
    }
    return res;
  }
  return fetch(request);
};
