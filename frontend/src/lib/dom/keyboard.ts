/**
 * Moving around a review from the keyboard.
 *
 * Focus is the cursor: the line numbers are buttons, so moving between them
 * is moving focus, the browser scrolls it into view, and the focus ring shows
 * where you are. That saves inventing a second notion of "current line" that
 * would have to be kept in step with the real one.
 */

/** Text-entry inputs; a checkbox or a button is not one of them. */
const TYPED_INTO = new Set(['text', 'search', 'email', 'url', 'tel', 'password', 'number']);

/**
 * Whether a key belongs to whatever has focus rather than to the review.
 *
 * Checking only the tag name caught checkboxes too, so one click on "Viewed"
 * parked focus on a hidden input and every shortcut went dead with nothing
 * on screen to explain it.
 */
export function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	if (target.isContentEditable || target.tagName === 'TEXTAREA') return true;
	if (!(target instanceof HTMLInputElement)) return false;
	return TYPED_INTO.has(target.type);
}

/**
 * What every line number a reader moves between from the keyboard carries,
 * in the order the page draws them. A role of its own: a test id may be
 * renamed for the tests' sake, and the tour's names are the tour's.
 */
export const LINE_NUMBER_ROLE = 'line-number';

function lineNumbers(): HTMLElement[] {
	return Array.from(document.querySelectorAll<HTMLElement>(`[data-role="${LINE_NUMBER_ROLE}"]`));
}

/** Whether an element comes after another in the document. */
function follows(element: Element, other: Element): boolean {
	return (other.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/**
 * The line a step lands on from whatever has the focus: the next or the
 * previous line from a line; from anything else on the page — a thread the
 * reader was taken to, a button in a file's header — the first line below it
 * or the last above it; from nothing, the first line. Never past either end.
 */
function steppedTo(lines: HTMLElement[], focused: Element | null, step: 1 | -1): HTMLElement | undefined {
	if (focused === null || focused === document.body) return lines.at(0);
	const at = lines.findIndex((line) => line === focused);
	if (at !== -1) return lines[Math.min(lines.length - 1, Math.max(0, at + step))];
	const beyond =
		step === 1 ? lines.find((line) => follows(line, focused)) : lines.findLast((line) => follows(focused, line));
	return beyond ?? (step === 1 ? lines.at(-1) : lines.at(0));
}

/** Move focus one line down or up, from wherever the focus is, starting at the top when nothing is focused. */
export function moveByLine(step: 1 | -1): void {
	steppedTo(lineNumbers(), document.activeElement, step)?.focus();
}
