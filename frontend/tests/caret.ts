/** Where the browser puts its caret under the pointer, which jsdom, laying nothing out, cannot say. */

/** Have the caret under the pointer fall at a place in a text node, wherever the pointer is. */
export function caretFallsAt(text: Node, offset: number): void {
	Object.defineProperty(document, 'caretPositionFromPoint', {
		configurable: true,
		value: () => ({ offsetNode: text, offset })
	});
}

/** A browser that says its caret under the pointer by the older range alone, as Safari before 26.2: over nothing yet. */
export function caretByRangeAlone(): void {
	delete (document as Partial<Document>).caretPositionFromPoint;
	caretRangeFallsAt(document, 0);
}

/** Have the caret range under the pointer start at a place in a text node, wherever the pointer is. */
export function caretRangeFallsAt(text: Node, offset: number): void {
	Object.defineProperty(document, 'caretRangeFromPoint', {
		configurable: true,
		value: () => ({ startContainer: text, startOffset: offset })
	});
}

/** A browser with no way to say where its caret under the pointer stands. */
export function noCaretUnderThePointer(): void {
	delete (document as Partial<Document>).caretPositionFromPoint;
	delete (document as Partial<Document>).caretRangeFromPoint;
}
