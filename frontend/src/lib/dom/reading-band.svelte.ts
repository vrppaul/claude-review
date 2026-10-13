/**
 * The band across the top of the reading area, and which section of the
 * stream is being read in it.
 *
 * A long file below the one whose header is pinned is in view too, but it
 * is not the one being read: what counts is the band at the top, and of the
 * sections crossing it, the one that comes first on the page — unless a jump
 * has just taken the reader to a section, which is then the one being read.
 */

import { Crossing } from '$lib/dom/crossing';
import { firstInDocument } from '$lib/dom/document-order';

// How far into the band a section must reach to cross it, in pixels. After a
// jump to a file, the file above it ends at the band's top edge, give or take
// a fraction of a pixel, and touching the band is not being read in it
const CROSSING_DEPTH = 1;
// The band, as a margin taken off the reading area: its top sixth or so,
// begun the crossing depth below the area's top edge
const READING_BAND = `-${CROSSING_DEPTH}px 0px -85% 0px`;

export class ReadingBand {
	// The sections crossing the band, while it is watched
	readonly #crossing = new Crossing(READING_BAND, () => this.#lookedAgain());
	// The section a jump took the reader to. It is the one being read until the
	// reader moves on from it, whatever the band says meanwhile: the band says
	// it only once the jump has landed, and not at all for a file at the end of
	// the stream, which cannot scroll up as far as the band
	#landed = $state.raw<Element | null>(null);
	// Whether the reader has come to rest since a jump landed that section:
	// what the band reports before then is the page moving them, and what it
	// reports after is the reader moving on
	#landingSettled = false;
	readonly #earliest = $derived(this.#landed ?? firstInDocument(this.#crossing.elements));

	/** The section being read: the one a jump took the reader to, or of those crossing the band, the first on the page. */
	get earliest(): Element | null {
		return this.#earliest;
	}

	/** The reading area the band is across, while it is watched; null while none is. */
	get area(): HTMLElement | null {
		return this.#crossing.area;
	}

	/** A jump is taking the reader to a section: it is the one being read from now on, until they move from it. */
	land(section: Element): void {
		this.#landed = section;
		this.#landingSettled = false;
	}

	/**
	 * The page has taken the reader as far as it was taking them, and they
	 * have come to rest: from here on, what crosses the band is the reader
	 * moving on. Said by whichever jump was the last, not only by the one
	 * that landed the section: another may have taken its place on the way.
	 */
	settle(): void {
		this.#landingSettled = true;
	}

	/** Watch the band of a scrolling area over these sections, and those added later; returns how to stop. */
	watch(root: HTMLElement, sections: Iterable<Element>): () => void {
		const stopCrossing = this.#crossing.watch(root, sections);
		return () => this.#stop(stopCrossing);
	}

	/** A section drawn, watched along with the rest while the band is. */
	add(section: Element): void {
		this.#crossing.add(section);
	}

	/** A section gone, no longer watched nor counted. */
	remove(section: Element): void {
		this.#crossing.remove(section);
		if (this.#landed === section) this.#landed = null;
	}

	/** The band has been looked at again: once the reader had come to rest where a jump took them, that is them moving on. */
	#lookedAgain(): void {
		if (this.#landingSettled) this.#landed = null;
	}

	#stop(stopCrossing: () => void): void {
		stopCrossing();
		// Where another area is watched in place of this one, the reader is still where a jump took them in it
		if (!this.#crossing.watched) this.#landed = null;
	}
}
