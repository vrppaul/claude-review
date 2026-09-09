import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { themeStore, THEME_STORAGE_KEY } from '$lib/stores/theme.svelte';

function stubSystem(prefersDark: boolean, listeners: ((e: MediaQueryListEvent) => void)[] = []) {
	vi.stubGlobal(
		'matchMedia',
		vi.fn().mockImplementation((query: string) => ({
			matches: query.includes('dark') ? prefersDark : !prefersDark,
			addEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => listeners.push(fn),
			removeEventListener: () => {}
		}))
	);
}

describe('themeStore', () => {
	beforeEach(() => {
		localStorage.clear();
		document.documentElement.removeAttribute('data-theme');
		stubSystem(true);
		themeStore.reset();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('follows the system until the reader chooses otherwise', () => {
		expect(themeStore.theme).toBe('system');
		expect(themeStore.resolved).toBe('dark');
	});

	it('remembers the choice for the next session', () => {
		themeStore.set('light');

		expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
		expect(document.documentElement.getAttribute('data-theme')).toBe('light');
	});

	it('restores a remembered choice over the system preference', () => {
		localStorage.setItem(THEME_STORAGE_KEY, 'light');
		themeStore.reset();

		expect(themeStore.theme).toBe('light');
		expect(themeStore.resolved).toBe('light');
	});

	it('cycles system, light, dark and back', () => {
		expect(themeStore.theme).toBe('system');
		themeStore.cycle();
		expect(themeStore.theme).toBe('light');
		themeStore.cycle();
		expect(themeStore.theme).toBe('dark');
		themeStore.cycle();
		expect(themeStore.theme).toBe('system');
	});

	it('reacts when the system flips while following it', () => {
		const listeners: ((e: MediaQueryListEvent) => void)[] = [];
		stubSystem(true, listeners);
		themeStore.reset();
		const stop = themeStore.start();

		expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
		listeners.forEach((fn) => fn({ matches: false } as MediaQueryListEvent));

		expect(document.documentElement.getAttribute('data-theme')).toBe('light');
		stop();
	});

	it('ignores a system flip once a theme has been chosen', () => {
		const listeners: ((e: MediaQueryListEvent) => void)[] = [];
		stubSystem(true, listeners);
		themeStore.reset();
		const stop = themeStore.start();
		themeStore.set('dark');

		listeners.forEach((fn) => fn({ matches: false } as MediaQueryListEvent));

		expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
		stop();
	});

	it('still applies a theme when site data is blocked', () => {
		const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});

		expect(() => themeStore.set('light')).not.toThrow();
		expect(document.documentElement.getAttribute('data-theme')).toBe('light');

		setItem.mockRestore();
	});
});
