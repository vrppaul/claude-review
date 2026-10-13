/**
 * What the reader's scrolling says once, and is then no longer asked: that
 * a file has come near enough for its rows to be worth building, and that a
 * part of the page has been read through.
 */

// How near a file must come to be built: well before it is reached, so it
// is ready by the time it is
const NEAR_ENOUGH = '1500px 0px';
// How much of an element must be within what it is watched in to count: any of it
const ANY_OF_IT = 0;

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
		threshold: ANY_OF_IT
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

/**
 * Call back once the head of something and its end have each been on
 * screen in the area it scrolls in, then stop.
 *
 * That is having read it through: where it begins was in front of the
 * reader, and so was where it ends, in whichever order and however long
 * apart. No time is counted: what the page glides past on its way
 * elsewhere has been on screen too.
 */
export function whenReadThrough(
	head: Element,
	end: Element,
	root: HTMLElement | null,
	onThrough: () => void
): () => void {
	const unseen = new Set([head, end]);
	const observer = new IntersectionObserver((entries, watching) => cameOnScreen(entries, watching, unseen, onThrough), {
		root,
		threshold: ANY_OF_IT
	});
	observer.observe(head);
	observer.observe(end);
	return () => observer.disconnect();
}

/** Some of what is watched came on screen, if any did: once none is left unseen, stop watching, and say so once. */
function cameOnScreen(
	entries: IntersectionObserverEntry[],
	watching: IntersectionObserver,
	unseen: Set<Element>,
	onThrough: () => void
): void {
	const onScreen = entries.filter((entry) => entry.isIntersecting);
	if (onScreen.length === 0) return;
	for (const entry of onScreen) unseen.delete(entry.target);
	if (unseen.size > 0) return;
	watching.disconnect();
	onThrough();
}
