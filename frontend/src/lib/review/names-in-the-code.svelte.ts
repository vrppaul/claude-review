/**
 * Names pointed at and pressed in the code of one reading area: the word
 * under the pointer marked while the key is held, and the lookup of the
 * name pressed, its pane standing by the name in the area and scrolling with
 * the code.
 *
 * What a name is, the review says at the press: the page only finds the
 * word under the pointer, to mark it while the key is held and to say
 * which character was pressed. One belongs to each area a view scrolls in,
 * so it goes when its view goes.
 */

import type { PlaceInCode } from '$lib/api/review-api';
import { type Caret, type CaretReader, caretReaderOfThisBrowser, rangeOfText, textOffsetIn } from '$lib/dom/caret-text';
import { type CodeMarks, codeMarksOfThisBrowser } from '$lib/dom/code-marks';
import type { FileSections } from '$lib/dom/file-sections';
import { DrawnName } from '$lib/review/drawn-name';
import { type AskedFrom, NameLookup } from '$lib/review/name-lookup.svelte';
import { READS_NAMES } from '$lib/review/reads-names';
import type { ReviewMode } from '$lib/types';
import { columnOf, wordAtCaret } from '$lib/utils/code-words';
import { placeKey } from '$lib/utils/line-places';

/**
 * What a browser lends the code's names: where its caret under the pointer stands, which says the word under it and
 * the character pressed, and the marks it draws over the code.
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
	if (!READS_NAMES[mode]) return null;
	const caretAt = caretReaderOfThisBrowser();
	if (caretAt === null) return null;
	const marks = codeMarksOfThisBrowser();
	return marks === null ? null : { caretAt, marks };
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

/**
 * A name pressed in a line's code: the pane stands by the name as its line is drawn now, while the line reads it
 * there, and the keyboard goes to the line's number, or to its file's toggle once the line is gone.
 */
export class PressedInTheCode implements AskedFrom {
	readonly #sections: FileSections;
	readonly #path: string;
	readonly #lineKey: string;
	/** The name where it stands in its line, found there as the line is drawn now. */
	readonly name: DrawnName;
	readonly standsBy: { at: () => DOMRectReadOnly | null };

	/**
	 * @param sections where each line of the review is drawn
	 * @param path the file the name was pressed in
	 * @param lineKey the key the line pressed is known by among its file's lines
	 * @param pressed the word pressed
	 */
	constructor(sections: FileSections, path: string, lineKey: string, pressed: PointedWord) {
		this.#sections = sections;
		this.#path = path;
		this.#lineKey = lineKey;
		this.name = new DrawnName(sections, path, lineKey, { column: pressed.starts, name: pressed.word });
		this.standsBy = { at: this.name.box };
	}

	readonly standsThere = (): boolean => this.name.stretch() !== null;

	readonly keyboardTo = (): HTMLElement | null => this.#sections.lineOrFile(this.#path, this.#lineKey);
}

export class NamesInTheCode {
	readonly #caretAt: CaretReader;
	readonly #sections: FileSections;
	/** The page's marks over the code, which the words marked here are drawn with. */
	readonly marks: CodeMarks;
	/** The lookup of the name pressed, while its pane or its window is open. */
	readonly lookup = new NameLookup<PressedInTheCode>();
	// Read again as the key goes down or up, the pointer still: kept only to mark what is under it
	#pointer: PointerOverCode | null = null;
	#held = $state.raw<Range | null>(null);

	/**
	 * @param pointing what the browser lends: the caret under the pointer, and the page's marks over the code, which
	 * the words marked here are drawn with
	 * @param sections where each line of the review is drawn, which the name pressed is found in while its pane is
	 * open
	 */
	constructor({ caretAt, marks }: NamePointing, sections: FileSections) {
		this.#caretAt = caretAt;
		this.marks = marks;
		this.#sections = sections;
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
		const from = new PressedInTheCode(this.#sections, line.path, lineKey, pressed);
		this.lookup.ask({ ...line, column: pressed.column }, pressed.word, from, take);
	}
}
