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
 * stands. The page holds one copy of it: read with the review's facts,
 * which say how far the telling had got, and changed by what the review
 * tells after them. A story held ends it here as it does in the review,
 * though facts read before the story was told still held it. What the
 * reader is waiting on is worked out from it (`story-wait.ts`), never
 * kept. Asking and stopping are requests made here and answered there:
 * nothing of the asking changes on this page until the review says so.
 * When a story is wanted — the reader's settings, the view on screen — is
 * the review's own to join.
 *
 * A story told while the page is open may land while the reader reads the
 * files, and the page never changes the view for them: it holds how that
 * arrival stands with the reader, offered until they put the offer away,
 * unseen until whoever draws the story says they have seen it. That is the
 * page's own and lasts as long as the page: a reload opens on the story
 * held, with nothing to say of how it came.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { askForStory, readStory, stopStory } from '$lib/api/review-api';
import { storyNotAskedForNote, storyNotStoppedNote } from '$lib/review/panel-notes';
import { contentsOf, NO_CONTENTS, type StoryContents } from '$lib/review/story-contents';
import { piecesOf, type StoryPieces } from '$lib/review/story-pieces';
import { StoryProgress, type PartsRead } from '$lib/review/story-progress.svelte';
import { canBeAskedFor, waitOf, type StoryWait } from '$lib/review/story-wait';
import type { StoryAsking, StoryHeld } from '$lib/types';

/**
 * What stands where the story is read: the story the review holds, or what
 * the reader waits on while it holds none. One or the other, never both
 * and never neither, which whoever draws it reads off the kind.
 */
export type StoryOrWait = { kind: 'story'; held: StoryHeld } | { kind: 'wait'; wait: StoryWait };

/**
 * How the asking for a story stands beside the story held: a story told
 * ended it, though facts read before it was told say it stood.
 */
function askingBeside(held: StoryHeld | null, asking: StoryAsking | null): StoryAsking | null {
	return held === null ? asking : null;
}

/** What stands where the story is read, worked out from what the page holds of the story, its asking and its agent. */
function storyOrWaitOf(held: StoryHeld | null, asking: StoryAsking | null, agentAttached: boolean): StoryOrWait {
	return held === null ? { kind: 'wait', wait: waitOf(asking, agentAttached) } : { kind: 'story', held };
}

/**
 * How a story told while the page was open stands with the reader.
 *
 * `none`: no story arrived that they have not seen.
 * `offered`: one arrived, and the page offers it to them.
 * `put-away`: they put the offer away without reading the story: it is
 * unseen still, and offered no more.
 */
export type StoryArrival = 'none' | 'offered' | 'put-away';

// What putting the offer away makes of each way an arrival stands: only an offer can be put away
const OFFER_PUT_AWAY: Record<StoryArrival, StoryArrival> = {
	none: 'none',
	offered: 'put-away',
	'put-away': 'put-away'
};

/** What the story of a page opens on. */
export interface StoryOpening {
	/** Whether the review takes a story. */
	canBeTold: boolean;
	/** The story the review held as the page opened, if the agent had told one. */
	held: StoryHeld | null;
	/** How the reader's asking for a story stood, as the review's facts said it as the page opened. */
	asking: StoryAsking | null;
	/** The parts of the story the reader had read through when the page was last open in this run of the review. */
	partsRead: readonly string[];
	/** Which take of the review the page reads now. */
	takeOnScreen: () => number;
	/** Whether an agent is attached to the review now. */
	agentAttached: () => boolean;
	/** Say something in the panel, where the reader is told what a request of theirs came to. */
	sayInPanel: (words: string) => void;
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
	readonly #sayInPanel: (words: string) => void;
	#held = $state.raw<StoryHeld | null>(null);
	// How the reader's asking for a story stands, as the review last said: replaced whole, by its facts or by what it tells
	#asking = $state.raw<StoryAsking | null>(null);
	// How the story held stands with the reader, where it was told while the page was open
	#arrival = $state<StoryArrival>('none');
	// What the story lists of itself, read off its steps once for the story held
	readonly #contents: StoryContents;
	// And the pieces of what it lists, laid out once, not at every question asked of them
	readonly #pieces: StoryPieces;
	// The story held, or what the reader waits on while none is, worked out anew whenever a fact it is read off changes
	readonly #storyOrWait: StoryOrWait;
	// What the reader waits on, read off that: nothing, once a story is held
	readonly #wait: StoryWait | null;
	// Which read is the latest. Two can be in flight — two stories told one
	// after the other — and only the latest is held, whatever order the
	// answers come back in.
	#reading = 0;

	constructor({ canBeTold, held, asking, partsRead, takeOnScreen, agentAttached, sayInPanel }: StoryOpening) {
		this.canBeTold = canBeTold;
		this.#progress = new StoryProgress(partsRead);
		this.#held = held;
		this.#asking = askingBeside(held, asking);
		this.#takeOnScreen = takeOnScreen;
		this.#agentAttached = agentAttached;
		this.#sayInPanel = sayInPanel;
		this.#contents = $derived(this.#held === null ? NO_CONTENTS : contentsOf(this.#held.story));
		this.#pieces = $derived(piecesOf(this.#contents));
		this.#storyOrWait = $derived(storyOrWaitOf(this.#held, this.#asking, this.#agentAttached()));
		this.#wait = $derived(this.#storyOrWait.kind === 'wait' ? this.#storyOrWait.wait : null);
	}

	/** The story held, as it was told, with the round it was told in; null while the agent has told none. */
	get held(): StoryHeld | null {
		return this.#held;
	}

	/** What stands where the story is read: the story held, or what the reader waits on while none is. */
	get storyOrWait(): StoryOrWait {
		return this.#storyOrWait;
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
	 * How the story held stands with the reader, where it was told while
	 * this page was open: offered to them, unseen with the offer put away,
	 * or neither once they have been shown it.
	 */
	get arrival(): StoryArrival {
		return this.#arrival;
	}

	/** The reader put the offer of the story away without reading it: it is unseen still. */
	putOfferAway(): void {
		this.#arrival = OFFER_PUT_AWAY[this.#arrival];
	}

	/** The reader has been shown the story held: said by whoever draws it. */
	seen(): void {
		this.#arrival = 'none';
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
	 */
	async read(): Promise<void> {
		const mine = ++this.#reading;
		const { held } = await readStory();
		if (mine === this.#reading) this.#hold(held);
	}

	/** Take in how the asking for a story stands, as the review's facts say it or the review tells it after them. */
	learnAsking(asking: StoryAsking | null): void {
		this.#asking = asking;
	}

	/**
	 * Whether a story can be asked for now: one can be told of this review,
	 * none is held and none is on its way. One the reader stopped can be.
	 */
	get canBeAskedFor(): boolean {
		return this.canBeTold && canBeAskedFor(this.#wait);
	}

	/**
	 * Ask the agent for a story of this review. How the asking then stands
	 * is the review's to say, to this page as to every other, and nothing is
	 * held of it here until it does; a request that fails is said in the
	 * panel.
	 */
	async askFor(): Promise<void> {
		try {
			await askForStory();
		} catch (error) {
			this.#sayInPanel(storyNotAskedForNote(error));
		}
	}

	/** Stop the story the reader asked for; a request that fails is said in the panel. */
	async stop(): Promise<void> {
		try {
			await stopStory();
		} catch (error) {
			this.#sayInPanel(storyNotStoppedNote(error));
		}
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
	 * Hold the story the review answered with. Where it is another the
	 * review was told, nothing of it is read yet, and it is offered to the
	 * reader, who has not seen it.
	 */
	#hold(held: StoryHeld | null): void {
		this.#held = held;
		this.#asking = askingBeside(held, this.#asking);
		if (!this.#anotherAwaited) return;
		this.#anotherAwaited = false;
		this.#progress.forget();
		this.#arrival = held === null ? 'none' : 'offered';
	}
}
