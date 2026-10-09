import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushSync } from 'svelte';
import { PageTheme } from '$lib/reader/page-theme.svelte';
import { Settings } from '$lib/reader/settings.svelte';
import { fakeServer, keepingSettings, type FakeServer } from './fake-server';

type SystemListener = (event: MediaQueryListEvent) => void;

/** Where the page reads the theme before its first paint: see index.html. */
const FIRST_PAINT_CACHE = 'claude-review:theme';

/** A system that prefers dark or light, telling `listeners` when that changes. */
function stubSystem(prefersDark: boolean, listeners: SystemListener[] = []) {
	vi.stubGlobal(
		'matchMedia',
		vi.fn().mockImplementation((query: string) => ({
			matches: query.includes('dark') ? prefersDark : !prefersDark,
			addEventListener: (_kind: string, listener: SystemListener) => listeners.push(listener),
			removeEventListener: vi.fn()
		}))
	);
}

/** The system changing its mind about dark. */
function systemFlips(listeners: SystemListener[], prefersDark: boolean) {
	for (const listener of listeners) listener({ matches: prefersDark } as MediaQueryListEvent);
}

/** The theme on the page's root, where the styles read it. */
function applied(): string | null {
	return document.documentElement.getAttribute('data-theme');
}

describe('the theme', () => {
	let server: FakeServer;
	let settings: Settings;

	beforeEach(() => {
		document.documentElement.removeAttribute('data-theme');
		stubSystem(true);
		server = fakeServer();
		keepingSettings(server);
		settings = new Settings();
	});

	it('follows the system until the reader chooses otherwise', () => {
		const stop = new PageTheme(settings).start();
		flushSync();

		expect(settings.current.theme).toBe('system');
		expect(applied()).toBe('dark');
		stop();
	});

	it('applies a choice at once and keeps it for every later review', () => {
		const stop = new PageTheme(settings).start();

		void settings.change({ theme: 'light' });
		flushSync();

		expect(applied()).toBe('light');
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ theme: 'light' }]);
		// And for this port's next first paint, before the server can answer
		expect(localStorage.getItem(FIRST_PAINT_CACHE)).toBe('light');
		stop();
	});

	it('reacts when the system flips while following it', () => {
		const listeners: SystemListener[] = [];
		stubSystem(true, listeners);
		const stop = new PageTheme(settings).start();
		flushSync();

		expect(applied()).toBe('dark');
		systemFlips(listeners, false);
		flushSync();

		expect(applied()).toBe('light');
		stop();
	});

	it('ignores a system flip once a theme has been chosen', () => {
		const listeners: SystemListener[] = [];
		stubSystem(true, listeners);
		const stop = new PageTheme(settings).start();
		void settings.change({ theme: 'dark' });

		systemFlips(listeners, false);
		flushSync();

		expect(applied()).toBe('dark');
		stop();
	});

	it('still applies a theme when site data is blocked', async () => {
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});
		const stop = new PageTheme(settings).start();

		await settings.change({ theme: 'light' });
		flushSync();
		expect(applied()).toBe('light');

		stop();
	});
});
