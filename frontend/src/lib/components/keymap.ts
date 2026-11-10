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
 * review from inside a comment field is what it is for. A chord a field
 * answers itself — sending what it holds, asking the agent now — is listed
 * here, and pressed through `isPressed` in the field.
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
import type { Review } from '$lib/review/review.svelte';

/**
 * What the header's button that opens the help carries: where the keyboard
 * goes when the tour or a card of the guide goes, since the tour and the news
 * are found again in the help.
 */
export const HELP_BUTTON_ROLE = 'open-help';

/** The key of the column beside what is read, the tree or a story's contents, as its rail says it. */
export const COLUMN_KEY = 'f';

/** The key that brings the agent's column on screen to talk to it, as its rail says it. */
export const TALK_KEY = 'c';

/** A modifier held with a key, named by what it is on a PC and on a Mac. */
type Modifier = 'ctrl-or-cmd' | 'alt-or-option' | 'shift';

/** A key as it is pressed: the key, and every modifier held with it. Any other modifier held makes another chord. */
export interface Chord {
	key: string;
	held: readonly Modifier[];
}

// The modifiers, in the order a chord's name writes them
const MODIFIERS: readonly Modifier[] = ['ctrl-or-cmd', 'alt-or-option', 'shift'];
// A key that types a character carries Shift in it, ? being Shift and /: beside one, Shift is not read
const MODIFIERS_BESIDE_A_CHARACTER: readonly Modifier[] = MODIFIERS.filter((modifier) => modifier !== 'shift');

// Whether a keystroke holds each modifier: Cmd on a Mac counts as Ctrl, so a chord is pressed as each platform does
const MODIFIER_HELD: Record<Modifier, (event: KeyboardEvent) => boolean> = {
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

// Enter on a line's number, which comments on the line: the number is a button
const LINE_NUMBER_CHORD: Chord = { key: 'Enter', held: [] };

/** A chord the review answers, and what it does. */
interface Press {
	chord: Chord;
	run: (review: Review) => void;
}

/**
 * Who answers a row's chords: the review, which runs each press; or the
 * element they are pressed in — a field, a line's number — which answers
 * them itself, the help only naming them.
 */
type Answered = { by: 'the-review'; presses: readonly Press[] } | { by: 'its-element'; chords: readonly Chord[] };

/** Whether a row's keys do anything, as the review stands. */
type Live = (review: Review) => boolean;

/** One line of the help: its chords, what they do, who answers them, and where and when they are keys at all. */
interface KeyRow {
	/** Who answers the chords, and the chords: one, or two that do opposite things, in the order `does` names them. */
	answered: Answered;
	does: string;
	/**
	 * The ways of reading the review the keys act in. A key that is one
	 * view's own — the files have a tree to put away, and files to tick off
	 * and fold; a story has none — is neither answered nor listed in the other.
	 */
	views: readonly ReadingViewName[];
	/**
	 * Whether the keys do anything in such a view as the review stands: what
	 * they act on is drawn. The files draw no line of a diff that holds no
	 * file; a story's view draws nothing until a story is told.
	 */
	live: Live;
}

/** A line of the help as it is drawn: the names of its chords, and what they do. */
interface ListedKeys {
	keys: readonly string[];
	does: string;
}

// The keys of every view, of the files alone, and of the story alone
const EVERY_VIEW: readonly ReadingViewName[] = ['files', 'story'];
const THE_FILES: readonly ReadingViewName[] = ['files'];
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
		answered: {
			by: 'the-review',
			presses: [
				alone('j', (review) => review.sections.stepLine(1)),
				alone('k', (review) => review.sections.stepLine(-1))
			]
		},
		does: 'Down / up a line',
		views: EVERY_VIEW,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		answered: { by: 'its-element', chords: [LINE_NUMBER_CHORD] },
		does: 'Comment on this line',
		views: EVERY_VIEW,
		live: WHILE_LINES_ARE_DRAWN
	},
	// The chord in a comment or a message is the field's own: it knows where what it holds goes.
	// A message is written whatever is drawn
	{
		answered: { by: 'its-element', chords: [FIELD_CHORD] },
		does: 'Add the comment, or send the message, being written',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The ask chord is the comment field's own too, as is its Ask agent now
	{
		answered: { by: 'its-element', chords: [ASK_CHORD] },
		does: 'Ask the agent now about the comment being written',
		views: EVERY_VIEW,
		live: WHILE_A_COMMENT_CAN_BE_ASKED
	},
	{
		answered: { by: 'the-review', presses: SECTION_PRESSES },
		does: 'Next / previous file',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	// A story's sections are its pieces: every step, then what no step tells
	{
		answered: { by: 'the-review', presses: SECTION_PRESSES },
		does: 'Next / previous piece of the story',
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	// Threads are stepped through wherever they are drawn: under lines that take comments, or above
	// a diff that no longer holds their file, even one that holds no file at all
	{
		answered: {
			by: 'the-review',
			presses: [alone('n', (review) => review.navigator.step(1)), alone('p', (review) => review.navigator.step(-1))]
		},
		does: 'Next / previous comment',
		views: EVERY_VIEW,
		live: WHILE_THREADS_ARE_DRAWN
	},
	// An answer on a line the view does not draw is gone to in the files, whatever is on screen
	{
		answered: { by: 'the-review', presses: [alone('a', (review) => review.navigator.nextUnread())] },
		does: 'Next unread reply',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	{
		answered: { by: 'the-review', presses: [alone(TALK_KEY, talkToAgent)] },
		does: 'Talk to the agent',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	// The tree stands beside the files whatever the diff holds: of no file, it says so
	{
		answered: { by: 'the-review', presses: [alone(COLUMN_KEY, (review) => review.layout.fileTree.toggle())] },
		does: 'Show or hide the file tree',
		views: THE_FILES,
		live: ALWAYS
	},
	// The same key in a story is its own column's: the contents, not the tree it does not draw.
	// The contents stand beside a story's lines, and with none told there are none to put away
	{
		answered: { by: 'the-review', presses: [alone(COLUMN_KEY, (review) => review.layout.storyContents.toggle())] },
		does: 'Show or hide the contents',
		views: THE_STORY,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		answered: {
			by: 'the-review',
			presses: [alone('v', (review) => onCurrentFile(review, (path) => review.reading.toggleViewed(path)))]
		},
		does: 'Mark this file viewed',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		answered: {
			by: 'the-review',
			presses: [alone('u', (review) => onCurrentFile(review, (path) => review.reading.toggleFolded(path)))]
		},
		does: 'Fold or unfold this file',
		views: THE_FILES,
		live: WHILE_LINES_ARE_DRAWN
	},
	{
		answered: { by: 'the-review', presses: [{ chord: FINISH_CHORD, run: finish }] },
		does: 'Finish the review',
		views: EVERY_VIEW,
		live: ALWAYS
	},
	{
		answered: { by: 'the-review', presses: [alone('?', (review) => review.guide.setHelpOpen(true))] },
		does: 'Show this list',
		views: EVERY_VIEW,
		live: ALWAYS
	}
];

/** What a chord is called in the help and the hints: its modifiers, then its key. */
export function chordName(chord: Chord): string {
	const modifiers = MODIFIERS.filter((modifier) => chord.held.includes(modifier));
	return [...modifiers.map((modifier) => MODIFIER_NAMES[modifier]), chord.key].join(CHORD_NAME_JOINER);
}

/**
 * Whether a key types a character, and is called by it, rather than by a word: `?` rather than `Enter`. Every
 * key the review names is a character of one unit or a word of several.
 */
function typesACharacter(key: string): boolean {
	return key.length === 1;
}

/** Whether a keystroke is the chord: its key, with its modifiers held and no other. */
export function isPressed(chord: Chord, event: KeyboardEvent): boolean {
	if (event.key !== chord.key) return false;
	const read = typesACharacter(chord.key) ? MODIFIERS_BESIDE_A_CHARACTER : MODIFIERS;
	return read.every((modifier) => MODIFIER_HELD[modifier](event) === chord.held.includes(modifier));
}

/** The rows of the view on screen that do something as the review stands. */
function liveRows(review: Review): KeyRow[] {
	const onScreen = review.views.onScreen.name;
	return KEYMAP.filter((row) => row.views.includes(onScreen) && row.live(review));
}

/** The chords of a row, whoever answers them. */
function chordsOf(answered: Answered): readonly Chord[] {
	return answered.by === 'the-review' ? answered.presses.map((press) => press.chord) : answered.chords;
}

/** What the help lists: each live row's chords by name, and what they do. */
export function keysListed(review: Review): ListedKeys[] {
	return liveRows(review).map((row) => ({ keys: chordsOf(row.answered).map(chordName), does: row.does }));
}

/** The press this keystroke is among the chords the review answers as it stands, if any. */
function pressOf(review: Review, event: KeyboardEvent): Press | undefined {
	return liveRows(review)
		.flatMap((row) => (row.answered.by === 'the-review' ? row.answered.presses : []))
		.find((press) => isPressed(press.chord, event));
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
	if (!press || (press.chord.held.length === 0 && isTypingTarget(event.target))) return;
	event.preventDefault();
	press.run(review);
}
