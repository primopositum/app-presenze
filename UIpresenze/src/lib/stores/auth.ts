import { writable } from 'svelte/store';
import type { Readable } from 'svelte/store';
import { goto } from '$app/navigation';

type User = any;

type AuthState = {
  isAuthed: boolean;
  token: string | null;
  user: User | null;
};

type AuthStore = Readable<AuthState> & {
  init: () => void;
  login: (tokenOrUser: string | User | null, maybeUser?: User | null) => void;
  logout: (options?: { redirect?: boolean }) => void;
  setUser: (user: User | null) => void;
};

function createAuth(): AuthStore {
  const { subscribe, set } = writable<AuthState>({
    isAuthed: false,
    token: null,
    user: null
  });
  let current: AuthState = {
    isAuthed: false,
    token: null,
    user: null
  };
  const STORAGE_KEY = 'auth_state';
  let hydrated = false;

  subscribe((value) => {
    current = value;
    if (typeof window === 'undefined' || !hydrated) return;
    try {
      if (value.isAuthed && (value.token || value.user)) {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ isAuthed: value.isAuthed, token: value.token, user: value.user })
        );
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // ignore storage errors (e.g. private mode)
    }
  });

  function init() {
    if (typeof window === 'undefined') return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw) as Partial<AuthState> | null;
      if (!data || typeof data !== 'object') return;
      const hasUser = !!data.user;
      const hasToken = !!data.token;
      set({
        isAuthed: !!data.isAuthed || hasToken || hasUser,
        token: data.token ?? null,
        user: data.user ?? null
      });
    } catch {
      // ignore invalid or inaccessible storage
    } finally {
      hydrated = true;
    }
  }

  function login(tokenOrUser: string | User | null, maybeUser: User | null = null) {
    if (typeof tokenOrUser === 'string') {
      set({ isAuthed: true, token: tokenOrUser, user: maybeUser });
      return;
    }
    const user = tokenOrUser as User | null;
    set({ isAuthed: !!user, token: null, user });
  }

  function setUser(user: User | null) {
    set({ ...current, user });
  }

  function logout(options: { redirect?: boolean } = { redirect: true }) {
    set({ isAuthed: false, token: null, user: null });
    if (options.redirect) {
      // best effort redirect client-side
      try {
        goto('/login');
      } catch {
        if (typeof window !== 'undefined') window.location.href = '/login';
      }
    }
  }

  return { subscribe, init, login, logout, setUser };
}

export const auth = createAuth();

