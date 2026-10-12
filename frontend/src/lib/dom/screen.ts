/**
 * How wide the screen is, against the breakpoints the stylesheet names.
 *
 * Each breakpoint is written once, in tokens.css, and the built stylesheet
 * sets it on the page's root; the page reads it there by name and asks the
 * browser about it, so what the page decides and what the stylesheet lays
 * out never part ways. A page with nothing to ask — no `matchMedia`, as
 * where no browser lays the page out — is taken to be on a wide screen, as
 * the page always was.
 */

/** Whether the screen is at least as wide as a breakpoint the stylesheet names, by its theme variable. */
export function screenReaches(breakpoint: string): boolean {
	if (typeof window.matchMedia !== 'function') return true;
	const width = getComputedStyle(document.documentElement).getPropertyValue(breakpoint).trim();
	return window.matchMedia(`(width >= ${width})`).matches;
}
