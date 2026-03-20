/**
 * Auth Store Tests
 * 
 * Comprehensive tests for the authentication store
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

describe('Auth Store - Comprehensive', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.clearAllMocks();
	});

	describe('Initialization', () => {
		it('should start with default logged out state', () => {
			const state = get(auth);
			
			expect(state).toEqual({
				isAuthed: false,
				token: null,
				user: null
			});
		});

		it('should restore state from valid localStorage', () => {
			const mockData = {
				token: 'restored-token',
				user: {
					id: 42,
					email: 'restored@example.com',
					nome: 'Restored',
					cognome: 'User',
					is_superuser: false
				}
			};
			
			localStorage.setItem('auth_state', JSON.stringify(mockData));
			auth.init();
			
			const state = get(auth);
			expect(state.isAuthed).toBe(true);
			expect(state.token).toBe('restored-token');
			expect(state.user).toEqual(mockData.user);
		});

		it('should handle missing localStorage gracefully', () => {
			// No localStorage item
			auth.init();
			
			const state = get(auth);
			expect(state.isAuthed).toBe(false);
			expect(state.token).toBeNull();
		});

		it('should handle invalid JSON in localStorage', () => {
			localStorage.setItem('auth_state', 'not-valid-json');
			
			// Should not throw
			expect(() => auth.init()).not.toThrow();
			
			const state = get(auth);
			expect(state.isAuthed).toBe(false);
		});

		it('should handle partial data in localStorage', () => {
			const partialData = { token: 'only-token' };
			localStorage.setItem('auth_state', JSON.stringify(partialData));
			
			auth.init();
			
			const state = get(auth);
			expect(state.token).toBe('only-token');
			expect(state.user).toBeNull();
		});
	});

	describe('Login', () => {
		it('should set auth state and persist to localStorage', () => {
			const user = {
				id: 1,
				email: 'login@example.com',
				nome: 'Login',
				cognome: 'Test',
				is_superuser: true
			};
			
			auth.login('new-token', user);
			
			// Check store state
			const state = get(auth);
			expect(state.isAuthed).toBe(true);
			expect(state.token).toBe('new-token');
			expect(state.user).toEqual(user);
			
			// Check localStorage
			const stored = localStorage.getItem('auth_state');
			expect(stored).toBeTruthy();
			
			const parsed = JSON.parse(stored!);
			expect(parsed.token).toBe('new-token');
			expect(parsed.user).toEqual(user);
		});

		it('should overwrite existing auth state', () => {
			// Initial login
			auth.login('first-token', { id: 1, email: 'first@example.com' });
			
			// Second login
			auth.login('second-token', { id: 2, email: 'second@example.com' });
			
			const state = get(auth);
			expect(state.token).toBe('second-token');
			expect(state.user?.email).toBe('second@example.com');
			
			const stored = JSON.parse(localStorage.getItem('auth_state')!);
			expect(stored.token).toBe('second-token');
		});
	});

	describe('Logout', () => {
		it('should clear auth state and localStorage', () => {
			// Login first
			auth.login('token-to-clear', { id: 1, email: 'test@example.com' });
			
			// Logout
			auth.logout({ redirect: false });
			
			const state = get(auth);
			expect(state.isAuthed).toBe(false);
			expect(state.token).toBeNull();
			expect(state.user).toBeNull();
			
			expect(localStorage.removeItem).toHaveBeenCalledWith('auth_state');
		});

		it('should clear state even if localStorage fails', () => {
			auth.login('token', { id: 1 });
			
			// Mock localStorage.removeItem to throw
			vi.spyOn(localStorage, 'removeItem').mockImplementation(() => {
				throw new Error('Storage error');
			});
			
			// Should not throw
			expect(() => auth.logout({ redirect: false })).not.toThrow();
			
			// State should still be cleared
			const state = get(auth);
			expect(state.isAuthed).toBe(false);
		});

		it('should accept optional redirect parameter', () => {
			auth.login('token', { id: 1 });
			
			// Logout without redirect
			auth.logout({ redirect: false });
			
			// With redirect (default behavior would navigate)
			auth.login('token', { id: 1 });
			auth.logout();
			
			expect(get(auth).isAuthed).toBe(false);
		});
	});

	describe('SetUser', () => {
		it('should update user in state and localStorage', () => {
			// Initial login
			auth.login('token', { id: 1, email: 'old@example.com', nome: 'Old' });
			
			// Update user
			const updatedUser = {
				id: 1,
				email: 'updated@example.com',
				nome: 'Updated',
				cognome: 'Name',
				is_superuser: true
			};
			
			auth.setUser(updatedUser);
			
			const state = get(auth);
			expect(state.user).toEqual(updatedUser);
			
			const stored = JSON.parse(localStorage.getItem('auth_state')!);
			expect(stored.user).toEqual(updatedUser);
		});

		it('should work without prior login', () => {
			const newUser = { id: 99, email: 'new@example.com' };
			auth.setUser(newUser);
			
			const state = get(auth);
			expect(state.user).toEqual(newUser);
			// Note: isAuthed might still be false if no token
		});

		it('should handle null user', () => {
			auth.login('token', { id: 1 });
			auth.setUser(null);
			
			const state = get(auth);
			expect(state.user).toBeNull();
		});
	});

	describe('Reactivity', () => {
		it('should notify subscribers on state changes', () => {
			const callback = vi.fn();
			
			const unsubscribe = auth.subscribe(callback);
			
			// Initial call
			expect(callback).toHaveBeenCalledTimes(1);
			
			// Login should trigger callback
			auth.login('token', { id: 1 });
			expect(callback).toHaveBeenCalledTimes(2);
			
			// Logout should trigger callback
			auth.logout({ redirect: false });
			expect(callback).toHaveBeenCalledTimes(3);
			
			unsubscribe();
		});
	});
});
