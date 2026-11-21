/**
 * The gesture that asks where a name is defined and used, on the lines of
 * one drawn file: Ctrl+click on a name in a line's code, Cmd+click on a Mac,
 * and the name under the pointer marked while the key is held.
 *
 * A line knows where it is, so the press is read here, beside it, and handed
 * to the lookup of the area the file is drawn in with the line's place. It
 * is offered where a comment is taken — on lines whose numbers are the
 * review's own — in an area that looks names up at all.
 */

import type { LineCommenting, DrawnFile } from '$lib/components/line-commenting.svelte';
import { holdsModifiersOf, LOOKUP_CHORD } from '$lib/components/keymap';
import type { NameLookup } from '$lib/review/name-lookup.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { DrawnLine } from '$lib/utils/drawn-file';

export class LineNaming {
	readonly #review: Review;
	readonly #lookup: NameLookup;
	readonly #file: DrawnFile;
	readonly #commenting: LineCommenting;

	/**
	 * @param review the review the file is drawn in
	 * @param lookup the lookup of the area the file is drawn in
	 * @param file the file drawn
	 * @param commenting commenting on its lines, which says where a comment is taken
	 */
	constructor(review: Review, lookup: NameLookup, file: DrawnFile, commenting: LineCommenting) {
		this.#review = review;
		this.#lookup = lookup;
		this.#file = file;
		this.#commenting = commenting;
	}

	/** The pointer moved over a line's code, or off it: the word under it is marked while the key is held. */
	point(event: MouseEvent, code: HTMLElement, drawn: DrawnLine): void {
		if (!this.#commenting.mayComment(drawn.place)) return;
		this.#lookup.point(code, event, holdsModifiersOf(LOOKUP_CHORD, event));
	}

	/**
	 * A click on a line's code: with the key held, on a word, the keyboard
	 * goes to the line's number, which the pane hands it back to as it closes,
	 * and the review is asked about the place pressed. A click without the
	 * key, or on no word, is left to the browser, as text is selected.
	 */
	press(event: MouseEvent, code: HTMLElement, drawn: DrawnLine): void {
		if (!holdsModifiersOf(LOOKUP_CHORD, event) || !this.#commenting.mayComment(drawn.place)) return;
		const pressed = this.#lookup.wordUnder(code, event.clientX, event.clientY);
		if (pressed === null) return;
		event.preventDefault();
		const path = this.#file.path();
		this.#review.sections.keyboardBackTo(path, drawn.key);
		const line = { path, side: drawn.place.side, line: drawn.place.number };
		this.#lookup.ask(line, pressed, this.#review.diff.takeOnScreen);
	}
}
