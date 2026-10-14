/**
 * The story the agent told of the change, as this page holds it.
 *
 * The review holds the story, whole, and replaces it whole: the page reads
 * it as it opens and again whenever the review says another was told. It is
 * no part of the reader's draft — nothing of it is theirs to lose. How far
 * they have got through it is theirs, and the draft keeps it: `progress`.
 * It is of the story held: once the review has said it was told another,
 * what was read is forgotten the moment that one is held here, whichever
 * read brings it, and stands with the story before until then.
 *
 * A story is pieces of the take of the change it was told of, and stays as
 * told when the diff is taken again: the page then holds a story of one
 * take beside threads and a diff of another, and says so by whose numbers
 * the story's lines carry.
 *
 * The reader may ask for a story, and the review holds how that asking
 * stands. The page holds one copy of it, beside the story that ends it:
 * both come in one answer when the story is read, and the review tells
 * each change of the asking in between. What the reader is waiting on is
 * worked out from it (`story-wait.ts`), never kept.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { readStory } from '$lib/api/review-api';
import { contentsOf, NO_CONTENTS, type StoryContents } from '$lib/review/story-contents';
import { piecesOf, type StoryPieces } from '$lib/review/story-pieces';
import { StoryProgress, type PartsRead } from '$lib/review/story-progress.svelte';
import { waitOf, type StoryWait } from '$lib/review/story-wait';
import type { StoryAsking, StoryHeld, StoryResponse } from '$lib/types';

/** What the story of a page opens on. */
export interface StoryOpening {
	/** Whether the review takes a story. */
	canBeTold: boolean;
	/** The story the review held as the page opened, if the agent had told one, and how the asking for one stood. */
	standing: StoryResponse;
	/** The parts of the story the reader had read through when the page was last open in this run of the review. */
	partsRead: readonly string[];
	/** Which take of the review the page reads now. */
	takeOnScreen: () => number;
	/** Whether an agent is attached to the review now. */
	agentAttached: () => boolean;
}

export class ReviewStory {
	/** Whether a story can be told of this review at all: the review says, the page never works it out. */
	readonly canBeTold: boolean;
	// How far the reader has got through the story held. Forgotten only here, as another story is held
	readonly #progress: StoryProgress;
	// The review said it was told another story, and that one is not held here yet: one that could not
	// be read, or is on its way. Whichever read holds it, what was read was of the story before
	#anotherAwaited = false;
	readonly #takeOnScreen: () => number;
	readonly #agentAttached: () => boolean;
	#held = $state.raw<StoryHeld | null>(null);
	// How the reader's asking for a story stands, as the review last said: replaced whole, by a read or by what it tells
	#asking = $state.raw<StoryAsking | null>(null);
	// What the story lists of itself, read off its steps once for the story held
	readonly #contents: StoryContents;
	// And the pieces of what it lists, laid out once, not at every question asked of them
	readonly #pieces: StoryPieces;
	// What the reader is waiting on while no story is held, worked out anew whenever a fact it is read off changes
	readonly #wait: StoryWait | null;
	// Which read is the latest. Two can be in flight — two stories told one
	// after the other — and only the latest is held, whatever order the
	// answers come back in.
	#reading = 0;

	constructor({ canBeTold, standing, partsRead, takeOnScreen, agentAttached }: StoryOpening) {
		this.canBeTold = canBeTold;
		this.#progress = new StoryProgress(partsRead);
		this.#held = standing.held;
		this.#asking = standing.asking;
		this.#takeOnScreen = takeOnScreen;
		this.#agentAttached = agentAttached;
		this.#contents = $derived(this.#held === null ? NO_CONTENTS : contentsOf(this.#held.story));
		this.#pieces = $derived(piecesOf(this.#contents));
		this.#wait = $derived(this.#held === null ? waitOf(this.#asking, this.#agentAttached()) : null);
	}

	/** The story held, as it was told, with the round it was told in; null while the agent has told none. */
	get held(): StoryHeld | null {
		return this.#held;
	}

	/**
	 * What the reader is waiting on while no story is held: one not asked
	 * for, one being written, an agent to attach, or nothing more once they
	 * stopped it. Null once a story is held: there is nothing to wait for.
	 */
	get wait(): StoryWait | null {
		return this.#wait;
	}

	/**
	 * How far the reader has got through the story held: which of its parts
	 * they have read through, asked and said by whoever draws a part, and
	 * kept by the draft. That it is of the story held is kept here alone.
	 */
	get progress(): PartsRead {
		return this.#progress;
	}

	/** The pieces of files the story held draws; none while no story is held. */
	get pieces(): StoryPieces {
		return this.#pieces;
	}

	/**
	 * What the story held lists of itself: its chapters, each with its files
	 * and steps, and what it leaves out; nothing while no story is held.
	 */
	get contents(): StoryContents {
		return this.#contents;
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

	/**
	 * Read the story the review holds now, in place of the one held here: the
	 * page was away, and reads again what it may have missed. For all it
	 * knows the story is the one it held, and what was read of it stands.
	 * How the asking for one stands comes in the same answer.
	 */
	async read(): Promise<void> {
		const mine = ++this.#reading;
		const standing = await readStory();
		if (mine === this.#reading) this.#hold(standing);
	}

	/** Take in how the asking for a story stands now, as the review tells it between two reads of the story. */
	learnAsking(asking: StoryAsking): void {
		this.#asking = asking;
	}

	/**
	 * The review said it was told another story: read it in place of the one
	 * held here. What the reader had read through was of the story before,
	 * and is forgotten as this one is held. A story that cannot be read
	 * leaves the one before as it was, and as far read.
	 */
	async readAnother(): Promise<void> {
		this.#anotherAwaited = true;
		await this.read();
	}

	/**
	 * The review said it was told another story, and the one held here is
	 * that story: the page read it as it opened. What the draft brought as
	 * read through was read of the story before.
	 */
	heldIsAnother(): void {
		this.#progress.forget();
	}

	/**
	 * Hold what the review answered of its story: the story, and how the
	 * asking for one stands. Where the story is another the review was told,
	 * nothing of it is read yet.
	 */
	#hold({ held, asking }: StoryResponse): void {
		this.#held = held;
		this.#asking = asking;
		if (!this.#anotherAwaited) return;
		this.#anotherAwaited = false;
		this.#progress.forget();
	}
}
