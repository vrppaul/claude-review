/**
 * How far the review's telling has got for this page: which run of the
 * review, and the last push taken in.
 *
 * Kept with the draft. A push already in it — taken in before a reload, or
 * by another tab whose draft this one took in — is then not taken in again
 * when the server hands it over, and the page's socket goes on from here
 * whenever it connects.
 */

import type { Draft } from '$lib/drafts/draft-shapes';
import type { ReviewResponse, TellingPosition } from '$lib/types';
import { comesAfter, laterPosition } from '$lib/utils/telling';

/**
 * Where a review opening takes up the telling: where its draft left off, if
 * the draft is of this run of the review — what was said while the page was
 * away is then handed over — and otherwise where its facts were read.
 */
function startingPosition(facts: ReviewResponse, draft: Draft | null): TellingPosition {
	if (draft?.told && draft.told.instance === facts.instance) return draft.told;
	return { instance: facts.instance, sequence: facts.sequence };
}

export class Telling {
	#position: TellingPosition;

	/**
	 * @param facts what the server said the review is, and how far its telling had got
	 * @param draft an unsent review of the same thing, and how far it had got
	 */
	constructor(facts: ReviewResponse, draft: Draft | null) {
		this.#position = $state(startingPosition(facts, draft));
	}

	/** The last push taken in. */
	get position(): TellingPosition {
		return this.#position;
	}

	/** Note that a push has arrived. False when it was taken in already, so it is not taken in twice. */
	hear(at: TellingPosition): boolean {
		if (!comesAfter(at, this.#position)) return false;
		this.#position = at;
		return true;
	}

	/**
	 * Take the telling up again where it goes on after a gap: what was said
	 * in between could not be handed over.
	 */
	continueFrom(at: TellingPosition): void {
		this.#position = at;
	}

	/** Take in how far another tab's draft had got: what it holds is not taken in again. */
	adopt(kept: TellingPosition | null): void {
		this.#position = laterPosition(this.#position, kept);
	}
}
