/**
 * The marks laid over words of the code: the name under the pointer while
 * the key that asks about it is held, the name pressed while its pane is
 * open, the name on the line the reader was taken to while the line is lit.
 *
 * Each is a highlight of the page (the CSS Custom Highlight API), drawn over
 * the text where it stands, so no mark rewrites a line's markup: what the
 * pointer went down on is still there as the press ends, and text selects as
 * on any line. The browser keeps one highlight to a name for the whole page,
 * so the page makes the three once, and the library's CodeMark lays its
 * ground on a stretch while it is drawn and takes it off as it goes: no
 * mark outlives what drew it.
 */

const MARKS = ['held', 'pressed', 'arrived'] as const;

/** What a mark over the code says of the word under it. */
export type CodeMark = (typeof MARKS)[number];

// The name each mark's highlight is drawn by (ui.css)
const DRAWN_AS: Record<CodeMark, string> = {
	held: 'cr-held-name',
	pressed: 'cr-pressed-name',
	arrived: 'cr-arrived-name'
};

/*
 * What the element a mark's stretch stands in carries while the mark is
 * laid, so the mark's highlight is drawn by a rule that holds there alone
 * (ui.css): a rule that held on every element made reading in the hidden
 * lines of a file of 5,000 lines take 80% more time recalculating styles
 */
const HELD_IN: Record<CodeMark, string> = {
	held: 'data-held-name',
	pressed: 'data-pressed-name',
	arrived: 'data-arrived-name'
};

/** The marks over the code, made for the page where this browser draws highlights; null where it draws none. */
export function codeMarksOfThisBrowser(): CodeMarks | null {
	return typeof globalThis.Highlight === 'function' && 'highlights' in CSS ? new CodeMarks() : null;
}

export class CodeMarks {
	readonly #highlights: Record<CodeMark, Highlight> = {
		held: new Highlight(),
		pressed: new Highlight(),
		arrived: new Highlight()
	};

	/**
	 * Made once for the page, in a browser that draws highlights (codeMarksOfThisBrowser): each mark's highlight is
	 * drawn from now on, holding nothing until a stretch is marked.
	 */
	constructor() {
		for (const mark of MARKS) CSS.highlights.set(DRAWN_AS[mark], this.#highlights[mark]);
	}

	/** Lay a mark over a stretch of the code, until whoever laid it takes it off. */
	lay(mark: CodeMark, stretch: Range): void {
		this.#highlights[mark].add(stretch);
		holderOf(stretch)?.setAttribute(HELD_IN[mark], '');
	}

	/** Take a mark off a stretch it was laid over. */
	takeOff(mark: CodeMark, stretch: Range): void {
		this.#highlights[mark].delete(stretch);
		holderOf(stretch)?.removeAttribute(HELD_IN[mark]);
	}
}

/** The element a stretch of text stands in: the nearest one that holds all of it. */
function holderOf(stretch: Range): Element | null {
	const holder = stretch.commonAncestorContainer;
	return holder instanceof Element ? holder : holder.parentElement;
}
