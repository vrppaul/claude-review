/**
 * How far the server's telling has got for this page, held three ways.
 *
 * - Heard: the last push this page's own socket handed over. Every socket
 *   the page opens goes on from here, so nothing is handed over twice and
 *   nothing is skipped.
 * - Read: the last push whose effect on the review's facts — its diff, its
 *   agent, its round — the page holds, whether it took the push in or read
 *   the facts after it. A push at or before it has nothing left to change
 *   there.
 * - Kept: in each run of the review, the last push whose effect on the
 *   draft the draft holds, this page's or another tab's taken in with it.
 *   Kept with the draft, so a page opening from it is handed what came
 *   after.
 *
 * What a push adds to the draft — an answer, a raised thread, a note — is
 * kept once however often it arrives, so a page may be handed a push whose
 * effect another tab's draft already brought it.
 */

import type { Draft } from '$lib/drafts/draft-shapes';
import type { ReviewResponse, TellingByRun, TellingPosition } from '$lib/types';
import { comesAfter, countedIn, furtherByRun } from '$lib/utils/telling';

/** A push as it reaches the review: where it stands, and whether the facts read hold it already. */
export interface HeardPush {
	at: TellingPosition;
	factsHoldIt: boolean;
}

/**
 * Where a review opening takes up the telling: where its draft left off,
 * if that is earlier than its facts — what was said in between is handed
 * over for the draft — and otherwise where its facts were read.
 */
function startingPosition(facts: TellingPosition, kept: TellingByRun): TellingPosition {
	const keptHere = kept[facts.instance];
	return keptHere === undefined || keptHere >= facts.sequence ? facts : { ...facts, sequence: keptHere };
}

export class Telling {
	#heard: TellingPosition;
	#read: TellingPosition;
	#kept: TellingByRun;

	/**
	 * @param facts what the server said the review is, and how far its telling had got
	 * @param draft an unsent review of the same thing, and how far its telling had got
	 */
	constructor(facts: ReviewResponse, draft: Draft | null) {
		const read = { instance: facts.instance, sequence: facts.sequence };
		const kept = draft?.told ?? {};
		this.#heard = startingPosition(read, kept);
		this.#read = read;
		this.#kept = $state(kept);
	}

	/** The last push this page's socket handed over: where the next socket goes on from. */
	get heard(): TellingPosition {
		return this.#heard;
	}

	/** How far the draft's effects go, in each run of the review: what the draft keeps. */
	get kept(): TellingByRun {
		return this.#kept;
	}

	/** Note that a push has arrived. Null when this page's socket handed it over before. */
	hear(at: TellingPosition): HeardPush | null {
		if (!comesAfter(at, this.#heard)) return null;
		this.#heard = at;
		this.#kept = countedIn(this.#kept, at);
		const factsHoldIt = !comesAfter(at, this.#read);
		if (!factsHoldIt) this.#read = at;
		return { at, factsHoldIt };
	}

	/**
	 * Take the telling up again where it goes on after a gap: what was said
	 * in between could not be handed over, and the facts are read again.
	 */
	continueFrom(at: TellingPosition): void {
		this.#heard = at;
		this.#read = at;
		this.#kept = countedIn(this.#kept, at);
	}

	/** Take in how far another tab's draft had got: what it holds is in this draft now too. */
	adopt(kept: TellingByRun): void {
		this.#kept = furtherByRun(this.#kept, kept);
	}
}
