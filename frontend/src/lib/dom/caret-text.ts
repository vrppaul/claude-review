/**
 * Where the pointer stands in the text of an element: the browser's caret
 * under it, and the place that is in the element's text, counted in UTF-16
 * units from the element's first character, however deep in its markup the
 * caret's text lies — a line of code is spans of the highlighter's, and
 * marks of what changed inside them.
 */

/** A place between two characters of a text node: the caret, as the browser says where it is. */
export interface Caret {
	node: Node;
	offset: number;
}

/** The caret under a point of the window, as the browser puts it there; null over nothing that holds text. */
export type CaretReader = (windowX: number, windowY: number) => Caret | null;

/**
 * How this browser says where its caret under the pointer stands: by its
 * position, or by the older range where that is all it has; null where it
 * has neither.
 */
export function caretReaderOfThisBrowser(): CaretReader | null {
	if ('caretPositionFromPoint' in document) return caretByPosition;
	if ('caretRangeFromPoint' in document) return caretByRange;
	return null;
}

/** The caret under a point of the window, read by its position. */
function caretByPosition(windowX: number, windowY: number): Caret | null {
	const position = document.caretPositionFromPoint(windowX, windowY);
	return position === null ? null : { node: position.offsetNode, offset: position.offset };
}

/** The caret under a point of the window, read as where the range it would hold starts. */
function caretByRange(windowX: number, windowY: number): Caret | null {
	// eslint-disable-next-line @typescript-eslint/no-deprecated -- Safari before 26.2 says the caret this way alone
	const range = document.caretRangeFromPoint(windowX, windowY);
	return range === null ? null : { node: range.startContainer, offset: range.startOffset };
}

/** Where a caret stands in the text of an element, in units from its start; null for a caret outside its text. */
export function textOffsetIn(element: Node, caret: Caret): number | null {
	let before = 0;
	for (const text of textNodesOf(element)) {
		if (text === caret.node) return before + caret.offset;
		before += text.data.length;
	}
	return null;
}

/** The stretch of an element's text from one place to another, in units from its start, as a range of the document. */
export function rangeOfText(element: Node, start: number, end: number): Range {
	const range = document.createRange();
	let before = 0;
	for (const text of textNodesOf(element)) {
		const after = before + text.data.length;
		if (start >= before && start <= after) range.setStart(text, start - before);
		if (end >= before && end <= after) range.setEnd(text, end - before);
		before = after;
	}
	return range;
}

/** Every text node inside an element, in the order it reads. */
function textNodesOf(element: Node): Text[] {
	const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
	const texts: Text[] = [];
	for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
		if (node instanceof Text) texts.push(node);
	}
	return texts;
}
