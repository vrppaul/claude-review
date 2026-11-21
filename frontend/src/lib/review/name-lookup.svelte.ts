/**
 * Where a name in the code is defined and used, asked of the review from
 * one reading area: the name the reader pressed there, and what the review
 * answered of it, held while its pane is open and gone once it closes.
 *
 * What a name is, the review says at the press: the page only finds the
 * word under the pointer, to mark it while the key is held and to say
 * which character was pressed. One lookup belongs to each area a view
 * scrolls in, so it goes when its view goes, and its pane stands in the
 * area, by the name pressed, scrolling with the code.
 */

import { type PlaceInCode, readName } from '$lib/api/review-api';
import { type Caret, type CaretReader, caretReaderOfThisBrowser, rangeOfText, textOffsetIn } from '$lib/dom/caret-text';
import { type CodeMarks, codeMarksOfThisBrowser } from '$lib/dom/code-marks';
import type { FileSections } from '$lib/dom/file-sections';
import { DrawnName } from '$lib/review/drawn-name';
import type { NameResponse, ReviewMode } from '$lib/types';
import { columnOf, wordAtCaret } from '$lib/utils/code-words';
import { messageOf } from '$lib/utils/errors';
import { placeKey } from '$lib/utils/line-places';

/**
 * Whether each kind of review looks names up: only a review of a
 * repository's change has a repository to look through, and the key does
 * nothing in the others.
 */
const LOOKS_UP_NAMES: Record<ReviewMode, boolean> = { diff: true, files: false, transcript: false };

/**
 * What a browser lends the lookup: where its caret under the pointer stands,
 * which says the word under it and the character pressed, and the marks it
 * draws over the code.
 */
export interface NamePointing {
	caretAt: CaretReader;
	marks: CodeMarks;
}

/**
 * How names are pointed at in a review of a kind, in this browser, asked
 * once as the review opens: none where the review looks no names up, or the
 * browser cannot say its caret under the pointer or draw marks over text,
 * and then the gesture is not offered at all.
 */
export function namePointingIn(mode: ReviewMode): NamePointing | null {
	if (!LOOKS_UP_NAMES[mode]) return null;
	const caretAt = caretReaderOfThisBrowser();
	if (caretAt === null) return null;
	const marks = codeMarksOfThisBrowser();
	return marks === null ? null : { caretAt, marks };
}

/** What asking came to: on its way, the review's answer, or why it could not be had. */
type Looked = { kind: 'looking' } | { kind: 'found'; found: NameResponse } | { kind: 'failed'; why: string };

/** The name the reader pressed: the place asked about, the word pressed, where it stands, and what asking came to. */
export interface AskedName {
	place: PlaceInCode;
	/** The word under the pointer, which heads the pane until the review says what the name is. */
	word: string;
	/** The word where it stands in its line, found there as the line is drawn now. */
	at: DrawnName;
	/** The take of the review the name was pressed in, which what the review answers of it is of. */
	take: number;
	looked: Looked;
}

/**
 * The word under the pointer in a line of code: what it says, the columns it starts at and of the character
 * pressed, and its range.
 */
export interface PointedWord {
	word: string;
	starts: number;
	column: number;
	range: Range;
}

/** Where the pointer was last over a line's code that takes the gesture, in the window. */
interface PointerOverCode {
	code: HTMLElement;
	windowX: number;
	windowY: number;
}

// A lookup on its way
const LOOKING: Looked = { kind: 'looking' };

/** Ask the review about a place, and say what that came to: whatever it refuses, in its own words. */
async function lookedUp(place: PlaceInCode): Promise<Looked> {
	try {
		return { kind: 'found', found: await readName(place) };
	} catch (error) {
		return { kind: 'failed', why: messageOf(error) };
	}
}

/** The word in a line's code at the caret, if the caret is in the line and touches one. */
function wordAt(code: HTMLElement, caret: Caret | null): PointedWord | null {
	const offset = caret === null ? null : textOffsetIn(code, caret);
	const text = code.textContent;
	const word = offset === null ? null : wordAtCaret(text, offset);
	if (word === null) return null;
	return {
		word: text.slice(word.start, word.end),
		starts: columnOf(text, word.start),
		column: columnOf(text, word.pressed),
		range: rangeOfText(code, word.start, word.end)
	};
}

export class NameLookup {
	#asked = $state.raw<AskedName | null>(null);
	readonly #caretAt: CaretReader;
	readonly #sections: FileSections;
	/** The page's marks over the code, which the words this lookup marks are drawn with. */
	readonly marks: CodeMarks;
	// Read again as the key goes down or up, the pointer still: kept only to mark what is under it
	#pointer: PointerOverCode | null = null;
	#held = $state.raw<Range | null>(null);

	/**
	 * @param pointing what the browser lends the lookup: the caret under the pointer, and the page's marks over the
	 * code, which the words it marks are drawn with
	 * @param sections where each line of the review is drawn, which the name pressed is found in while its pane is
	 * open
	 */
	constructor({ caretAt, marks }: NamePointing, sections: FileSections) {
		this.#caretAt = caretAt;
		this.marks = marks;
		this.#sections = sections;
	}

	/** The name pressed, while its pane is open, and marked; null once it closes, or before any is pressed. */
	get asked(): AskedName | null {
		return this.#asked;
	}

	/** The word under the pointer while the key is held, and marked; null while none is. */
	get held(): Range | null {
		return this.#held;
	}

	/**
	 * The pointer moved over a line's code that takes the gesture: the word
	 * under it is marked while the key is held, and unmarked once it is not,
	 * or the pointer is over no word.
	 */
	point(code: HTMLElement, event: MouseEvent, held: boolean): void {
		this.#pointer = { code, windowX: event.clientX, windowY: event.clientY };
		this.hold(held);
	}

	/** The key went down or up, the pointer where it was: the word under it is marked, or no longer. */
	hold(held: boolean): void {
		const pointer = this.#pointer;
		const pointed = held && pointer !== null ? this.wordUnder(pointer.code, pointer.windowX, pointer.windowY) : null;
		this.#held = pointed?.range ?? null;
	}

	/** The word under a point of the window in a line's code, if the browser's caret there touches one. */
	wordUnder(code: HTMLElement, windowX: number, windowY: number): PointedWord | null {
		return wordAt(code, this.#caretAt(windowX, windowY));
	}

	/**
	 * Ask about a word pressed in a line's code, the place of the line saying where it is, and the take of the
	 * review the line is drawn from.
	 */
	ask(line: Omit<PlaceInCode, 'column'>, pressed: PointedWord, take: number): void {
		const lineKey = placeKey({ side: line.side, number: line.line });
		const asked: AskedName = {
			place: { ...line, column: pressed.column },
			word: pressed.word,
			at: new DrawnName(this.#sections, line.path, lineKey, { column: pressed.starts, name: pressed.word }),
			take,
			looked: LOOKING
		};
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

	/** Close the pane: what was asked is gone. */
	close(): void {
		this.#asked = null;
	}

	/** Look a name up, and hold what came of it while it is still the one asked about. */
	async #lookUp(asked: AskedName): Promise<void> {
		const looked = await lookedUp(asked.place);
		if (this.#asked === asked) this.#asked = { ...asked, looked };
	}
}
