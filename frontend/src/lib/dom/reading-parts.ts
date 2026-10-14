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
 *
 * A part says where its head is too. The reader is deep in the part they
 * read once that head has left the reading area: nothing on screen then
 * says which part it is, unless the page does.
 */

import { Announced, type Announcement } from '$lib/dom/announced';
import { Crossing } from '$lib/dom/crossing';
import type { Jumps } from '$lib/dom/jump';
import { lendKeyboardToWhatRemains } from '$lib/dom/keyboard';

/** A part as it announced itself: what whoever draws it knows it by, the whole of it, which the band reads it by, and its head. */
interface Part extends Announcement {
	head: HTMLElement;
}

// The whole of the reading area, as a strip of it: nothing is taken off its edges
const THE_WHOLE_AREA = '0px';

export class ReadingParts {
	// Every part on the page, and which of them the reader is in, while the reading area is watched
	readonly #parts = new Announced<Part>();
	// The heads in view anywhere in the reading area, while it is watched
	readonly #headsInView = new Crossing(THE_WHOLE_AREA);
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
		return this.#parts.beingRead?.key ?? null;
	}

	/**
	 * The part the reader is deep in, by its key: the one being read, once
	 * its head has left the reading area. None while that head is in view.
	 */
	get deepIn(): string | null {
		const read = this.#parts.beingRead;
		return read === null || this.#headsInView.has(read.head) ? null : read.key;
	}

	/**
	 * Say where a part is, the whole of it and its head, by the key whoever
	 * draws it knows it by. Returns how to take it back.
	 */
	register(key: string, whole: HTMLElement, head: HTMLElement): () => void {
		const takeBackPart = this.#parts.add({ key, element: whole, head });
		this.#headsInView.add(head);
		return () => this.#unregister(takeBackPart, head);
	}

	/**
	 * Follow which part the reader is in as they scroll an area, and which
	 * heads are in view in it. Parts drawn later are watched as they arrive.
	 * Returns how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		const stopParts = this.#parts.watch(root);
		const stopHeads = this.#headsInView.watch(
			root,
			this.#parts.all.map((part) => part.head)
		);
		return () => this.#stopWatching(stopParts, stopHeads);
	}

	/**
	 * Take the reader to a part: its head to the top at once, and the part
	 * the one being read, which they are not deep in. Nowhere, for a part
	 * that is not drawn.
	 */
	goTo(key: string): void {
		const part = this.#parts.get(key);
		if (!part) return;
		// Where the reader is taken is its head: in view from now on, before what watches the heads has looked again
		this.#headsInView.countIn(part.head);
		this.#jumps.land(this.#parts.band, part.element, 'instant');
	}

	/**
	 * Put the keyboard on the head of the part being read, if what had it
	 * went: a bar over the part that is drawn only while the reader is deep
	 * in it. The head is where the bar's own buttons take the reader, and
	 * the next key starts from it; it is words, so it holds the keyboard
	 * only until the keyboard leaves it.
	 */
	keyboardToBeingRead(): void {
		lendKeyboardToWhatRemains(() => this.#parts.beingRead?.head);
	}

	/**
	 * Put the keyboard on the head of a part, by its key, if what had it
	 * went: the part a story begins with, as the story takes the place of
	 * what stood there until it was told. No part is being read yet at that
	 * moment, so the part is named. Its head holds the keyboard as the head
	 * of the part being read does; nothing does, for a part that is not drawn.
	 */
	keyboardToHeadOf(key: string): void {
		lendKeyboardToWhatRemains(() => this.#parts.get(key)?.head);
	}

	#stopWatching(stopParts: () => void, stopHeads: () => void): void {
		stopParts();
		stopHeads();
	}

	#unregister(takeBackPart: () => void, head: HTMLElement): void {
		takeBackPart();
		this.#headsInView.remove(head);
	}
}
