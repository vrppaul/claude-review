/**
 * How the page moves the reader when it moves them itself: smoothly, unless
 * they asked their system for less motion — then at once. The stylesheet
 * holds every animation and transition to the same wish, in one place at its
 * end; a scroll the page starts asks here, since a scroll asked for in code
 * takes no notice of the stylesheet.
 */

// The wish for less motion, as the browser reports it
const LESS_MOTION = '(prefers-reduced-motion: reduce)';

/** How a scroll the page starts moves: gliding, or at once. */
export type Motion = 'smooth' | 'instant';

/** How a scroll the page starts on its own moves. */
export function scrollMotion(): Motion {
	const lessMotion = typeof window.matchMedia === 'function' && window.matchMedia(LESS_MOTION).matches;
	return lessMotion ? 'instant' : 'smooth';
}
