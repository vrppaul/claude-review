/**
 * The names outside the change that hold what the tree's filter was typed,
 * as the review said them: asked once the reader pauses typing, so what is
 * typed on the way to a name is never asked, and handed out only for the
 * diff on screen.
 */

import { readNamesFound } from '$lib/api/review-api';
import type { DiffReading, ReviewDiff } from '$lib/review/review-diff.svelte';
import type { NameDefined } from '$lib/types';

// How long the reader pauses typing before the names are asked
const ASKED_AFTER_PAUSE_MS = 200;

/** What the review said of a text: the names it lists, and how many more hold the text. */
export interface FoundOutside {
	names: readonly NameDefined[];
	more: number;
	/**
	 * Whether these are every name that answers: said of this very text, or held from a shorter one it narrows, of
	 * which every name was listed. While not, none listed proves nothing.
	 */
	whole: boolean;
}

/** What was asked: a text, of one reading of the diff. */
interface Asking {
	reading: DiffReading;
	text: string;
}

/** What the review said of what was asked. */
interface Said extends Asking {
	found: FoundOutside;
}

// What a text nothing was asked of finds, and what a read that failed leaves: nothing is drawn of either
const NOTHING_FOUND: FoundOutside = { names: [], more: 0, whole: true };
// What a text has before the review said anything of the diff on screen
const NOTHING_SAID_YET: FoundOutside = { names: [], more: 0, whole: false };

/** What calls off an asking never begun: an empty text is not asked. */
function nothingToCallOff(): void {}

export class NamesOutside {
	readonly #diff: ReviewDiff;
	#said = $state.raw<Said | null>(null);
	// The last asked: an answer to any other is of a text or a diff no longer on screen
	#asked: Asking | null = null;

	/** @param diff the diff on screen, whose reading the names are asked of and handed out with */
	constructor(diff: ReviewDiff) {
		this.#diff = diff;
	}

	/**
	 * Ask for the names holding a text once the reader pauses, nothing for an empty one. Hands back what calls the
	 * asking off: whoever seeks calls it as the text, or the diff on screen, changes before the pause is over.
	 */
	seek(text: string): () => void {
		const reading = this.#diff.reading;
		if (text === '') return nothingToCallOff;
		const pause = setTimeout(() => void this.#ask({ reading, text }), ASKED_AFTER_PAUSE_MS);
		return () => clearTimeout(pause);
	}

	/**
	 * What the review said of a text in the diff on screen. While its answer is on its way, the names it said of the
	 * last text it answered that hold this one too, none counted past them: each is a true answer, and none blinks
	 * away as the reader types. Nothing for an empty text, or before anything was said of this diff.
	 */
	of(text: string): FoundOutside {
		const said = this.#said;
		if (text === '') return NOTHING_FOUND;
		if (said?.reading !== this.#diff.reading) return NOTHING_SAID_YET;
		if (said.text === text) return said.found;
		// More typed only narrows what answered: where every name was listed, those still answering are all there are
		const narrowed = text.includes(said.text) && said.found.whole && said.found.more === 0;
		// Lower-cased, as the text sought is and as the review matches it
		const names = said.found.names.filter((name) => name.name.toLowerCase().includes(text));
		return { names, more: 0, whole: narrowed };
	}

	async #ask(asking: Asking): Promise<void> {
		this.#asked = asking;
		let found: FoundOutside;
		try {
			const answer = await readNamesFound(asking.reading.asked, asking.text);
			// Read once a retake had landed: of a take the diff on screen is not, and the new diff on its way
			if (answer.take !== asking.reading.take) return;
			found = { names: answer.names, more: answer.more, whole: true };
		} catch {
			// Nothing is drawn of names that could not be found: the tree stands alone, as for a text none holds
			found = NOTHING_FOUND;
		}
		if (this.#asked === asking) this.#said = { ...asking, found };
	}
}
