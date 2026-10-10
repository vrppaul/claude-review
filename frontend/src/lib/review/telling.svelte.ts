/**
 * How far the server's telling has got for this page, held two ways.
 *
 * - Heard: the last push this page's socket handed over. Every socket the
 *   page opens goes on from here, so nothing is handed over twice and
 *   nothing is skipped; and it is kept with the draft, since everything the
 *   pushes up to it added to the draft is in it.
 * - Read: the last push whose effect on the review's facts — its diff, its
 *   agent, its round — the page holds, whether it took the push in or read
 *   the facts after it. A push at or before it has nothing left to change
 *   there.
 *
 * A page opening from a draft goes on from where the draft left off when
 * that is before its facts: what was said in between still belongs in the
 * draft, though the facts hold it already.
 */

import type { TellingPosition } from '$lib/types';

/** A push as it reaches the review: where it stands, and whether the facts read hold it already. */
export interface HeardPush {
	at: TellingPosition;
	factsHoldIt: boolean;
}

/**
 * Whether a position comes after another in the same run of the review.
 * Each run numbers its pushes afresh, so positions in different runs are
 * never compared.
 */
function comesAfter(position: TellingPosition, other: TellingPosition): boolean {
	return position.instance === other.instance && position.sequence > other.sequence;
}

/** Where a review opening goes on from: where its draft left off, if that is earlier than its facts. */
function startingPosition(facts: TellingPosition, told: TellingPosition | null): TellingPosition {
	return told !== null && comesAfter(facts, told) ? told : facts;
}

export class Telling {
	#heard: TellingPosition;
	#read: TellingPosition;

	/**
	 * @param facts how far the telling had got when the review's facts were read
	 * @param told how far it had got for the draft the review opened from, if it opened from one
	 */
	constructor(facts: TellingPosition, told: TellingPosition | null) {
		this.#heard = $state(startingPosition(facts, told));
		this.#read = facts;
	}

	/** The last push this page's socket handed over: where the next socket goes on from. */
	get heard(): TellingPosition {
		return this.#heard;
	}

	/** Note that a push has arrived. Null when this page's socket handed it over before. */
	hear(at: TellingPosition): HeardPush | null {
		if (!comesAfter(at, this.#heard)) return null;
		this.#heard = at;
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
	}
}
