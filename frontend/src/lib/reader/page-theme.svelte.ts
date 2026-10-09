/**
 * The reader's theme, applied to the page, and the system's when that is
 * the choice.
 *
 * Only the applying lives here: the choice itself is one of the reader's
 * settings, and is changed there.
 */

import type { Settings } from '$lib/reader/settings.svelte';
import { stopsTogether } from '$lib/utils/stops';

type ResolvedTheme = 'light' | 'dark';

// Light only when the system asks for it, dark otherwise — the rule the
// first paint in index.html keeps too, before any of this has loaded
const SYSTEM_PREFERS_LIGHT = '(prefers-color-scheme: light)';
// What the page's root carries for the styles to read
const THEME_ATTRIBUTE = 'data-theme';

function systemTheme(): ResolvedTheme {
	// Absent in jsdom and in browsers old enough not to matter here
	if (typeof window.matchMedia !== 'function') return 'dark';
	return window.matchMedia(SYSTEM_PREFERS_LIGHT).matches ? 'light' : 'dark';
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

		const query = window.matchMedia(SYSTEM_PREFERS_LIGHT);
		query.addEventListener('change', this.#followSystem);
		return stopsTogether(stopApplying, () => query.removeEventListener('change', this.#followSystem));
	}

	#apply(): void {
		document.documentElement.setAttribute(THEME_ATTRIBUTE, this.#resolved);
	}

	readonly #followSystem = (event: MediaQueryListEvent): void => {
		this.#system = event.matches ? 'light' : 'dark';
	};
}
