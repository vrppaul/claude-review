/**
 * The keys the review answers: one table, which the keys run and the help
 * reads, so the two cannot say different things.
 *
 * Every key is a chord, written once as data: the key and the modifiers held
 * with it. Whether a keystroke is that chord, and the name the help and the
 * hints give it, are both read from it, so a chord added is a row of data,
 * never a new reading of a keystroke.
 *
 * A key on its own is the review's only while nothing is being typed — j in
 * a comment is a letter. A chord is the review's anywhere: finishing the
 * review from inside a comment field is what it is for. A chord the element
 * it is pressed in answers itself — a field sending what it holds, a line's
 * number commenting on its line — is listed here without a run, and the
 * element presses it through `isPressed`.
 *
 * A row says which ways of reading the review its keys are keys of, and
 * when they do anything there. What is answered, and what the help lists,
 * are the rows of the view on screen that do something as the review
 * stands: a key of the files alone does nothing unseen while a story is
 * read, and no key is listed for what the view does not draw — a line of a
 * diff that holds no file, a piece of a story not told.
 */

import { isComposingText, isTypingTarget } from '$lib/dom/keyboard';
import type { ReadingViewName } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import type { ListedKeys } from '$lib/ui/key-list';

/**
 * What the header's button that opens the help carries: where the keyboard
 * goes when the tour or a card of the guide goes, since the tour and the news
 * are found again in the help.
 */
export const HELP_BUTTON_ROLE = 'open-help';

/** A modifier held with a key, named by what it is on a PC and on a Mac. */
type Modifier = 'ctrl-or-cmd' | 'alt-or-option' | 'shift';

/**
 * A key as it is pressed: the key, and every modifier held with it. Any other
 * modifier held makes another chord. A key that types a character carries
 * Shift in the character, ? being Shift and /, so such a chord holds no Shift.
 */
export interface Chord {
	key: string;
	held: readonly Modifier[];
}

/**
 * A press of the pointer with every modifier held with it: listed in the
 * help as a key is, and answered by what it presses, never by a keystroke.
 */
export interface PointerChord {
	pointer: 'click';
	held: readonly Modifier[];
}

// The modifiers, in the order a chord's name writes them
const MODIFIERS: readonly Modifier[] = ['ctrl-or-cmd', 'alt-or-option', 'shift'];
// What is read beside a key that types a character: Shift is in the character
const MODIFIERS_BESIDE_A_CHARACTER: readonly Modifier[] = MODIFIERS.filter((modifier) => modifier !== 'shift');
// How long a key that types a character is called: by the character, one unit; a key that types none is called by a
// word, Enter
const CHARACTER_KEY_LENGTH = 1;

/** What a keystroke or a press of the pointer says of the modifiers held with it. */
type HeldWith = Pick<KeyboardEvent, 'ctrlKey' | 'metaKey' | 'altKey' | 'shiftKey'>;

// Whether a keystroke or a press holds each modifier: Cmd on a Mac counts as Ctrl, so a chord is pressed as each
// platform does
const MODIFIER_HELD: Record<Modifier, (event: HeldWith) => boolean> = {
	'ctrl-or-cmd': (event) => event.ctrlKey || event.metaKey,
	'alt-or-option': (event) => event.altKey,
	shift: (event) => event.shiftKey
};

// What each modifier is called in a chord's name, and what joins the parts of the name: Ctrl+Shift+Enter
const MODIFIER_NAMES: Record<Modifier, string> = { 'ctrl-or-cmd': 'Ctrl', 'alt-or-option': 'Alt', shift: 'Shift' };
const CHORD_NAME_JOINER = '+';

/** The chord that sends what a field holds where it goes: a comment into the review, a message to the agent. */
export const FIELD_CHORD: Chord = { key: 'Enter', held: ['ctrl-or-cmd'] };

/** The chord that hands a comment being written to the agent at once. */
export const ASK_CHORD: Chord = { key: 'Enter', held: ['alt-or-option'] };

/** The chord that finishes the review. */
export const FINISH_CHORD: Chord = { key: 'Enter', held: ['ctrl-or-cmd', 'shift'] };

/** The key that opens the help, and closes it again. */
export const HELP_CHORD: Chord = { key: '?', held: [] };

/** The key of the column beside what is read, the tree or a story's contents, as its rail says it. */
export const COLUMN_CHORD: Chord = { key: 'f', held: [] };

/** The key that brings the agent's column on screen to talk to it, as its rail says it. */
export const TALK_CHORD: Chord = { key: 'c', held: [] };

// Enter on a line's number, which comments on the line: the number is a button
const LINE_NUMBER_CHORD: Chord = { key: 'Enter', held: [] };

/**
 * A click on a name in the code with Ctrl held, Cmd on a Mac, which asks where the name is defined and used: the
 * code's lines answer it (LineNaming).
 */
export const LOOKUP_CHORD: PointerChord = { pointer: 'click', held: ['ctrl-or-cmd'] };

/** A chord of the help's, and what the review does on it. */
interface Press {
	chord: Chord;
	/** None where the element it is pressed in — a field, a line's number — answers it, the help only naming it. */
	run?: (review: Review) => void;
}

/** Whether a row's keys do anything, as the review stands. */
type Live = (review: Review) => boolean;

/** One line of the help: what its presses do, and where and when they do anything at all. */
interface HelpRow {
	does: string;
	/**
	 * The views the keys act in. A key that is some views' own — the
	 * change's files have files to walk, tick off and fold, and the tree
	 * beside them, as a file read alone has; a story has none of these — is
	 * neither answered nor listed in the others.
	 */
	views: readonly ReadingViewName[];
	/**
	 * Whether the keys do anything in such a view as the review stands: what
	 * they act on is drawn. The files draw no line of a diff that holds no
	 * file; a story's view draws nothing until a story is told.
	 */
	live: Live;
}

/** A line of the help of keys the review answers. */
interface KeyRow extends HelpRow {
	/** One, or two that do opposite things, in the order `does` names them. */
	presses: readonly Press[];
}

/** A line of the help of a press of the pointer, which what it presses answers. */
interface PointerRow extends HelpRow {
	pointer: PointerChord;
}

// The keys of every view; of the change's files alone; of the views the tree stands beside, those files and a file
// read alone; and of the story alone
const EVERY_VIEW: readonly ReadingViewName[] = ['files', 'story', 'file-alone'];
const THE_FILES: readonly ReadingViewName[] = ['files'];
const BESIDE_THE_TREE: readonly ReadingViewName[] = ['files', 'file-alone'];
const THE_STORY: readonly ReadingViewName[] = ['story'];

// When a row's keys do something: whatever is on screen; while the view on screen draws lines, which
// take comments; and while it draws threads, on such lines or on none. Each asks the view of the one
// thing its keys act on
const ALWAYS: Live = () => true;
const WHILE_LINES_ARE_DRAWN: Live = (review) => review.views.onScreen.drawn().lines;
const WHILE_THREADS_ARE_DRAWN: Live = (review) => review.views.onScreen.drawn().threads;
// While a comment can be written and asked about: an agent can be asked, which is when a field offers Ask agent
// now, and threads are drawn, there being lines to comment on or a thread to reply in
const WHILE_A_COMMENT_CAN_BE_ASKED: Live = (review) => review.canAsk && review.views.onScreen.drawn().threads;
// While the page has taken the reader from a place in the diff on screen, which Back takes them to
const WHILE_THERE_IS_A_WAY_BACK: Live = (review) => review.wayBack.top !== null;
// While the view draws lines where names are pointed at: of a repository's change, in a browser that lends the way
const WHILE_NAMES_ARE_LOOKED_UP: Live = (review) => review.namePointing !== null && review.views.onScreen.drawn().lines;

/** A key pressed on its own. */
function alone(key: string, run: (review: Review) => void): Press {
	return { chord: { key, held: [] }, run };
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
		presses: [
			alone('j', (review) => review.sections.stepLine(1)),
			alone('k', (review) => review.sections.stepLine(-1))
		],
		does: 'Down / up a line',
		views: EVERY_VIEW,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		presses: [{ chord: LINE_NUMBER_CHORD }],
		does: 'Comment on this line',
		views: EVERY_VIEW,
		live: WHILE_LINES_ARE_DRAWN
	},
	// The chord in a comment or a message is the field's own: it knows where what it holds goes.
	// A message is written whatever is drawn
	{
		presses: [{ chord: FIELD_CHORD }],
		does: 'Add the comment, or send the message, being written',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The ask chord is the comment field's own too, as is its Ask agent now
	{
		presses: [{ chord: ASK_CHORD }],
		does: 'Ask the agent now about the comment being written',
		views: EVERY_VIEW,
		live: WHILE_A_COMMENT_CAN_BE_ASKED
	},
	{
		presses: SECTION_PRESSES,
		does: 'Next / previous file',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	// A story's sections are its pieces: every step, then what no step tells
	{
		presses: SECTION_PRESSES,
		does: 'Next / previous piece of the story',
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	// Threads are stepped through wherever they are drawn: under lines that take comments, or above
	// a diff that no longer holds their file, even one that holds no file at all
	{
		presses: [alone('n', (review) => review.navigator.step(1)), alone('p', (review) => review.navigator.step(-1))],
		does: 'Next / previous comment',
		views: EVERY_VIEW,
		live: WHILE_THREADS_ARE_DRAWN
	},
	// An answer on a line the view does not draw is gone to in the files, whatever is on screen
	{
		presses: [alone('a', (review) => review.navigator.nextUnread())],
		does: 'Next unread reply',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The place left is gone back to in the view it was left in, whatever is on screen
	{
		presses: [alone('b', (review) => void review.navigator.goBack())],
		does: 'Back to where you were',
		views: EVERY_VIEW,
		live: WHILE_THERE_IS_A_WAY_BACK
	},
	{
		presses: [{ chord: TALK_CHORD, run: talkToAgent }],
		does: 'Talk to the agent',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The tree stands beside the files whatever the diff holds: of no file, it says so
	{
		presses: [{ chord: COLUMN_CHORD, run: (review) => review.layout.fileTree.toggle() }],
		does: 'Show or hide the file tree',
		views: BESIDE_THE_TREE,
		live: ALWAYS
	},
	// The same key in a story is its own column's: the contents, not the tree it does not draw.
	// The contents stand beside a story's lines, and with none told there are none to put away
	{
		presses: [{ chord: COLUMN_CHORD, run: (review) => review.layout.storyContents.toggle() }],
		does: 'Show or hide the contents',
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		presses: [alone('v', (review) => onCurrentFile(review, (path) => review.reading.toggleViewed(path)))],
		does: 'Mark this file viewed',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		presses: [alone('u', (review) => onCurrentFile(review, (path) => review.reading.toggleFolded(path)))],
		does: 'Fold or unfold this file',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		presses: [{ chord: FINISH_CHORD, run: finish }],
		does: 'Finish the review',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The help, once open, closes on the same key itself
	{
		presses: [{ chord: HELP_CHORD, run: (review) => review.guide.setHelpOpen(true) }],
		does: 'Show this list',
		views: EVERY_VIEW,
		live: ALWAYS
	}
];

// The presses of the pointer the help lists after the keys
const POINTER_ROWS: readonly PointerRow[] = [
	{
		pointer: LOOKUP_CHORD,
		does: 'Where a name in the code is defined and used',
		views: EVERY_VIEW,
		live: WHILE_NAMES_ARE_LOOKED_UP
	}
];

/** What a chord is called in the help and the hints: its modifiers, then its key. */
export function chordName(chord: Chord): string {
	return heldWith(chord.held, chord.key);
}

/** What a press of the pointer is called in the help and the hints: its modifiers, then the press. */
export function pointerChordName(chord: PointerChord): string {
	return heldWith(chord.held, chord.pointer);
}

/** The name of what is pressed with modifiers held: the modifiers in their order, then what is pressed. */
function heldWith(held: readonly Modifier[], pressed: string): string {
	const modifiers = MODIFIERS.filter((modifier) => held.includes(modifier));
	return [...modifiers.map((modifier) => MODIFIER_NAMES[modifier]), pressed].join(CHORD_NAME_JOINER);
}

/** Whether a keystroke is the chord: its key, with its modifiers held and no other. */
export function isPressed(chord: Chord, event: KeyboardEvent): boolean {
	if (event.key !== chord.key) return false;
	const read = chord.key.length === CHARACTER_KEY_LENGTH ? MODIFIERS_BESIDE_A_CHARACTER : MODIFIERS;
	return holdsOnly(read, chord.held, event);
}

/**
 * Whether a press of the pointer, a move of it or a keystroke holds the modifiers of a press of the pointer, and
 * no other: what the press is made with, and what holds the name under the pointer marked.
 */
export function holdsModifiersOf(chord: PointerChord, event: HeldWith): boolean {
	return holdsOnly(MODIFIERS, chord.held, event);
}

/** Whether, of the modifiers read, the event holds those held and no other. */
function holdsOnly(read: readonly Modifier[], held: readonly Modifier[], event: HeldWith): boolean {
	return read.every((modifier) => MODIFIER_HELD[modifier](event) === held.includes(modifier));
}

/** The rows of a list of the view on screen that do something as the review stands. */
function liveRows<Row extends HelpRow>(rows: readonly Row[], review: Review): Row[] {
	const onScreen = review.views.onScreen.name;
	return rows.filter((row) => row.views.includes(onScreen) && row.live(review));
}

/** What the help lists: each live row's chords by name, then its presses of the pointer, and what they do. */
export function keysListed(review: Review): ListedKeys[] {
	const keys = liveRows(KEYMAP, review).map((row) => ({
		keys: row.presses.map((press) => chordName(press.chord)),
		does: row.does
	}));
	const pointerPresses = liveRows(POINTER_ROWS, review).map((row) => ({
		keys: [pointerChordName(row.pointer)],
		does: row.does
	}));
	return [...keys, ...pointerPresses];
}

/**
 * What the review does at a keystroke it has a key for; nothing at any
 * other. A key something on the page has already answered is not the
 * review's, nor one an input method is composing a word with; while the help
 * is open the keys are the help's; while a field is being typed in, only a
 * chord is the review's.
 */
function answerTo(review: Review, event: KeyboardEvent): Press['run'] {
	if (event.defaultPrevented || isComposingText(event) || review.guide.helpOpen) return undefined;
	const press = liveRows(KEYMAP, review)
		.flatMap((row) => row.presses)
		.find((candidate) => isPressed(candidate.chord, event));
	// A chord the element it is pressed in answers is left to it
	if (press === undefined || (press.chord.held.length === 0 && isTypingTarget(event.target))) return undefined;
	return press.run;
}

/**
 * Whether the review answers a keystroke, as it stands: asked by what holds
 * the keyboard apart from where the reader reads, before the review hears
 * the key.
 */
export function answersKey(review: Review, event: KeyboardEvent): boolean {
	return answerTo(review, event) !== undefined;
}

/** Answer a keystroke the review has a key for. */
export function pressKey(review: Review, event: KeyboardEvent): void {
	const answer = answerTo(review, event);
	if (answer === undefined) return;
	event.preventDefault();
	answer(review);
}
