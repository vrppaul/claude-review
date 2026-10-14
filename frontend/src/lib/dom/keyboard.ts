/**
 * Moving around a review from the keyboard.
 *
 * Focus is the cursor: the line numbers are buttons, so moving between them
 * is moving focus, the browser scrolls it into view, and the focus ring shows
 * where you are. That saves inventing a second notion of "current line" that
 * would have to be kept in step with the real one.
 */

import { tick } from 'svelte';

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
 * Whether a key is part of a word an input method is composing — a word
 * built from several keys, as Japanese or Chinese is typed. Enter there takes
 * the composition and Escape drops it: neither is the page's, not a field's,
 * not a pane's and not the review's, and every key the page reads asks here
 * first.
 */
export function isComposingText(event: KeyboardEvent): boolean {
	return event.isComposing;
}

/**
 * What every line number a reader moves between from the keyboard carries,
 * in the order the page draws them. A role of its own: a test id may be
 * renamed for the tests' sake, and the tour's names are the tour's.
 */
export const LINE_NUMBER_ROLE = 'line-number';

/** The numbers of the lines drawn within an element, one for each row, in the order the page draws them. */
export function lineNumbersIn(within: HTMLElement): HTMLElement[] {
	return Array.from(within.querySelectorAll<HTMLElement>(`[data-role="${LINE_NUMBER_ROLE}"]`));
}

/** Whether an element comes after another in the document. */
function follows(element: Element, other: Element): boolean {
	return (other.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/**
 * What everything kept in sight at the top of a reading area carries, while
 * what it heads scrolls under it: the header of a section, the slot of a
 * chapter's bar. A line behind one is drawn, and the reader does not see it.
 * The role is what keeps it there: the stylesheet has one rule that does,
 * and it is the role's.
 */
export const KEPT_IN_SIGHT_ROLE = 'kept-in-sight';

// How near two edges stand that touch, in pixels: where an edge stands is not a whole number
const TOUCHING_WITHIN = 1;

/**
 * Where what the reader sees of a reading area begins: at its top edge, or
 * at the foot of what is kept in sight there, one thing under another — the
 * bar of a chapter, and under it the header of the piece being read. They
 * are looked at in the order the page draws them, which is down the area:
 * each one that begins no lower than what is seen so far takes its room too.
 */
function inSightFrom(area: HTMLElement): number {
	let seenFrom = area.getBoundingClientRect().top;
	for (const kept of area.querySelectorAll(`[data-role="${KEPT_IN_SIGHT_ROLE}"]`)) {
		const box = kept.getBoundingClientRect();
		if (box.top - seenFrom < TOUCHING_WITHIN) seenFrom = Math.max(seenFrom, box.bottom);
	}
	return seenFrom;
}

/**
 * The line the reader reads from in a reading area: the first that begins
 * where what they see of the area does, or below. With every line above
 * that, the last.
 */
function lineReadFrom(lines: HTMLElement[], area: HTMLElement): HTMLElement | undefined {
	const seenFrom = inSightFrom(area);
	return lines.find((line) => seenFrom - line.getBoundingClientRect().top < TOUCHING_WITHIN) ?? lines.at(-1);
}

/**
 * The line a step lands on from whatever has the keyboard. From a line, the
 * next or the previous. From anything else in the reading area — a thread
 * the reader was taken to, a button in a file's header — the first line
 * below it or the last above it. From outside the area — an entry of the
 * column beside it, a control of the page's header — or from nothing, the
 * line the reader reads from, whichever way the step goes: what holds the
 * keyboard there stands before everything that is read, and a step counted
 * from it would throw the reader back to the first line of all. Never past
 * either end.
 */
function steppedTo(
	lines: HTMLElement[],
	area: HTMLElement,
	focused: Element | null,
	step: 1 | -1
): HTMLElement | undefined {
	if (focused === null || !area.contains(focused)) return lineReadFrom(lines, area);
	const at = lines.findIndex((line) => line === focused);
	if (at !== -1) return lines[Math.min(lines.length - 1, Math.max(0, at + step))];
	const beyond =
		step === 1 ? lines.find((line) => follows(line, focused)) : lines.findLast((line) => follows(focused, line));
	return beyond ?? (step === 1 ? lines.at(-1) : lines.at(0));
}

/** Move the keyboard one line down or up among the lines of a reading area, from wherever the keyboard is. */
export function moveByLine(area: HTMLElement, step: 1 | -1): void {
	steppedTo(lineNumbersIn(area), area, document.activeElement, step)?.focus();
}

/** What remains to take the keyboard, looked for once the page has drawn what changed: none, if it went too. */
type FindWhatRemains = () => HTMLElement | null | undefined;

/** The tab index of what only the page can put the keyboard on: Tab never reaches it. */
const KEYBOARD_BY_THE_PAGE_ONLY = -1;

/** Put the keyboard on an element; the screen stays where it is. */
function focusInPlace(element: HTMLElement): void {
	element.focus({ preventScroll: true });
}

/** The class of words while they are lent the keyboard: it stands their ring off them, who have no room of their own around them. */
const LENT_CLASS = 'cr-lent-keyboard';

/** What was lent the keyboard can take it no more, once the keyboard is on something else. */
function takeBackOnceLeft(element: HTMLElement, lent: AbortController): void {
	// A window the reader leaves blurs what holds the keyboard, which holds it still when they are back
	if (document.activeElement === element) return;
	element.removeAttribute('tabindex');
	element.classList.remove(LENT_CLASS);
	lent.abort();
}

/**
 * Put the keyboard on words, which are no control. Whatever can hold the
 * keyboard takes it on a press too, and a press on words must put it on
 * nothing: so the words can hold it only until it leaves them.
 */
function lendKeyboard(element: HTMLElement): void {
	const lent = new AbortController();
	element.tabIndex = KEYBOARD_BY_THE_PAGE_ONLY;
	element.classList.add(LENT_CLASS);
	element.addEventListener('blur', () => takeBackOnceLeft(element, lent), { signal: lent.signal });
	focusInPlace(element);
}

/** Give the keyboard to what is found, if it is on nothing now. */
function giveIfOnNothing(find: FindWhatRemains, give: (element: HTMLElement) => void): void {
	const focused = document.activeElement;
	if (focused !== null && focused !== document.body) return;
	const found = find();
	if (found) give(found);
}

/**
 * Once the page has drawn what an action changed, put the keyboard on what
 * remains in place of what went. The control an action was taken with often
 * goes with it — a field saved, a thread folded, settled or deleted, a gap
 * read whole — and the keyboard with it, onto nothing, where no key the
 * reader presses next acts where they were. Only then, and only on what is
 * drawn: a keyboard something else has taken stays where it is. The screen
 * does not move; the reader is looking there already.
 */
export function focusWhatRemains(find: FindWhatRemains): void {
	void tick().then(() => giveIfOnNothing(find, focusInPlace));
}

/**
 * As `focusWhatRemains`, where what remains stands far from what went and
 * is the one thing on the page that carries a role: the header's button
 * that brings back, or opens again, what was put away.
 */
export function focusWhatCarries(role: string): void {
	focusWhatRemains(() => document.querySelector<HTMLElement>(`[data-role="${role}"]`));
}

/**
 * As `focusWhatRemains`, where what remains is words and no control: the
 * head of the part of a story the reader was taken to. The words hold the
 * keyboard until it leaves them, and can take it no more after.
 */
export function lendKeyboardToWhatRemains(find: FindWhatRemains): void {
	void tick().then(() => giveIfOnNothing(find, lendKeyboard));
}
