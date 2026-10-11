/**
 * What the browser needs to know about each kind of anchor.
 *
 * A thread is named in its own header, in menus and in the panel, a panel
 * message mentions it by a token, and it is drawn under the lines of a file
 * it hangs on, if it hangs on any. Each kind of anchor answers those
 * questions in its own module, so naming, matching, mentioning and drawing a
 * thread never ask what it hangs on; bringing one into view moves the page,
 * which is the review's `Navigator`.
 *
 * Each answer is a function property rather than a method, so a kind's view
 * is held to anchors of that kind: methods are compared loosely, and with a
 * second kind `viewOf` would still compile, handing one kind's anchor to the
 * other's view. As properties, a second kind stops `viewOf` compiling until
 * it is told which view each kind is answered by.
 */

import type { Anchor, AnchorKind, LineAnchor } from '$lib/types';
import { lineAnchorView } from '$lib/anchors/line';

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
	/** The lines of a file it hangs on, for a kind drawn under a file's lines; null for one that is not. */
	linesOf: (anchor: Kind) => LineAnchor | null;
}

const VIEWS: {
	[Kind in AnchorKind]: AnchorView<Extract<Anchor, { kind: Kind }>>;
} = {
	line: lineAnchorView
};

function viewOf(anchor: Anchor): AnchorView<Anchor> {
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

/** Whether two anchors hang on the same spot. */
export function sameSpot(one: Anchor, other: Anchor): boolean {
	return viewOf(one).sameSpot(one, other);
}

/** The lines of a file an anchor hangs on; null for a kind that hangs on none. */
export function anchorLines(anchor: Anchor): LineAnchor | null {
	return viewOf(anchor).linesOf(anchor);
}
