/**
 * The page taking the reader to an element, until it stands where it was
 * sent.
 *
 * One scroll is aimed at where the element stands as it starts. A file's
 * rows are built once the reader comes near it, and built it takes another
 * room than its section held for it: so what lies below moves while the
 * files on the way are built, after the scroll was aimed. A scroll that
 * glides ends where the element was; one made at once to the foot of the
 * area is pushed out of it as the files beside it are built. So each time
 * the element has come to rest it is scrolled to once more, at once: a
 * scroll that moves nothing is the only proof that it stands where it was
 * sent, and one that moves it has put it there, to be looked at again.
 *
 * At once, not gliding again: glides one after the other take seconds.
 *
 * A jump is the page's own doing, and gives way to the reader's: once they
 * move themselves or act where they are, the element is left wherever it
 * comes to rest. Nor does it go on for ever: what something else keeps
 * moving is left to it, and the jump says it is over all the same.
 */

import type { Motion } from '$lib/dom/motion';

// A smooth scroll that never ends — a scroll container that cannot reach the
// element, a tab put in the background mid-flight — must not be waited on for ever
const SETTLE_WITHIN = 2000;
// How many frames in a row an element has to stay put to count as come to rest
const STILL_FRAMES = 2;
// How long an element may stand still, in milliseconds, before a scroll to it
// has begun to move it. A glide moves nothing in its first frames — two to
// four of them, 75 ms at the longest of twelve measured in Chromium — so it
// is given over three times that: what has not moved by then had nowhere to
// go. A scroll made at once has moved what it moves before anyone looks
const BEGINS_WITHIN: Record<Motion, number> = { smooth: 250, instant: 0 };
// How long a jump goes on scrolling to its element, in milliseconds: as long
// as a glide is waited on, and as long again for the scroll made at once
// that lands it. What still moves then is moved by something else, which is
// not the jump's to chase: whoever waits to hear it has come to rest hears it
const SCROLLS_ON_FOR = SETTLE_WITHIN + SETTLE_WITHIN;
// What the reader does to move themselves, or to act where they are
const READERS_OWN_MOVES = ['wheel', 'touchstart', 'pointerdown', 'keydown'] as const;

/** A jump under way: what stops the hearing of the reader's own moves, and when it started. */
interface UnderWay {
	hearing: AbortController;
	since: number;
}

/**
 * Call back once an element a scroll was asked to move has stopped moving.
 *
 * Where the element actually is, rather than which element is doing the
 * scrolling: a section sits inside whatever container the layout gives it,
 * and asking the element itself works wherever it ends up.
 */
class SettleWatch {
	readonly #element: HTMLElement;
	readonly #beginsWithin: number;
	readonly #then: () => void;
	readonly #startedAt = performance.now();
	readonly #startedFrom: number;
	#previousTop = Number.NaN;
	#stillFor = 0;
	#hasMoved = false;

	/**
	 * @param element what the scroll was asked to move
	 * @param moving how the scroll moves it, which says how long it may take to begin
	 * @param then called once the element is still, or has been waited on long enough
	 */
	constructor(element: HTMLElement, moving: Motion, then: () => void) {
		this.#element = element;
		this.#beginsWithin = BEGINS_WITHIN[moving];
		this.#then = then;
		this.#startedFrom = element.getBoundingClientRect().top;
	}

	/** Start looking, once a frame, until the element is still. */
	start(): void {
		requestAnimationFrame(() => this.#look());
	}

	#look(): void {
		const top = this.#element.getBoundingClientRect().top;
		const waited = performance.now() - this.#startedAt;
		this.#stillFor = top === this.#previousTop ? this.#stillFor + 1 : 0;
		this.#previousTop = top;
		this.#hasMoved ||= top !== this.#startedFrom;

		// Standing still before it has begun to move is not having come to rest
		const begun = this.#hasMoved || waited >= this.#beginsWithin;
		const settled = begun && this.#stillFor >= STILL_FRAMES;
		if (settled || waited > SETTLE_WITHIN) {
			this.#then();
			return;
		}
		requestAnimationFrame(() => this.#look());
	}
}

export class Jump {
	readonly #element: HTMLElement;
	readonly #sentTo: ScrollLogicalPosition;
	readonly #motion: Motion;
	readonly #atRest: () => void;
	// Held while the jump is under way: null before it starts, and once it is over
	#underWay: UnderWay | null = null;
	// Whether the reader has moved since it started: the element is then left wherever it comes to rest
	#readerMoved = false;

	/**
	 * @param element what the reader is taken to
	 * @param sentTo where in the area it scrolls in the element is sent: its head to the top, or itself to the middle
	 * @param motion how the first scroll to it moves
	 * @param atRest called once the element has come to rest, where it was sent or where the reader
	 *   left it; never by a jump another took the place of
	 */
	constructor(element: HTMLElement, sentTo: ScrollLogicalPosition, motion: Motion, atRest: () => void) {
		this.#element = element;
		this.#sentTo = sentTo;
		this.#motion = motion;
		this.#atRest = atRest;
	}

	/** Scroll to the element, and go on until it rests where it was sent. */
	start(): void {
		const hearing = new AbortController();
		this.#underWay = { hearing, since: performance.now() };
		for (const move of READERS_OWN_MOVES) {
			window.addEventListener(move, () => (this.#readerMoved = true), {
				capture: true,
				passive: true,
				signal: hearing.signal
			});
		}
		this.#scrollThere(this.#motion);
	}

	/** Another jump takes its place: it scrolls no more, and never says it has come to rest. */
	abandon(): void {
		this.#end();
	}

	/** Scroll to the element, and look again once it has come to rest. */
	#scrollThere(moving: Motion): void {
		const from = this.#top();
		this.#element.scrollIntoView({ block: this.#sentTo, behavior: moving });
		new SettleWatch(this.#element, moving, () => this.#cameToRest(from)).start();
	}

	/**
	 * The element has come to rest since it was last scrolled to, or was
	 * waited on long enough. Where that scroll moved it, or something has
	 * since, it may not stand where it was sent: it is scrolled to once
	 * more, at once — unless the reader has moved, or the jump has gone on
	 * as long as one may.
	 */
	#cameToRest(from: number): void {
		const underWay = this.#underWay;
		if (underWay === null) return;
		const movedSince = this.#top() !== from;
		const jumpGoesOn = !this.#readerMoved && performance.now() - underWay.since <= SCROLLS_ON_FOR;
		if (movedSince && jumpGoesOn) {
			this.#scrollThere('instant');
			return;
		}
		this.#end();
		this.#atRest();
	}

	#top(): number {
		return this.#element.getBoundingClientRect().top;
	}

	/** The jump is over, however it ended: the reader's moves are theirs alone again. */
	#end(): void {
		this.#underWay?.hearing.abort();
		this.#underWay = null;
	}
}
