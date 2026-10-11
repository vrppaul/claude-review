/**
 * The keys the review answers: one table, which the keys run and the help
 * reads, so the two cannot say different things.
 *
 * A key on its own is the review's only while nothing is being typed — j in
 * a comment is a letter. A chord is the review's anywhere: finishing the
 * review from inside a comment field is what it is for.
 */

import { isTypingTarget, moveByLine } from '$lib/dom/keyboard';
import type { Review } from '$lib/review/review.svelte';

/** What is held with a key: nothing, or Ctrl (Cmd on a Mac) and Shift together. */
type Held = 'nothing' | 'command-and-shift';

/** A key as it is pressed, and what it does. */
interface Press {
	key: string;
	held: Held;
	run: (review: Review) => void;
}

/** One line of the help: the keys as it writes them, what they do, and each press. */
export interface KeyRow {
	keys: string;
	does: string;
	presses: readonly Press[];
}

/** A key pressed on its own. */
function alone(key: string, run: (review: Review) => void): Press {
	return { key, held: 'nothing', run };
}

/**
 * Open the panel and put the cursor in it. Everything else in this review
 * can be done from the keyboard; talking to the agent should not be the one
 * thing that needs a mouse.
 */
function talkToAgent(review: Review): void {
	review.layout.agentPanel.setOpen(true);
	review.layout.agentPanel.askForInput();
}

/** Do something to the file the reader is in: by focus if a line in it has the focus, by scroll if not. */
function onCurrentFile(review: Review, act: (path: string) => void): void {
	const path = review.sections.focused() ?? review.sections.fileInView;
	if (path) act(path);
}

/** The first press opens the pane the review is sent from; the second sends it. */
function finish(review: Review): void {
	if (review.submission.finishing) void review.submission.send();
	else review.submission.setFinishing(true);
}

export const KEYMAP: readonly KeyRow[] = [
	{
		keys: 'j / k',
		does: 'Down / up a line',
		presses: [alone('j', () => moveByLine(1)), alone('k', () => moveByLine(-1))]
	},
	// Enter on a line's number is the number's own: it is a button
	{ keys: 'Enter', does: 'Comment on this line', presses: [] },
	{
		keys: '] / [',
		does: 'Next / previous file',
		presses: [
			alone(']', (review) => review.navigator.stepFile(1)),
			alone('[', (review) => review.navigator.stepFile(-1))
		]
	},
	{
		keys: 'n / p',
		does: 'Next / previous comment',
		presses: [alone('n', (review) => review.navigator.step(1)), alone('p', (review) => review.navigator.step(-1))]
	},
	{ keys: 'a', does: 'Next unread reply', presses: [alone('a', (review) => review.navigator.nextUnread())] },
	{ keys: 'c', does: 'Talk to the agent', presses: [alone('c', talkToAgent)] },
	{ keys: 'f', does: 'Show or hide the file tree', presses: [alone('f', (review) => review.layout.fileTree.toggle())] },
	{
		keys: 'v',
		does: 'Mark this file viewed',
		presses: [alone('v', (review) => onCurrentFile(review, (path) => review.reading.toggleViewed(path)))]
	},
	{
		keys: 'u',
		does: 'Fold or unfold this file',
		presses: [alone('u', (review) => onCurrentFile(review, (path) => review.reading.toggleFolded(path)))]
	},
	{
		keys: 'Ctrl+Shift+Enter',
		does: 'Finish the review',
		presses: [{ key: 'Enter', held: 'command-and-shift', run: finish }]
	},
	{ keys: '?', does: 'Show this list', presses: [alone('?', (review) => review.guide.setHelpOpen(true))] }
];

/** What is held with a press, if it is anything the review answers; Alt is never the review's. */
function heldWith(event: KeyboardEvent): Held | null {
	if (event.altKey) return null;
	if (event.metaKey || event.ctrlKey) return event.shiftKey ? 'command-and-shift' : null;
	return 'nothing';
}

/** The press in the table this keystroke is, if any. */
function pressOf(event: KeyboardEvent): Press | undefined {
	const held = heldWith(event);
	return KEYMAP.flatMap((row) => row.presses).find((press) => press.key === event.key && press.held === held);
}

/**
 * Answer a keystroke the review has a key for. A key something on the page
 * has already answered is not the review's; while the help is open the keys
 * are the help's; while a field is being typed in, only a chord is the
 * review's.
 */
export function pressKey(review: Review, event: KeyboardEvent): void {
	if (event.defaultPrevented || review.guide.helpOpen) return;
	const press = pressOf(event);
	if (!press || (press.held === 'nothing' && isTypingTarget(event.target))) return;
	event.preventDefault();
	press.run(review);
}
