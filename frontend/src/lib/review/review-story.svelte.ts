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
 * A story is pieces of one take of the change. When the diff is taken
 * again the review follows the story onto the new take, and the page reads
 * the two together, holding neither until both are read (`Review`). It
 * holds a story only beside the diff of its take: a story read of another
 * take, and one that cannot be read with the diff taken again, leave none
 * held, until the diff of its take is read with it. Reads are taken in one
 * at a time by the review, so the last read is the last held.
 *
 * Its diagram is drawn once and kept as long as the review: drawing it
 * takes mermaid a moment, and the story drawn again each time it comes on
 * screen would grow under the reader as it did.
 *
 * The reader may ask for a story, and the review holds how that asking
 * stands. The page holds one copy of it: read with the review's facts,
 * which say how far the telling had got, and replaced by whatever the
 * review tells of it after them, the end a story told brings too. What the
 * reader is waiting on while no story held is current — none is held, or a
 * round moved the code on under it — is worked out from it
 * (`story-wait.ts`), never kept. Asking and stopping are requests made here
 * and answered there: nothing of the asking changes on this page until the
 * review says so. When a story is wanted — the reader's settings, the view
 * on screen — is the review's own to join.
 *
 * A story told while the page is open may land while the reader reads the
 * files, and the page never changes the view for them: it holds how that
 * arrival stands with the reader, offered until they put the offer away,
 * unseen until whoever draws the story says they have seen it. That is the
 * page's own and lasts as long as the page: a reload opens on the story
 * held, with nothing to say of how it came.
 */

import { askForStory, readStory, stopStory } from '$lib/api/review-api';
import type { Drawing } from '$lib/dom/diagram';
import { storyNotAskedForNote, storyNotReadNote, storyNotStoppedNote } from '$lib/review/panel-notes';
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

/** The story's diagram drawn from one source: the drawing once mermaid has drawn it, and until then the drawing on its way. */
interface DiagramDrawn {
	source: string;
	drawing: Drawing | Promise<Drawing>;
}

/** Draw the story's diagram from a source, keeping the drawing itself in place of its promise once it is drawn. */
function drawnFrom(source: string, draw: (source: string) => Promise<Drawing>): DiagramDrawn {
	const onItsWay = draw(source);
	const drawn: DiagramDrawn = { source, drawing: onItsWay };
	void onItsWay.then((drawing) => (drawn.drawing = drawing));
	return drawn;
}

/** What stands where the story is read: the story held, or what the reader waits on while none is. */
function storyOrWaitOf(held: StoryHeld | null, wait: StoryWait): StoryOrWait {
	return held === null ? { kind: 'wait', wait } : { kind: 'story', held };
}

/** Whether a story is held that is current: told of the code under review, which no round moved on since. */
function isCurrent(held: StoryHeld | null): boolean {
	return held !== null && held.moved_on === null;
}

/** Whether what the review answered of its story is of the take the page reads: no story at all goes with any. */
function isOfTake(held: StoryHeld | null, take: number): boolean {
	return held === null || held.take === take;
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
	/** Say something in the panel, where the reader is told what a request of theirs, or of the page's, came to. */
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
	// What the reader waits on while no story held is current, worked out anew whenever the asking or its agent changes
	readonly #askingWait: StoryWait;
	// The story held, or what the reader waits on while none is
	readonly #storyOrWait: StoryOrWait;
	// What the reader waits on: nothing while the story held is current
	readonly #wait: StoryWait | null;
	// The story's diagram as drawn, kept as long as the review: the story coming on screen again draws it no more
	#diagram: DiagramDrawn | null = null;

	constructor({ canBeTold, held, asking, partsRead, takeOnScreen, agentAttached, sayInPanel }: StoryOpening) {
		this.canBeTold = canBeTold;
		this.#progress = new StoryProgress(partsRead);
		// Read beside the diff as the page opened, it may straddle a retake: then the retake brings both
		this.#held = isOfTake(held, takeOnScreen()) ? held : null;
		this.#asking = asking;
		this.#takeOnScreen = takeOnScreen;
		this.#agentAttached = agentAttached;
		this.#sayInPanel = sayInPanel;
		this.#contents = $derived(this.#held === null ? NO_CONTENTS : contentsOf(this.#held.story));
		this.#pieces = $derived(piecesOf(this.#contents));
		this.#askingWait = $derived(waitOf(this.#asking, this.#agentAttached()));
		this.#storyOrWait = $derived(storyOrWaitOf(this.#held, this.#askingWait));
		this.#wait = $derived(isCurrent(this.#held) ? null : this.#askingWait);
	}

	/** The story held, on a take of the change, with the round it was told in; null while the agent has told none. */
	get held(): StoryHeld | null {
		return this.#held;
	}

	/** What stands where the story is read: the story held, or what the reader waits on while none is. */
	get storyOrWait(): StoryOrWait {
		return this.#storyOrWait;
	}

	/**
	 * What the reader is waiting on while no story held is current — none is
	 * held, or a round moved the code on under it: one not asked for, one
	 * being written, an agent to attach, or nothing more once they stopped
	 * it. Null while the story held is current: there is nothing to wait for.
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
	 * The story's diagram drawn from a source, drawn once, as whoever draws
	 * it first draws it: the drawing itself once mermaid has drawn it, so the
	 * story comes back on screen with it standing drawn, and until then the
	 * drawing on its way. A source of another diagram is drawn in its place.
	 */
	diagramDrawn(source: string, draw: (source: string) => Promise<Drawing>): Drawing | Promise<Drawing> {
		if (this.#diagram?.source !== source) this.#diagram = drawnFrom(source, draw);
		return this.#diagram.drawing;
	}

	/**
	 * Read the story the review holds now, in place of the one held here,
	 * and return how to hold it: whoever reads it with the diff holds both
	 * once both are read. For all the page knows the story is the one it
	 * held, and what was read of it stands. One that cannot be read is said
	 * in the panel, and none is held: the one held here is of the take
	 * before. A review that takes no story is not asked, and holds none.
	 */
	async read(): Promise<() => void> {
		if (!this.canBeTold) return () => this.#holdNone();
		try {
			const { held } = await readStory();
			return () => this.#hold(held);
		} catch (error) {
			this.#sayInPanel(storyNotReadNote(error));
			return () => this.#holdNone();
		}
	}

	/** Take in how the asking for a story stands, as the review's facts say it or the review tells it after them. */
	learnAsking(asking: StoryAsking | null): void {
		this.#asking = asking;
	}

	/**
	 * Whether a story can be asked for now: one can be told of this review,
	 * no story held is current and none is on its way. One the reader
	 * stopped can be.
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
	 * and is forgotten as this one is held. A story that cannot be read is
	 * said in the panel, and leaves the one before as it was, and as far
	 * read: it is of the take on screen still. That the telling ended the
	 * asking for one the review says next, as it says any change to the
	 * asking.
	 */
	async readAnother(): Promise<void> {
		this.#anotherAwaited = true;
		try {
			const { held } = await readStory();
			this.#hold(held);
		} catch (error) {
			this.#sayInPanel(storyNotReadNote(error));
		}
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
	 * reader, who has not seen it. One of a take the page has not taken in
	 * — the review took the diff again between this read and the diff's —
	 * is held with that take's diff, which the review is on its way to
	 * hand over: none is held until then.
	 */
	#hold(held: StoryHeld | null): void {
		if (!isOfTake(held, this.#takeOnScreen())) {
			this.#holdNone();
			return;
		}
		this.#held = held;
		if (!this.#anotherAwaited) return;
		this.#anotherAwaited = false;
		this.#progress.forget();
		this.#arrival = held === null ? 'none' : 'offered';
	}

	/**
	 * Hold no story, where none to hold is of the take on screen. A story the
	 * review said it was told is still awaited, and what was read of the one
	 * before stands until it is held.
	 */
	#holdNone(): void {
		this.#held = null;
	}
}
