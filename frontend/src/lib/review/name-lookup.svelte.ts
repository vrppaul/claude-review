/**
 * Where a name in the code is defined and used, asked of the review: the
 * place asked about, what the review answered of it, and how the reader
 * reads that, held while its pane or its window is open and gone once it
 * closes.
 *
 * A name is asked about from two places — pressed in a reading area's code,
 * or by the icon on its row in the tree of files — and each keeps its own
 * lookup. What differs between them is only where the question was asked
 * from (`AskedFrom`): where the pane stands, whether that is still drawn,
 * and what takes the keyboard as the pane or the window goes.
 */

import { type PlaceInCode, readName } from '$lib/api/review-api';
import { focusWhatRemains } from '$lib/dom/keyboard';
import type { NamePlace, NameResponse } from '$lib/types';
import { messageOf } from '$lib/utils/errors';

/**
 * How the reader reads what the review answered: in the pane by the name, a line to each place; or in a window over
 * the page, one place chosen at all times, its code beside the list.
 */
export type AnswerRead = { way: 'compact' } | { way: 'full'; chosen: NamePlace };

// How every answer is read as it comes
const IN_THE_PANE: AnswerRead = { way: 'compact' };

/**
 * What asking came to: on its way, the review's answer and how the reader reads it, or why it could not be had.
 * Only an answer is read one way or another: there is no window while the review looks, or once it failed.
 */
type Looked =
	{ kind: 'looking' } | { kind: 'found'; found: NameResponse; read: AnswerRead } | { kind: 'failed'; why: string };

// A lookup on its way
const LOOKING: Looked = { kind: 'looking' };

/**
 * What the lookup's pane stands by: a stretch of the code, where it stands in the window now and null while it is
 * not drawn; or the control pressed to ask, drawn apart from the pane.
 */
type PaneStandsBy = { at: () => DOMRectReadOnly | null } | { control: HTMLElement };

/** Where a name was asked about from, which is all the lookup's pane and window need of it. */
export interface AskedFrom {
	standsBy: PaneStandsBy;
	/** Whether what the pane stands by is still drawn for the name asked about. */
	standsThere: () => boolean;
	/** What takes the keyboard as the pane or the window goes: what was pressed, or what stands for it once it is gone. */
	keyboardTo: () => HTMLElement | null;
}

/** A name asked about: the place, the word asked, where it was asked from, and what asking came to. */
export interface AskedName<From extends AskedFrom> {
	place: PlaceInCode;
	/** The word asked about, which heads the pane until the review says what the name is. */
	word: string;
	from: From;
	/** The take of the review the name was asked in, which what the review answers of it is of. */
	take: number;
	looked: Looked;
}

/** Ask the review about a place, and say what that came to: whatever it refuses, in its own words. */
async function lookedUp(place: PlaceInCode): Promise<Looked> {
	try {
		return { kind: 'found', found: await readName(place), read: IN_THE_PANE };
	} catch (error) {
		return { kind: 'failed', why: messageOf(error) };
	}
}

/** Put the keyboard on what a name was asked from, so the pane opening by it notes it and gives it back there. */
function keyboardToWhereAsked(from: AskedFrom): void {
	from.keyboardTo()?.focus({ preventScroll: true });
}

export class NameLookup<From extends AskedFrom> {
	#asked = $state.raw<AskedName<From> | null>(null);

	/** The name asked about, while its pane or its window is open; null once it closes, or before any is asked. */
	get asked(): AskedName<From> | null {
		return this.#asked;
	}

	/**
	 * Ask the review about the word at a place, from where the reader asked, in the take on screen. The keyboard
	 * goes there first, as the pane notes what has it as it opens.
	 */
	ask(place: PlaceInCode, word: string, from: From, take: number): void {
		const asked: AskedName<From> = { place, word, from, take, looked: LOOKING };
		keyboardToWhereAsked(from);
		this.#asked = asked;
		void this.#lookUp(asked);
	}

	/** Ask again about the name whose lookup failed. */
	tryAgain(): void {
		const asked = this.#asked;
		if (asked === null) return;
		const again = { ...asked, looked: LOOKING };
		this.#asked = again;
		void this.#lookUp(again);
	}

	/** Read the review's answer in the window, or choose another place there. */
	readInTheWindow(chosen: NamePlace): void {
		this.#readAnswer({ way: 'full', chosen });
	}

	/** Bring the pane back from the window, the keyboard first on where the name was asked from, as at the asking. */
	readInThePane(): void {
		const asked = this.#asked;
		if (asked === null) return;
		keyboardToWhereAsked(asked.from);
		this.#readAnswer(IN_THE_PANE);
	}

	/**
	 * Put the keyboard back where the name was asked from, before the review hears a key pressed in the pane: the
	 * pane stands apart from that in the page's order, and a key that acts from where the keyboard is would act there.
	 */
	keyboardBack(): void {
		const asked = this.#asked;
		if (asked !== null) keyboardToWhereAsked(asked.from);
	}

	/**
	 * Whether what the lookup holds stands for what is on screen: asked of the take on screen, and what it was asked
	 * from still drawn. Once the change is taken again, or that is drawn no more, it is of the past.
	 */
	standsFor(takeOnScreen: number): boolean {
		const asked = this.#asked;
		return asked !== null && asked.take === takeOnScreen && asked.from.standsThere();
	}

	/** Close the pane, or the window: what was asked is gone. */
	close(): void {
		this.#asked = null;
	}

	/**
	 * Close the pane or the window, the keyboard going to where the name was asked from, or what stands for that,
	 * where their going leaves it on nothing.
	 */
	closeToWhereAsked(): void {
		const asked = this.#asked;
		if (asked === null) return;
		focusWhatRemains(asked.from.keyboardTo);
		this.#asked = null;
	}

	/** Read the review's answer about the name asked about so, while there is one. */
	#readAnswer(read: AnswerRead): void {
		const asked = this.#asked;
		if (asked?.looked.kind === 'found') this.#asked = { ...asked, looked: { ...asked.looked, read } };
	}

	/** Look a name up, and hold what came of it while it is still the one asked about. */
	async #lookUp(asked: AskedName<From>): Promise<void> {
		const looked = await lookedUp(asked.place);
		if (this.#asked === asked) this.#asked = { ...asked, looked };
	}
}
