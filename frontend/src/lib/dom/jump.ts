/**
 * The page taking the reader to an element: at once, and put right once
 * what that brought near stands at its real size.
 *
 * A file's rows are built once the reader comes near it, and built they may
 * take more room than their section held for them: a thread's card, a line
 * that wraps. A scroll made at once puts the element where it was sent;
 * then the files beside it are built, and what grows above it pushes it
 * down. The browser's scroll anchoring does not always hold it there:
 * Chromium does not where the element lands a fraction of a pixel low, the
 * file above left in view by that fraction. So once those files stand at
 * their real size, the element is scrolled to once more, at once. Once: that
 * scroll moves the area by what grew, and what grows below the element
 * moves nothing above it.
 *
 * Never a glide: across sixty files one took a second and a half, and ended
 * short of where the files built on its way had pushed the element.
 *
 * A jump is the page's own doing, and gives way to the reader's: once they
 * move themselves or act where they are, the element is not scrolled to
 * again, and stays where they take it.
 *
 * The page takes the reader one place at a time: `Jumps` holds the jump in
 * flight for whoever asks, to a section, a thread or a part of a story.
 */

// How many frames a file the first scroll brought near takes to stand at its real size. In the first,
// the browser says it has come near (`dom/built-when-near.svelte.ts`), and its rows are built after it;
// in the second, content-visibility lets them be drawn; by the third they are laid out at the height
// they take. Counted, not heard: each file is built on its own observer's word, and content-visibility
// speaks only of a file whose drawing it changes, so nothing says when all of them are done, and a jump
// that brought nothing new near would wait for a word never said. Seen so in Chromium, frame by frame
const FRAMES_TO_REAL_SIZE = 3;
// And how many more for whoever reads where the reader is, a reading band, to look at where the scroll
// that put the element right left them: told they had come to rest before then, the band would take what
// it says of that scroll for the reader moving on
const FRAMES_TO_LOOK_AGAIN = 1;
// What the reader does to move themselves, or to act where they are
const READERS_OWN_MOVES = ['wheel', 'touchstart', 'pointerdown', 'keydown'] as const;

class Jump {
	readonly #element: HTMLElement;
	readonly #sentTo: ScrollLogicalPosition;
	readonly #atRest: () => void;
	// What hears the reader's own moves while the jump is under way
	readonly #hearing = new AbortController();
	// Whether the reader has moved since it started: the element is then left where they take it
	#readerMoved = false;
	// The frame the jump waits for next, as the browser numbers its request: cancelled when another
	// jump takes its place
	#frameAwaited = 0;

	/**
	 * @param element what the reader is taken to
	 * @param sentTo where in its area the element is sent: its head to the top, or itself to the middle
	 * @param atRest called once the element has come to rest, where it was sent or where the reader
	 *   left it; never by a jump another took the place of
	 */
	constructor(element: HTMLElement, sentTo: ScrollLogicalPosition, atRest: () => void) {
		this.#element = element;
		this.#sentTo = sentTo;
		this.#atRest = atRest;
	}

	/** Scroll to the element at once, hearing the reader's own moves until the jump is over, and put it right later. */
	start(): void {
		for (const move of READERS_OWN_MOVES) {
			window.addEventListener(move, () => this.#giveWay(), {
				capture: true,
				passive: true,
				signal: this.#hearing.signal
			});
		}
		this.#scrollThere();
		this.#inFrames(FRAMES_TO_REAL_SIZE, () => this.#putRight());
	}

	/** Another jump takes its place: the frame it waits for is cancelled, so it scrolls no more and never says it has come to rest. */
	abandon(): void {
		cancelAnimationFrame(this.#frameAwaited);
		this.#hearing.abort();
	}

	/**
	 * What the first scroll brought near stands at its real size: the
	 * element is scrolled to once more, unless the reader has moved, and
	 * comes to rest once where that left them has been looked at.
	 */
	#putRight(): void {
		if (!this.#readerMoved) this.#scrollThere();
		this.#inFrames(FRAMES_TO_LOOK_AGAIN, () => this.#cameToRest());
	}

	/** The reader has come to rest: their moves are theirs alone again. */
	#cameToRest(): void {
		this.#hearing.abort();
		this.#atRest();
	}

	/** The reader moved, or acted where they are: the element is not scrolled to again, and nothing they do after is listened for. */
	#giveWay(): void {
		this.#readerMoved = true;
		this.#hearing.abort();
	}

	#scrollThere(): void {
		this.#element.scrollIntoView({ block: this.#sentTo, behavior: 'instant' });
	}

	/** Call back as the browser begins to draw the frame as many frames from now, before it lays that one out. */
	#inFrames(count: number, then: () => void): void {
		this.#frameAwaited = requestAnimationFrame(() => (count > 1 ? this.#inFrames(count - 1, then) : then()));
	}
}

/** What says which of some elements the reader is at, and is told when the page takes them to one: a reading band. */
interface TakesLandings {
	/** The page is taking the reader to this element: it is the one they are at from now on. */
	land: (element: Element) => void;
	/** The reader has come to rest: from here on, where they are is theirs to say by moving on. */
	settle: () => void;
}

/**
 * Where the page is taking the reader: one place at a time, whoever asks.
 *
 * A jump asked for takes the place of the one in flight, which scrolls no
 * more and never says it has come to rest: an earlier one neither pulls the
 * reader back nor does what it meant to do at rest once another was asked
 * for. What it owed whoever it landed on is not lost with it: they hear
 * that the reader has come to rest from the jump that took its place,
 * whoever asked for that one.
 */
export class Jumps {
	// The jump in flight, or the last one made
	#latest: Jump | null = null;
	// Whoever was told the reader is being taken to one of theirs, and is still owed word that they came to rest
	readonly #landedOn = new Set<TakesLandings>();

	/**
	 * Take the reader to an element, in place of wherever the page was taking them.
	 *
	 * @param element what the reader is taken to
	 * @param sentTo where in its area the element is sent: its head to the top, or itself to the middle
	 * @param atRest what this jump alone does once it has come to rest, unless another takes its place first
	 */
	to(element: HTMLElement, sentTo: ScrollLogicalPosition, atRest?: () => void): void {
		this.#latest?.abandon();
		this.#latest = new Jump(element, sentTo, () => this.#cameToRest(atRest));
		this.#latest.start();
	}

	/**
	 * Take the reader to the head of an element, and tell whoever reads
	 * which of such elements the reader is at that it is this one from now
	 * on, whatever is at the top while it is on its way. They hear once the
	 * reader has come to rest, from this jump or from one that took its place.
	 */
	land(reading: TakesLandings, element: HTMLElement, atRest?: () => void): void {
		reading.land(element);
		this.#landedOn.add(reading);
		this.to(element, 'start', atRest);
	}

	/** The reader has come to rest where the page took them: whoever was landed on since the last rest hears of it. */
	#cameToRest(atRest: (() => void) | undefined): void {
		for (const reading of this.#landedOn) reading.settle();
		this.#landedOn.clear();
		atRest?.();
	}
}
