import type { HandleFetch } from '@sveltejs/kit';
import { auth } from '$lib/stores/auth';
import { goto } from '$app/navigation';
import { stopAutoRefresh } from '$lib/api';

export const handleFetch: HandleFetch = async ({ request, fetch }) => {
  const res = await fetch(request);
  if (res.status === 401) {
    stopAutoRefresh();
    auth.logout({ redirect: false });
    try {
      await goto('/login');
    } catch {
      if (typeof window !== 'undefined') window.location.href = '/login';
    }
  }
  return res;
};
