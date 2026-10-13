/**
 * The story the agent told of the change, as this page holds it.
 *
 * The review holds the story, whole, and replaces it whole: the page reads
 * it as it opens and again whenever the review says another was told. It is
 * no part of the reader's draft — nothing of it is theirs to lose.
 *
 * A story is pieces of the take of the change it was told of, and stays as
 * told when the diff is taken again: the page then holds a story of one
 * take beside threads and a diff of another, and says so by whose numbers
 * the story's lines carry.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { readStory } from '$lib/api/review-api';
import { NO_PIECES, piecesOf, type StoryPieces } from '$lib/review/story-pieces';
import type { StoryHeld } from '$lib/types';

export class ReviewStory {
	/** Whether a story can be told of this review at all: the review says, the page never works it out. */
	readonly canBeTold: boolean;
	readonly #takeOnScreen: () => number;
	#held = $state.raw<StoryHeld | null>(null);
	// Laid out once for the story held, not at every question asked of them
	readonly #pieces: StoryPieces;
	// Which read is the latest. Two can be in flight — two stories told one
	// after the other — and only the latest is held, whatever order the
	// answers come back in.
	#reading = 0;

	/**
	 * @param canBeTold whether the review takes a story
	 * @param held the story it held as the page opened, if the agent had told one
	 * @param takeOnScreen which take of the review the page reads now
	 */
	constructor(canBeTold: boolean, held: StoryHeld | null, takeOnScreen: () => number) {
		this.canBeTold = canBeTold;
		this.#held = held;
		this.#takeOnScreen = takeOnScreen;
		this.#pieces = $derived(this.#held === null ? NO_PIECES : piecesOf(this.#held.story));
	}

	/** The story held, as it was told, with the round it was told in; null while the agent has told none. */
	get held(): StoryHeld | null {
		return this.#held;
	}

	/** The pieces of files the story held draws; none while no story is held. */
	get pieces(): StoryPieces {
		return this.#pieces;
	}

	/**
	 * Whose numbers the lines of the story held carry: the review's own
	 * while it was told of the take the page reads, another take's once the
	 * diff was taken again and the story was not told again. One read just
	 * before the diff it was told of lands is another take's until it does.
	 * With no story held there are no lines to carry any.
	 */
	get numbering(): StoryNumbering {
		const held = this.#held;
		return held === null || held.take === this.#takeOnScreen() ? 'the-reviews' : 'another-takes';
	}

	/** Read the story the review holds now, in place of the one held here. */
	async read(): Promise<void> {
		const mine = ++this.#reading;
		const { held } = await readStory();
		if (mine === this.#reading) this.#held = held;
	}
}
