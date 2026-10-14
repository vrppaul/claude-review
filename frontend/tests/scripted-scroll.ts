/**
 * A scroll the test scripts. jsdom lays nothing out, so nothing ever comes
 * into view by itself: here every observer the page makes reports where
 * what it watches stands — as it begins to watch, as a browser's observer
 * does, and then only when the test says what the reader has scrolled to.
 * Until the test scrolls, nothing is in view and everything is below.
 */
import { vi } from 'vitest';

/** Where an element stands, by its top and bottom edges. */
interface Edges {
	top: number;
	bottom: number;
}

// The area every observer watches within, and where an element stands above it, in it and below it
const THE_AREA: Edges = { top: 0, bottom: 100 };
const ABOVE: Edges = { top: -20, bottom: -10 };
const IN_VIEW: Edges = { top: 40, bottom: 60 };
const BELOW: Edges = { top: 200, bottom: 220 };

// Every observer made since the scroll was last scripted
const made: ScriptedObserver[] = [];
// Where the reader is, as the test last scrolled: where what stands in view or above it stands. Everything else is below
let standing = new Map<Element, Edges>();

/** What an observer reports of one element: whether it is in view, and where it and the area stand. */
function entryOf(target: Element): IntersectionObserverEntry {
	const edges = standing.get(target) ?? BELOW;
	return {
		target,
		isIntersecting: edges === IN_VIEW,
		boundingClientRect: edges,
		rootBounds: THE_AREA
	} as IntersectionObserverEntry;
}

/** An observer that tells, of the elements it watches, where they stand: as it begins, and when the test scrolls. */
class ScriptedObserver {
	/** The area it was told to watch within; null for the page itself. */
	readonly area: Element | Document | null;
	readonly #callback: IntersectionObserverCallback;
	readonly #watched = new Set<Element>();

	constructor(callback: IntersectionObserverCallback, options: IntersectionObserverInit = {}) {
		this.#callback = callback;
		this.area = options.root ?? null;
		made.push(this);
	}

	observe(target: Element): void {
		this.#watched.add(target);
		this.#callback([entryOf(target)], this as unknown as IntersectionObserver);
	}

	unobserve(target: Element): void {
		this.#watched.delete(target);
	}

	disconnect(): void {
		this.#watched.clear();
	}

	/** Whether it is still watching an element. */
	watches(element: Element): boolean {
		return this.#watched.has(element);
	}

	/** Tell whoever watches where what it watches stands now. */
	report(): void {
		this.#callback([...this.#watched].map(entryOf), this as unknown as IntersectionObserver);
	}
}

/**
 * From here to the end of the test nothing is in view until the test
 * scrolls to it. The stub is dropped with the test, as every stub is.
 */
export function scriptTheScroll(): void {
	made.length = 0;
	standing = new Map();
	vi.stubGlobal('IntersectionObserver', ScriptedObserver);
}

/**
 * The areas an element is being watched within now, one for each observer
 * still watching it: an observer the page has let go of watches nothing.
 */
export function areasWatching(element: Element): (Element | Document | null)[] {
	return made.filter((observer) => observer.watches(element)).map((observer) => observer.area);
}

/** The reader scrolled until these, and only these, are in view, and nothing is above them. */
export function scrollTo(...shown: Element[]): void {
	standing = new Map(shown.map((element) => [element, IN_VIEW]));
	for (const observer of made) observer.report();
}

/** The reader scrolled on until these have gone out above the top, and nothing is in view. */
export function scrollPast(...passed: Element[]): void {
	standing = new Map(passed.map((element) => [element, ABOVE]));
	for (const observer of made) observer.report();
}
