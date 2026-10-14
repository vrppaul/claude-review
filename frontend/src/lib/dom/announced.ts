/**
 * What announced itself to the page as drawn in a reading area, and which
 * of it is being read.
 *
 * The page finds nothing it draws by an id: whoever draws a section of a
 * file, or a part of a story, says where it is, by the key it knows it by,
 * and takes that back when it goes. What is said is kept here one way for
 * both: by its key, to take the reader to it; by its element, so the one
 * the band says is being read names itself; and in the band from the
 * moment it is drawn to the moment it is taken back.
 */

import { ReadingBand } from '$lib/dom/reading-band.svelte';

/** Something drawn, as it announced itself: what whoever draws it knows it by, and the element the band reads it by. */
export interface Announcement {
	key: string;
	element: HTMLElement;
}

export class Announced<Said extends Announcement> {
	// Each of them, by what whoever draws it knows it by
	readonly #byKey = new Map<string, Said>();
	// And by its element, so the one being read names itself
	readonly #byElement = new Map<Element, Said>();
	/** The band they are read in: what a jump to one of them lands it in. */
	readonly band = new ReadingBand();

	/**
	 * The one being read, while their area is watched: the one a jump took
	 * the reader to, or the first on the page of those at the top of the area.
	 */
	get beingRead(): Said | null {
		const earliest = this.band.earliest;
		return earliest === null ? null : (this.#byElement.get(earliest) ?? null);
	}

	/** Every one of them, in the order they announced themselves. */
	get all(): Said[] {
		return [...this.#byKey.values()];
	}

	/** The one known by a key, where it is drawn. */
	get(key: string): Said | undefined {
		return this.#byKey.get(key);
	}

	/** The area they are read in, while it is watched; null while none is. */
	get area(): HTMLElement | null {
		return this.band.area;
	}

	/** One of them is drawn and says so: it is read in the band with the rest. Returns how to take that back. */
	add(said: Said): () => void {
		this.#byKey.set(said.key, said);
		this.#byElement.set(said.element, said);
		this.band.add(said.element);
		return () => this.#takeBack(said);
	}

	/**
	 * Follow which of them the reader is in as they scroll an area. Those
	 * drawn later are followed as they arrive. Returns how to stop.
	 */
	watch(root: HTMLElement): () => void {
		return this.band.watch(
			root,
			this.all.map((said) => said.element)
		);
	}

	#takeBack(said: Said): void {
		this.band.remove(said.element);
		// What the band noted of it before it went may still arrive: it then names nothing being read
		this.#byElement.delete(said.element);
		// Drawn anew under its key before this was taken back, what the one drawn anew said is what the key names
		if (this.#byKey.get(said.key) === said) this.#byKey.delete(said.key);
	}
}
