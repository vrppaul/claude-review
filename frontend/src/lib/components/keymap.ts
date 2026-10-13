/**
 * The keys the review answers: one table, which the keys run and the help
 * reads, so the two cannot say different things.
 *
 * A key on its own is the review's only while nothing is being typed — j in
 * a comment is a letter. A chord is the review's anywhere: finishing the
 * review from inside a comment field is what it is for.
 *
 * A row says which ways of reading the review its keys are keys of, and
 * when they do anything there. What is answered, and what the help lists,
 * are the rows of the view on screen that do something as the review
 * stands: a key of the files alone does nothing unseen while a story is
 * read, and no key is listed for what the view does not draw — a line of a
 * diff that holds no file, a piece of a story not told.
 */

import { isComposingText, isTypingTarget } from '$lib/dom/keyboard';
import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { Drawn } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';

/**
 * What the header's button that opens the help carries: where the keyboard
 * goes when the tour or a card of the guide goes, since the tour and the news
 * are found again in the help.
 */
export const HELP_BUTTON_ROLE = 'open-help';

/** The chord that finishes the review, as the help and the hints beside its button write it. */
export const FINISH_KEYS = 'Ctrl+Shift+Enter';

/**
 * The chord that sends what a field holds where it goes — a comment into the
 * review, a message to the agent — as the help and the hints beside the
 * fields write it.
 */
export const FIELD_KEYS = 'Ctrl+Enter';

/** What is held with a key: nothing, Ctrl (Cmd on a Mac), or Ctrl and Shift together. */
type Held = 'nothing' | 'command' | 'command-and-shift';

/** A key as it is pressed, and what it does. */
interface Press {
	key: string;
	held: Held;
	run: (review: Review) => void;
}

/** Whether a row's keys do anything, as the review stands. */
type Live = (review: Review) => boolean;

/** One line of the help: the keys as it writes them, what they do, each press, and where and when they are keys at all. */
export interface KeyRow {
	keys: string;
	does: string;
	presses: readonly Press[];
	/**
	 * The ways of reading the review the keys act in. A key that is one
	 * view's own — the files have a tree to put away, and files to tick off
	 * and fold; a story has none — is neither answered nor listed in the other.
	 */
	views: readonly ReadingViewName[];
	/**
	 * Whether the keys do anything in such a view as the review stands: what
	 * they act on is drawn. The files draw no line of a diff that holds no
	 * file; a story's view draws nothing until a story is told, and one told
	 * of another take takes no comment and carries none.
	 */
	live: Live;
}

// The keys of every view, of the files alone, and of the story alone
const EVERY_VIEW: readonly ReadingViewName[] = ['files', 'story'];
const THE_FILES: readonly ReadingViewName[] = ['files'];
const THE_STORY: readonly ReadingViewName[] = ['story'];

// What a view may say it draws that has lines in it to walk, and what has threads in it to step through
const DRAWN_WITH_LINES: readonly Drawn[] = ['lines', 'lines-taking-comments'];
const DRAWN_WITH_THREADS: readonly Drawn[] = ['threads-alone', 'lines-taking-comments'];

// When a row's keys do something: whatever is on screen; while the view on screen draws lines; while
// those lines take comments; and while it draws threads, on such lines or on none
const ALWAYS: Live = () => true;
const WHILE_LINES_ARE_DRAWN: Live = (review) => DRAWN_WITH_LINES.includes(review.views.onScreen.drawn());
const WHILE_LINES_TAKE_COMMENTS: Live = (review) => review.views.onScreen.drawn() === 'lines-taking-comments';
const WHILE_THREADS_ARE_DRAWN: Live = (review) => DRAWN_WITH_THREADS.includes(review.views.onScreen.drawn());

/** A key pressed on its own. */
function alone(key: string, run: (review: Review) => void): Press {
	return { key, held: 'nothing', run };
}

/**
 * Open the panel and put the cursor in it. Everything else in this review
 * can be done from the keyboard; talking to the agent should not be the one
 * thing that needs a mouse. With nobody listening the panel has no field to
 * write in, and the cursor is not asked for: a field drawn when an agent
 * arrives, long after, would take it from whatever the reader is typing then.
 */
function talkToAgent(review: Review): void {
	review.layout.agentPanel.setOpen(true);
	if (review.answerer.attached) review.layout.agentPanel.askForInput();
}

/** Do something to the file the reader is reading: the one a line of which has the keyboard, or else the one in view. */
function onCurrentFile(review: Review, act: (path: string) => void): void {
	const path = review.sections.currentFile();
	if (path) act(path);
}

// ] and [ walk the sections of whichever view is on screen; what a section is, each view's row says
const SECTION_PRESSES: readonly Press[] = [
	alone(']', (review) => review.navigator.stepSection(1)),
	alone('[', (review) => review.navigator.stepSection(-1))
];

/** The first press opens the pane the review is sent from; the second sends it. */
function finish(review: Review): void {
	if (review.submission.finishing) void review.submission.send();
	else review.submission.setFinishing(true);
}

const KEYMAP: readonly KeyRow[] = [
	{
		keys: 'j / k',
		does: 'Down / up a line',
		presses: [
			alone('j', (review) => review.sections.stepLine(1)),
			alone('k', (review) => review.sections.stepLine(-1))
		],
		views: EVERY_VIEW,
		live: WHILE_LINES_ARE_DRAWN
	},
	// Enter on a line's number is the number's own: it is a button
	{
		keys: 'Enter',
		does: 'Comment on this line',
		presses: [],
		views: EVERY_VIEW,
		live: WHILE_LINES_TAKE_COMMENTS
	},
	// The chord in a comment or a message is the field's own: it knows where what it holds goes.
	// A message is written whatever is drawn
	{
		keys: FIELD_KEYS,
		does: 'Add the comment, or send the message, being written',
		presses: [],
		views: EVERY_VIEW,
		live: ALWAYS
	},
	{
		keys: '] / [',
		does: 'Next / previous file',
		presses: SECTION_PRESSES,
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	// A story's sections are its pieces: every step, then what no step tells
	{
		keys: '] / [',
		does: 'Next / previous piece of the story',
		presses: SECTION_PRESSES,
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	// Threads are stepped through wherever they are drawn: under lines that take comments, or above
	// a diff that no longer holds their file, even one that holds no file at all
	{
		keys: 'n / p',
		does: 'Next / previous comment',
		presses: [alone('n', (review) => review.navigator.step(1)), alone('p', (review) => review.navigator.step(-1))],
		views: EVERY_VIEW,
		live: WHILE_THREADS_ARE_DRAWN
	},
	// An answer on a line the view does not draw is gone to in the files, whatever is on screen
	{
		keys: 'a',
		does: 'Next unread reply',
		presses: [alone('a', (review) => review.navigator.nextUnread())],
		views: EVERY_VIEW,
		live: ALWAYS
	},
	{ keys: 'c', does: 'Talk to the agent', presses: [alone('c', talkToAgent)], views: EVERY_VIEW, live: ALWAYS },
	// The tree stands beside the files whatever the diff holds: of no file, it says so
	{
		keys: 'f',
		does: 'Show or hide the file tree',
		presses: [alone('f', (review) => review.layout.fileTree.toggle())],
		views: THE_FILES,
		live: ALWAYS
	},
	// The same key in a story is its own column's: the contents, not the tree it does not draw.
	// The contents stand beside a story's lines, and with none told there are none to put away
	{
		keys: 'f',
		does: 'Show or hide the contents',
		presses: [alone('f', (review) => review.layout.storyContents.toggle())],
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		keys: 'v',
		does: 'Mark this file viewed',
		presses: [alone('v', (review) => onCurrentFile(review, (path) => review.reading.toggleViewed(path)))],
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		keys: 'u',
		does: 'Fold or unfold this file',
		presses: [alone('u', (review) => onCurrentFile(review, (path) => review.reading.toggleFolded(path)))],
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		keys: FINISH_KEYS,
		does: 'Finish the review',
		presses: [{ key: 'Enter', held: 'command-and-shift', run: finish }],
		views: EVERY_VIEW,
		live: ALWAYS
	},
	{
		keys: '?',
		does: 'Show this list',
		presses: [alone('?', (review) => review.guide.setHelpOpen(true))],
		views: EVERY_VIEW,
		live: ALWAYS
	}
];

/**
 * The keys that do something as the review stands: those of the view on
 * screen whose rows are live. What is answered, and what the help lists.
 */
export function keysOf(review: Review): KeyRow[] {
	const onScreen = review.views.onScreen.name;
	return KEYMAP.filter((row) => row.views.includes(onScreen) && row.live(review));
}

/** What is held with a press, if it is anything the review answers; Alt is never the review's. */
function heldWith(event: KeyboardEvent): Held | null {
	if (event.altKey) return null;
	if (event.metaKey || event.ctrlKey) return event.shiftKey ? 'command-and-shift' : 'command';
	return 'nothing';
}

/** Whether a keystroke in a field is the field's chord: Enter with Ctrl, never with Shift — that finishes the review. */
export function isFieldChord(event: KeyboardEvent): boolean {
	return event.key === 'Enter' && heldWith(event) === 'command';
}

/** The press this keystroke is among the keys that do something as the review stands, if any. */
function pressOf(review: Review, event: KeyboardEvent): Press | undefined {
	const held = heldWith(event);
	return keysOf(review)
		.flatMap((row) => row.presses)
		.find((press) => press.key === event.key && press.held === held);
}

/**
 * Answer a keystroke the review has a key for. A key something on the page
 * has already answered is not the review's, nor one an input method is
 * composing a word with; while the help is open the keys are the help's;
 * while a field is being typed in, only a chord is the review's.
 */
export function pressKey(review: Review, event: KeyboardEvent): void {
	if (event.defaultPrevented || isComposingText(event) || review.guide.helpOpen) return;
	const press = pressOf(review, event);
	if (!press || (press.held === 'nothing' && isTypingTarget(event.target))) return;
	event.preventDefault();
	press.run(review);
}
