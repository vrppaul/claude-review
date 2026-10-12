/**
 * The story the agent told of the change, as this page holds it.
 *
 * The review holds the story, whole, and replaces it whole: the page reads
 * it as it opens and again whenever the review says another was told. It is
 * no part of the reader's draft — nothing of it is theirs to lose.
 */

import { readStory } from '$lib/api/review-api';
import type { StoryHeld } from '$lib/types';

export class ReviewStory {
	/** Whether a story can be told of this review at all: the review says, the page never works it out. */
	readonly canBeTold: boolean;
	#held = $state.raw<StoryHeld | null>(null);
	// Which read is the latest. Two can be in flight — two stories told one
	// after the other — and only the latest is held, whatever order the
	// answers come back in.
	#reading = 0;

	/**
	 * @param canBeTold whether the review takes a story
	 * @param held the story it held as the page opened, if the agent had told one
	 */
	constructor(canBeTold: boolean, held: StoryHeld | null) {
		this.canBeTold = canBeTold;
		this.#held = held;
	}

	/** The story held, as it was told, with the round it was told in; null while the agent has told none. */
	get held(): StoryHeld | null {
		return this.#held;
	}

	/** Read the story the review holds now, in place of the one held here. */
	async read(): Promise<void> {
		const mine = ++this.#reading;
		const { held } = await readStory();
		if (mine === this.#reading) this.#held = held;
	}
}
