/**
 * What the browser needs to know about each kind of anchor.
 *
 * A thread is named in its own header, in menus and in the panel, a panel
 * message mentions it by a token, it is drawn under what it hangs on — lines
 * of a file, or a block of the story's words — it shows what it was written
 * against once that is gone, as code or as words, and a suggestion in it
 * shows what it replaces. Each kind of anchor answers those questions in its
 * own module, so naming, matching and mentioning a thread never ask what it
 * hangs on; drawing one asks where (`ThreadPlace`), and bringing one into
 * view moves the page, which is the review's `Navigator`.
 *
 * Each answer that reads the anchor is a function property rather than a
 * method, so a kind's view is held to anchors of that kind: methods are
 * compared loosely, and with a second kind `viewOf` would still compile,
 * handing one kind's anchor to the other's view. As properties, a new kind
 * stops `viewOf` compiling until it is told which view each kind is
 * answered by.
 */

import type { Anchor, AnchorKind, LineAnchor, StoryBlock, Thread } from '$lib/types';
import { lineAnchorView } from '$lib/anchors/line';
import { storyAnchorView } from '$lib/anchors/story';

/** The lines of a file a thread hangs on, whichever kind of anchor says so. */
export type FileLines = Pick<LineAnchor, 'file' | 'side' | 'start_line' | 'end_line'>;

/**
 * Where a thread is drawn: under lines of a file, or under a block of the
 * story's words. Every part of the page that draws threads, or goes to one,
 * says what it does with each.
 */
export type ThreadPlace = { on: 'lines'; lines: FileLines } | { on: 'story'; block: StoryBlock };

/**
 * How what a thread was written against reads: as lines of code, each kept
 * whole as it stood, or as words that wrap to the width they are given.
 */
export type QuoteReads = 'code' | 'prose';

/** A thread, with the lines of a file it hangs on. */
export interface ThreadOnLines {
	thread: Thread;
	lines: FileLines;
}

export interface AnchorView<Kind extends Anchor> {
	/** In the thread's own header: "Line 42". */
	label: (anchor: Kind) => string;
	/** In full, where there is room: "src/a.py · Line 42". */
	place: (anchor: Kind) => string;
	/** In a chip or a menu row: "a.py Line 42". */
	shortPlace: (anchor: Kind) => string;
	/** The word a panel message mentions the thread by. */
	token: (anchor: Kind) => string;
	/** Where a message mentions the thread by its token, and not by a longer one: where each mention starts. */
	mentionsIn: (text: string, anchor: Kind) => number[];
	/** Whether two anchors of this kind hang on the same spot. */
	sameSpot: (one: Kind, other: Kind) => boolean;
	/** What the comment was written against, as it read then: shown once the place it hangs on is gone. */
	writtenAgainst: (anchor: Kind) => string[];
	/** How that reads, the same for every anchor of the kind. */
	quoteReads: QuoteReads;
	/** What a suggestion in the thread replaces, a line to each; nothing where no suggestion replaces anything. */
	replaces: (anchor: Kind) => string[];
	/** Where the thread is drawn. */
	placeOf: (anchor: Kind) => ThreadPlace;
}

/** Each kind of anchor, by its kind. */
export type AnchorOfKind = { [Kind in AnchorKind]: Extract<Anchor, { kind: Kind }> };

const VIEWS: { [Kind in AnchorKind]: AnchorView<AnchorOfKind[Kind]> } = {
	line: lineAnchorView,
	story: storyAnchorView
};

/**
 * The view of an anchor's own kind. Taken as `AnchorOfKind[Kind]`, the anchor
 * stays paired with its kind, so the compiler holds the table to a view of
 * each kind. Handed any anchor, it hands back a view said to take any: its
 * own kind's, which is only ever given the anchor it was looked up by.
 */
function viewOf<Kind extends AnchorKind>(anchor: AnchorOfKind[Kind]): AnchorView<AnchorOfKind[Kind]> {
	return VIEWS[anchor.kind];
}

export function anchorLabel(anchor: Anchor): string {
	return viewOf(anchor).label(anchor);
}

export function anchorPlace(anchor: Anchor): string {
	return viewOf(anchor).place(anchor);
}

export function anchorShortPlace(anchor: Anchor): string {
	return viewOf(anchor).shortPlace(anchor);
}

export function anchorToken(anchor: Anchor): string {
	return viewOf(anchor).token(anchor);
}

export function anchorMentionsIn(text: string, anchor: Anchor): number[] {
	return viewOf(anchor).mentionsIn(text, anchor);
}

/** Whether two anchors hang on the same spot: never, for anchors of two kinds. */
export function sameSpot(one: Anchor, other: Anchor): boolean {
	return one.kind === other.kind && viewOf(one).sameSpot(one, other);
}

/** What a comment on an anchor was written against, as it read then. */
export function anchorWrittenAgainst(anchor: Anchor): string[] {
	return viewOf(anchor).writtenAgainst(anchor);
}

/** How what a comment on an anchor was written against reads. */
export function anchorQuoteReads(anchor: Anchor): QuoteReads {
	return viewOf(anchor).quoteReads;
}

/** What a suggestion in a thread on an anchor replaces. */
export function anchorReplaces(anchor: Anchor): string[] {
	return viewOf(anchor).replaces(anchor);
}

/** Where a thread on an anchor is drawn. */
export function threadPlaceOf(anchor: Anchor): ThreadPlace {
	return viewOf(anchor).placeOf(anchor);
}
