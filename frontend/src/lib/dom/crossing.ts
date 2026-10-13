/**
 * Which of the elements it watches cross a strip of a scrolling area.
 *
 * The page asks it of two strips. The band across the top of the reading
 * area: what crosses it is what may be being read (`ReadingBand`). And the
 * whole of the area: the head of a part of a story that crosses it is in
 * view, and the reader is not deep in that part yet (`ReadingParts`).
 *
 * What is watched is drawn and taken away while the area is on screen, so
 * elements are added and removed one at a time, whether or not the strip is
 * watched yet. An area gives way to another — one way of reading the review
 * to the next — and the one that goes may stop being watched after the
 * other began: stopping it leaves what the other counts alone.
 */

import { SvelteSet } from 'svelte/reactivity';

/** A strip being watched: the area it is a strip of, and what looks at it. */
interface Watch {
	area: HTMLElement;
	observer: IntersectionObserver;
}

export class Crossing {
	// The strip, as the margin that leaves it of the area
	readonly #strip: string;
	// What whoever watches does each time the strip has been looked at again; nothing, where only what crosses it is asked
	readonly #lookedAgain: (() => void) | undefined;
	// The elements crossing the strip, while it is watched
	readonly #crossing = new SvelteSet<Element>();
	// The watch of the area watched last, until it is stopped
	#underWay: Watch | null = null;

	/**
	 * @param strip the strip, as the margin that leaves it of the area it is a strip of
	 * @param lookedAgain called each time the strip has been looked at again, once what crosses it is counted
	 */
	constructor(strip: string, lookedAgain?: () => void) {
		this.#strip = strip;
		this.#lookedAgain = lookedAgain;
	}

	/** The elements crossing the strip, while it is watched. */
	get elements(): Iterable<Element> {
		return this.#crossing;
	}

	/** Whether the strip of some area is being watched. */
	get watched(): boolean {
		return this.#underWay !== null;
	}

	/** The area whose strip is being watched; null while none is. */
	get area(): HTMLElement | null {
		return this.#underWay?.area ?? null;
	}

	/** Whether an element crosses the strip. */
	has(element: Element): boolean {
		return this.#crossing.has(element);
	}

	/** Watch the strip of a scrolling area over these elements, and those added later; returns how to stop. */
	watch(root: HTMLElement, elements: Iterable<Element>): () => void {
		const observer = new IntersectionObserver((entries) => this.#looked(entries), {
			root,
			rootMargin: this.#strip,
			threshold: 0
		});
		this.#underWay = { area: root, observer };
		for (const element of elements) observer.observe(element);
		return () => this.#stop(observer);
	}

	/** An element drawn, watched along with the rest while the strip is. */
	add(element: Element): void {
		this.#underWay?.observer.observe(element);
	}

	/** An element gone, no longer watched nor counted. */
	remove(element: Element): void {
		this.#underWay?.observer.unobserve(element);
		this.#crossing.delete(element);
	}

	/** The page has just brought an element into the strip: it crosses it from now on, before the strip is looked at again. */
	countIn(element: Element): void {
		this.#crossing.add(element);
	}

	#looked(entries: IntersectionObserverEntry[]): void {
		for (const entry of entries) {
			// What the observer noted before an element was taken away still
			// arrives after it: what is no longer on the page crosses nothing
			if (entry.isIntersecting && entry.target.isConnected) this.#crossing.add(entry.target);
			else this.#crossing.delete(entry.target);
		}
		this.#lookedAgain?.();
	}

	#stop(observer: IntersectionObserver): void {
		observer.disconnect();
		if (this.#underWay?.observer !== observer) return;
		this.#underWay = null;
		this.#crossing.clear();
	}
}
