/**
 * A scroll the test scripts. jsdom lays nothing out, so nothing ever comes
 * into view by itself: here every observer the page makes reports only when
 * the test says what the reader has scrolled to.
 */
import { vi } from 'vitest';

// Every observer made since the scroll was last scripted
const made: ScriptedObserver[] = [];

/** An observer that tells, of the elements it watches, which are in view — when the test scrolls, never before. */
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

	/** Tell whoever watches which of what it watches is in view now. */
	report(shown: readonly Element[]): void {
		const entries = [...this.#watched].map((target) => ({ target, isIntersecting: shown.includes(target) }));
		this.#callback(entries as IntersectionObserverEntry[], this as unknown as IntersectionObserver);
	}
}

/**
 * From here to the end of the test nothing is in view until the test
 * scrolls to it. The stub is dropped with the test, as every stub is.
 */
export function scriptTheScroll(): void {
	made.length = 0;
	vi.stubGlobal('IntersectionObserver', ScriptedObserver);
}

/**
 * The areas an element is being watched within now, one for each observer
 * still watching it: an observer the page has let go of watches nothing.
 */
export function areasWatching(element: Element): (Element | Document | null)[] {
	return made.filter((observer) => observer.watches(element)).map((observer) => observer.area);
}

/** The reader scrolled until these, and only these, are in view. */
export function scrollTo(...shown: Element[]): void {
	for (const observer of made) observer.report(shown);
}
