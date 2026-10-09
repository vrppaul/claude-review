/**
 * The reader's theme, applied to the page, and the system's when that is
 * the choice.
 *
 * Only the applying lives here: the choice itself is one of the reader's
 * settings, and is changed there.
 */

import type { Settings } from '$lib/reader/settings.svelte';

type ResolvedTheme = 'light' | 'dark';

const SYSTEM_PREFERS_DARK = '(prefers-color-scheme: dark)';
// What the page's root carries for the styles to read
const THEME_ATTRIBUTE = 'data-theme';

function systemTheme(): ResolvedTheme {
	// Absent in jsdom and in browsers old enough not to matter here
	if (typeof window.matchMedia !== 'function') return 'dark';
	return window.matchMedia(SYSTEM_PREFERS_DARK).matches ? 'dark' : 'light';
}

export class PageTheme {
	readonly #settings: Settings;
	#system = $state<ResolvedTheme>(systemTheme());
	readonly #resolved = $derived.by<ResolvedTheme>(() => {
		const chosen = this.#settings.current.theme;
		return chosen === 'system' ? this.#system : chosen;
	});

	constructor(settings: Settings) {
		this.#settings = settings;
	}

	/**
	 * Apply the theme whenever it changes — chosen, read from the server, or
	 * followed from the system. Returns a teardown.
	 */
	start(): () => void {
		const stopApplying = $effect.root(() => {
			$effect(() => this.#apply());
		});
		if (typeof window.matchMedia !== 'function') return stopApplying;

		const query = window.matchMedia(SYSTEM_PREFERS_DARK);
		query.addEventListener('change', this.#followSystem);
		return () => {
			stopApplying();
			query.removeEventListener('change', this.#followSystem);
		};
	}

	#apply(): void {
		document.documentElement.setAttribute(THEME_ATTRIBUTE, this.#resolved);
	}

	readonly #followSystem = (event: MediaQueryListEvent): void => {
		this.#system = event.matches ? 'dark' : 'light';
	};
}
