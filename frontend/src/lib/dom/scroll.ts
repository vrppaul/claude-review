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
 * Call back once the reader's scrolling has carried the end of something
 * across the edge of the area it scrolls in — into view, or out above the
 * top — then stop.
 *
 * That is having read it through. Where the end stands as it is first
 * watched carries it across nothing: what is on screen as it is drawn is
 * not read for being there, nor what is above for being past. Out below,
 * as the reader scrolls back up, counts nothing. No time is counted: what
 * the page glides past on its way elsewhere is carried across too.
 */
export function whenReadThrough(end: Element, root: HTMLElement | null, onThrough: () => void): () => void {
	const reports = new EdgeReports(onThrough);
	const observer = new IntersectionObserver((entries, watching) => reports.heard(entries, watching), {
		root,
		threshold: ANY_OF_IT
	});
	observer.observe(end);
	return () => observer.disconnect();
}

/**
 * What an observer of one end reports. Its first report is where the end
 * stood as it began to watch, and carries it across nothing; any after it
 * says the end was carried across an edge.
 */
class EdgeReports {
	// Whether the first report, of where the end stood as it was first watched, has been heard
	#standingHeard = false;
	readonly #onThrough: () => void;

	constructor(onThrough: () => void) {
		this.#onThrough = onThrough;
	}

	/** Reports heard: once one says the end came into view or went out above the top, stop watching, and say so once. */
	heard(entries: IntersectionObserverEntry[], watching: IntersectionObserver): void {
		const [, ...afterTheFirst] = entries;
		const crossings = this.#standingHeard ? entries : afterTheFirst;
		this.#standingHeard = true;
		if (!crossings.some(carriedOnward)) return;
		watching.disconnect();
		this.#onThrough();
	}
}

/** Whether a report says the end came into view, or went out above the top, rather than out below. */
function carriedOnward(entry: IntersectionObserverEntry): boolean {
	const aboveTheTop = entry.rootBounds !== null && entry.boundingClientRect.bottom <= entry.rootBounds.top;
	return entry.isIntersecting || aboveTheTop;
}
