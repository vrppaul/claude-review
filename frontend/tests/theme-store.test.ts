import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushSync } from 'svelte';
import { settingsStore } from '$lib/stores/settings.svelte';
import { themeStore } from '$lib/stores/theme.svelte';

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

/** Where the page reads the theme before its first paint: see index.html. */
const FIRST_PAINT_CACHE = 'claude-review:theme';

describe('themeStore', () => {
	beforeEach(() => {
		localStorage.clear();
		document.documentElement.removeAttribute('data-theme');
		stubSystem(true);
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
		settingsStore.clear();
		themeStore.reset();
	});


	it('follows the system until the reader chooses otherwise', () => {
		expect(themeStore.theme).toBe('system');
		expect(themeStore.resolved).toBe('dark');
	});

	it('applies a choice at once and keeps it for every later review', () => {
		const stop = themeStore.start();

		themeStore.set('light');
		flushSync();

		expect(document.documentElement.getAttribute('data-theme')).toBe('light');
		expect(vi.mocked(fetch)).toHaveBeenCalledWith(
			'/api/settings',
			expect.objectContaining({ method: 'PUT', body: JSON.stringify({ theme: 'light' }) })
		);
		// And for this port's next first paint, before the server can answer
		expect(localStorage.getItem(FIRST_PAINT_CACHE)).toBe('light');
		stop();
	});

	it('reacts when the system flips while following it', () => {
		const listeners: ((e: MediaQueryListEvent) => void)[] = [];
		stubSystem(true, listeners);
		themeStore.reset();
		const stop = themeStore.start();
		flushSync();

		expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
		listeners.forEach((fn) => fn({ matches: false } as MediaQueryListEvent));
		flushSync();

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
		flushSync();

		expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
		stop();
	});

	it('still applies a theme when site data is blocked', () => {
		const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});
		const stop = themeStore.start();

		expect(() => themeStore.set('light')).not.toThrow();
		flushSync();
		expect(document.documentElement.getAttribute('data-theme')).toBe('light');

		setItem.mockRestore();
		stop();
	});
});
