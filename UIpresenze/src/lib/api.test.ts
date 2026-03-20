/**
 * Frontend Tests - Gestionale Presenze Trasferte
 * 
 * Test suite for SvelteKit frontend covering:
 * - Auth store
 * - API client
 * - Services
 * - Components
 * 
 * Run with: npm test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';

// ============================================================
// AUTH STORE TESTS
// ============================================================

describe('Auth Store', () => {
	let auth: any;
	let localStorageMock: any;

	beforeEach(() => {
		// Clear localStorage
		localStorage.clear();
		
		// Mock localStorage
		localStorageMock = {
			store: {} as Record<string, string>,
			getItem: vi.fn(function (key: string) {
				return this.store[key] || null;
			}),
			setItem: vi.fn(function (key: string, value: string) {
				this.store[key] = value;
			}),
			removeItem: vi.fn(function (key: string) {
				delete this.store[key];
			}),
			clear: vi.fn(function () {
				this.store = {};
			})
		};
		
		// Replace localStorage
		global.localStorage = localStorageMock as any;
		
		// Import fresh instance
		vi.resetModules();
	});

	it('should initialize with default auth state', async () => {
		const { auth } = await import('$lib/stores/auth');
		const state = get(auth);
		
		expect(state.isAuthed).toBe(false);
		expect(state.token).toBeNull();
		expect(state.user).toBeNull();
	});

	it('should initialize from localStorage on init()', async () => {
		// Pre-populate localStorage
		const mockState = {
			token: 'test-token-123',
			user: { id: 1, email: 'test@example.com', nome: 'Test' }
		};
		localStorage.setItem('auth_state', JSON.stringify(mockState));
		
		const { auth } = await import('$lib/stores/auth');
		auth.init();
		
		const state = get(auth);
		expect(state.isAuthed).toBe(true);
		expect(state.token).toBe('test-token-123');
		expect(state.user).toEqual(mockState.user);
	});

	it('should persist to localStorage on login()', async () => {
		const { auth } = await import('$lib/stores/auth');
		
		const mockUser = { id: 1, email: 'test@example.com', nome: 'Test' };
		auth.login('test-token', mockUser);
		
		expect(localStorage.setItem).toHaveBeenCalled();
		const stored = JSON.parse(localStorageMock.store['auth_state']);
		expect(stored.token).toBe('test-token');
		expect(stored.user).toEqual(mockUser);
		
		const state = get(auth);
		expect(state.isAuthed).toBe(true);
		expect(state.token).toBe('test-token');
	});

	it('should clear state and localStorage on logout()', async () => {
		const { auth } = await import('$lib/stores/auth');
		
		// Login first
		auth.login('test-token', { id: 1, email: 'test@example.com' });
		
		// Logout
		auth.logout({ redirect: false });
		
		expect(localStorage.removeItem).toHaveBeenCalledWith('auth_state');
		
		const state = get(auth);
		expect(state.isAuthed).toBe(false);
		expect(state.token).toBeNull();
		expect(state.user).toBeNull();
	});

	it('should update user with setUser()', async () => {
		const { auth } = await import('$lib/stores/auth');
		
		const newUser = { 
			id: 1, 
			email: 'updated@example.com', 
			nome: 'Updated',
			is_superuser: true 
		};
		
		auth.setUser(newUser);
		
		const state = get(auth);
		expect(state.user).toEqual(newUser);
		expect(state.user?.is_superuser).toBe(true);
	});

	it('should handle malformed localStorage data gracefully', async () => {
		// Invalid JSON
		localStorage.setItem('auth_state', 'invalid-json');
		
		const { auth } = await import('$lib/stores/auth');
		
		// Should not throw
		expect(() => auth.init()).not.toThrow();
		
		const state = get(auth);
		expect(state.isAuthed).toBe(false);
	});
});

// ============================================================
// API CLIENT TESTS
// ============================================================

describe('API Client', () => {
	let mockFetch: any;

	beforeEach(() => {
		// Clear localStorage
		localStorage.clear();
		
		// Mock fetch
		mockFetch = vi.fn();
		global.fetch = mockFetch as any;
		
		// Mock PUBLIC_API_BASE
		vi.mock('$env/static/public', () => ({
			PUBLIC_API_BASE: 'http://localhost:7999'
		}));
	});

	it('should construct correct base URL', async () => {
		const { apiBase } = await import('$lib/api');
		const base = apiBase();
		
		expect(base).toBe('http://localhost:7999/api');
	});

	it('should include auth token in requests when available', async () => {
		// Setup auth
		const { auth } = await import('$lib/stores/auth');
		auth.login('test-token', { id: 1, email: 'test@example.com' });
		
		const { request } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => ({ data: 'test' }),
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		await request('/profile/');
		
		expect(mockFetch).toHaveBeenCalledWith(
			expect.any(String),
			expect.objectContaining({
				headers: expect.any(Headers)
			})
		);
		
		const callArgs = mockFetch.mock.calls[0];
		const headers = callArgs[1].headers as Headers;
		expect(headers.get('Authorization')).toBe('Bearer test-token');
	});

	it('should not include auth token when not available', async () => {
		const { request } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => ({ data: 'test' }),
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		await request('/public-endpoint/');
		
		const callArgs = mockFetch.mock.calls[0];
		const headers = callArgs[1].headers as Headers;
		expect(headers.get('Authorization')).toBeNull();
	});

	it('should throw error on non-ok response', async () => {
		const { request } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 400,
			json: async () => ({ error: 'Bad request' }),
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		await expect(request('/invalid/')).rejects.toThrow('Bad request');
	});

	it('should handle non-JSON responses', async () => {
		const { request } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			text: async () => 'Plain text response',
			headers: new Headers({ 'content-type': 'text/plain' })
		});
		
		const result = await request('/text-endpoint/');
		expect(result).toBe('Plain text response');
	});

	it('should send JSON payload when json option provided', async () => {
		const { request } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => ({ success: true }),
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		const payload = { email: 'test@example.com', password: 'pass123' };
		await request('/login/', { method: 'POST', json: payload });
		
		expect(mockFetch).toHaveBeenCalledWith(
			expect.any(String),
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify(payload)
			})
		);
		
		const callArgs = mockFetch.mock.calls[0];
		const headers = callArgs[1].headers as Headers;
		expect(headers.get('Content-Type')).toBe('application/json');
	});
});

// ============================================================
// AUTH SERVICE TESTS
// ============================================================

describe('Auth Service (getToken)', () => {
	let mockFetch: any;

	beforeEach(() => {
		localStorage.clear();
		mockFetch = vi.fn();
		global.fetch = mockFetch as any;
	});

	it('should call login endpoint with credentials', async () => {
		const { getToken } = await import('$lib/api');
		
		const mockResponse = {
			token: 'new-token',
			token_type: 'Bearer',
			user: { id: 1, email: 'test@example.com' }
		};
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => mockResponse,
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		const result = await getToken('test@example.com', 'password123');
		
		expect(mockFetch).toHaveBeenCalledWith(
			'http://localhost:7999/api/login/',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({
					email: 'test@example.com',
					password: 'password123'
				})
			})
		);
		
		expect(result).toEqual(mockResponse);
	});

	it('should throw error on invalid credentials', async () => {
		const { getToken } = await import('$lib/api');
		
		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 400,
			json: async () => ({ error: 'Credenziali non valide' }),
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		await expect(getToken('wrong@example.com', 'wrongpass'))
			.rejects.toThrow('Credenziali non valide');
	});
});

// ============================================================
// PROFILE SERVICE TESTS
// ============================================================

describe('Profile Service (getProfile)', () => {
	let mockFetch: any;

	beforeEach(() => {
		localStorage.clear();
		mockFetch = vi.fn();
		global.fetch = mockFetch as any;
		
		// Setup auth
		const { auth } = await import('$lib/stores/auth');
		auth.login('test-token', { id: 1, email: 'test@example.com' });
	});

	it('should fetch user profile with auth token', async () => {
		const { getProfile } = await import('$lib/api');
		
		const mockProfile = {
			id: 1,
			email: 'test@example.com',
			nome: 'Test',
			cognome: 'User',
			saldo: { valore_saldo_validato: '10.00' }
		};
		
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => mockProfile,
			headers: new Headers({ 'content-type': 'application/json' })
		});
		
		const result = await getProfile();
		
		expect(mockFetch).toHaveBeenCalledWith(
			'http://localhost:7999/api/profile/',
			expect.objectContaining({
				headers: expect.any(Headers)
			})
		);
		
		expect(result).toEqual(mockProfile);
	});
});

// ============================================================
// UTILITY TESTS
// ============================================================

describe('Utility Functions', () => {
	it('getAuthToken should return current token', async () => {
		const { auth } = await import('$lib/stores/auth');
		const { getAuthToken } = await import('$lib/api');
		
		auth.login('my-token', { id: 1 });
		
		expect(getAuthToken()).toBe('my-token');
	});

	it('getAuthToken should return null when not authenticated', async () => {
		const { getAuthToken } = await import('$lib/api');
		expect(getAuthToken()).toBeNull();
	});
});
