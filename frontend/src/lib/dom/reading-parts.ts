/**
 * Which part of a story the reader is in — its overview, a chapter, what it
 * leaves out — and taking them to one.
 *
 * A part is more than the sections inside it. A chapter's head, why its
 * changes belong together and where to doubt them draw no line of a file,
 * and the overview draws none at all: while those are at the top of the
 * reading area no section is being read, and no section stands for a
 * chapter's head to take the reader to. So the parts announce themselves
 * here, as sections do to `FileSections`, and are read by a band of their
 * own. A band apart, because a chapter holds its steps: read among them, the
 * chapter, which comes first on the page, would always be the one read.
 */

import type { Jumps } from '$lib/dom/jump';
import { ReadingBand } from '$lib/dom/reading-band.svelte';

export class ReadingParts {
	// Where every part on the page is, by what whoever draws it knows it by
	readonly #parts = new Map<string, HTMLElement>();
	// The part each element is, so the one being read names itself
	readonly #keys = new Map<Element, string>();
	// Which part the reader is in, while the reading area is watched
	readonly #band = new ReadingBand();
	// Where the page is taking the reader: one jump at a time, shared with whatever else takes them somewhere
	readonly #jumps: Jumps;

	/** @param jumps where the page is taking the reader, one place at a time */
	constructor(jumps: Jumps) {
		this.#jumps = jumps;
	}

	/**
	 * The part the reader is in, by its key: the one the page took them to,
	 * or the first on the page of those at the top of the reading area.
	 * None while the area is not watched, or no part is at its top.
	 */
	get beingRead(): string | null {
		const read = this.#band.earliest;
		return read === null ? null : (this.#keys.get(read) ?? null);
	}

	/** Say where a part is, by the key whoever draws it knows it by. Returns how to take it back. */
	register(key: string, element: HTMLElement): () => void {
		this.#parts.set(key, element);
		this.#keys.set(element, key);
		this.#band.add(element);
		return () => this.#unregister(key, element);
	}

	/**
	 * Follow which part the reader is in as they scroll an area. Parts drawn
	 * later are watched as they arrive. Returns how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		return this.#band.watch(root, this.#parts.values());
	}

	/**
	 * Take the reader to a part: its head to the top at once, and the part
	 * the one being read. Nowhere, for a part that is not drawn.
	 */
	goTo(key: string): void {
		const part = this.#parts.get(key);
		if (part) this.#jumps.land(this.#band, part, 'instant');
	}

	#unregister(key: string, element: HTMLElement): void {
		this.#band.remove(element);
		this.#keys.delete(element);
		if (this.#parts.get(key) === element) this.#parts.delete(key);
	}
}
