/**
 * The band across the top of the reading area, and which section of the
 * stream is being read in it.
 *
 * A long file below the one whose header is pinned is in view too, but it
 * is not the one being read: what counts is the band at the top, and of the
 * sections crossing it, the one that comes first on the page.
 */

import { SvelteSet } from 'svelte/reactivity';

// The band, as a margin taken off the reading area: its top sixth or so
const READING_BAND = '0px 0px -85% 0px';

export class ReadingBand {
	// The sections crossing the band, while it is watched
	readonly #crossing = new SvelteSet<Element>();
	readonly #earliest = $derived(firstInDocument(this.#crossing));
	#observer: IntersectionObserver | null = null;

	/** The section being read: of those crossing the band, the first on the page. */
	get earliest(): Element | null {
		return this.#earliest;
	}

	/** Watch the band of a scrolling area over these sections, and those added later; returns how to stop. */
	watch(root: HTMLElement, sections: Iterable<Element>): () => void {
		const observer = new IntersectionObserver((entries) => this.#crossed(entries), {
			root,
			rootMargin: READING_BAND,
			threshold: 0
		});
		this.#observer = observer;
		for (const section of sections) observer.observe(section);
		return () => this.#stop(observer);
	}

	/** A section drawn, watched along with the rest while the band is. */
	add(section: Element): void {
		this.#observer?.observe(section);
	}

	/** A section gone, no longer watched nor counted. */
	remove(section: Element): void {
		this.#observer?.unobserve(section);
		this.#crossing.delete(section);
	}

	#crossed(entries: IntersectionObserverEntry[]): void {
		for (const entry of entries) {
			// What the observer noted before a section was taken away still
			// arrives after it: a section no longer on the page is not read
			if (entry.isIntersecting && entry.target.isConnected) this.#crossing.add(entry.target);
			else this.#crossing.delete(entry.target);
		}
	}

	#stop(observer: IntersectionObserver): void {
		observer.disconnect();
		if (this.#observer !== observer) return;
		this.#observer = null;
		this.#crossing.clear();
	}
}

/** Of some elements, the one that comes first in the document; null of none. */
function firstInDocument(elements: Iterable<Element>): Element | null {
	let first: Element | null = null;
	for (const element of elements) {
		if (first === null || comesBefore(element, first)) first = element;
	}
	return first;
}

function comesBefore(element: Element, other: Element): boolean {
	return (element.compareDocumentPosition(other) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}
