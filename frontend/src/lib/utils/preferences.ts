/**
 * The choices a reader makes about how a review is drawn.
 *
 * How a markdown file is shown, how wide the panels are: none of these
 * belong to a particular review, they are how this person reads this page.
 * Kept in the browser's own storage, which belongs to one port; what should
 * follow the reader into every review lives in `reader/settings.svelte.ts`.
 */

// What every name this page keeps in the port's storage begins with. The
// first paint reads the theme under it too, in index.html, which cannot
// import it and spells it out.
const STORAGE_PREFIX = 'claude-review:';

/** Where in this port's storage a choice of this name is kept. */
export function storageKey(name: string): string {
	return `${STORAGE_PREFIX}${name}`;
}

/** Read a stored choice, falling back when it is missing or no longer valid. */
export function readChoice<T extends string>(name: string, allowed: readonly T[], fallback: T): T {
	try {
		const stored = localStorage.getItem(storageKey(name));
		return allowed.includes(stored as T) ? (stored as T) : fallback;
	} catch {
		// Private mode and blocked site data both throw; the default is fine
		return fallback;
	}
}

export function readFlag(name: string, fallback = false): boolean {
	try {
		const stored = localStorage.getItem(storageKey(name));
		return stored === null ? fallback : stored === 'on';
	} catch {
		return fallback;
	}
}

/**
 * Read a stored measurement, holding it to what the layout can take.
 *
 * A width saved on a wide screen must not leave a narrow one with no room
 * for the diff, so the bounds are applied on the way out rather than only
 * when it is set.
 */
export function readNumber(
	name: string,
	{ min, max, fallback }: { min: number; max: number; fallback: number }
): number {
	try {
		const stored = Number.parseInt(localStorage.getItem(storageKey(name)) ?? '', 10);
		if (!Number.isFinite(stored)) return fallback;
		return Math.min(max, Math.max(min, stored));
	} catch {
		return fallback;
	}
}

export function writeChoice(name: string, value: string | number | boolean): void {
	try {
		const stored = typeof value === 'boolean' ? (value ? 'on' : 'off') : String(value);
		localStorage.setItem(storageKey(name), stored);
	} catch {
		// The choice still applies to this tab, it just will not be remembered
	}
}

/** Drop a stored choice that something else now keeps. */
export function forget(name: string): void {
	try {
		localStorage.removeItem(storageKey(name));
	} catch {
		// Blocked site data: there is nothing stored to drop
	}
}
