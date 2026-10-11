/**
 * Building what is about to be read: a file's rows are worth building once
 * it comes near enough to the reader.
 */

// How near a file must come to be built: well before it is reached, so it
// is ready by the time it is
const NEAR_ENOUGH = '1500px 0px';

/**
 * Call back once an element comes within reach of the viewport, then stop.
 *
 * Used to decide when a file's rows are worth building. A review of sixty
 * files is tens of thousands of table rows, and building them all before
 * anything appears costs seconds — and makes every later change to the
 * comment list cost again. The margin is generous so a file is ready well
 * before it is reached, and nothing is torn down once built: a file scrolled
 * past stays in the document, and stays findable.
 */
export function whenNearViewport(element: HTMLElement, root: HTMLElement | null, onNear: () => void): () => void {
	const observer = new IntersectionObserver((entries, watching) => cameNear(entries, watching, onNear), {
		root,
		rootMargin: NEAR_ENOUGH,
		threshold: 0
	});
	observer.observe(element);
	return () => observer.disconnect();
}

/** The element came within reach, if it did: stop watching it, and say so once. */
function cameNear(entries: IntersectionObserverEntry[], watching: IntersectionObserver, onNear: () => void): void {
	if (!entries.some((entry) => entry.isIntersecting)) return;
	watching.disconnect();
	onNear();
}
