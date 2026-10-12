/**
 * The reader's theme, applied to the page, and the system's when that is
 * the choice.
 *
 * Only the applying lives here: the choice itself is one of the reader's
 * settings, and is changed there.
 */

import type { Settings } from '$lib/reader/settings.svelte';
import { stopsTogether } from '$lib/utils/stops';

/** A theme as the page carries it: the system's choice made one of the two. */
export type ResolvedTheme = 'light' | 'dark';

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
	// The theme the page carries, once its root says so: set after the root,
	// so whatever reads the page's colours by it reads them in that theme
	#applied = $state<ResolvedTheme | null>(null);

	constructor(settings: Settings) {
		this.#settings = settings;
	}

	/** The theme the page carries now, once one is applied: what to read the page's colours again by. */
	get applied(): ResolvedTheme | null {
		return this.#applied;
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
		const theme = this.#resolved;
		document.documentElement.setAttribute(THEME_ATTRIBUTE, theme);
		this.#applied = theme;
	}

	readonly #followSystem = (event: MediaQueryListEvent): void => {
		this.#system = event.matches ? 'light' : 'dark';
	};
}
