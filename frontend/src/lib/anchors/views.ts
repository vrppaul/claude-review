/**
 * What the browser needs to know about each kind of anchor.
 *
 * A thread is named in its own header, in menus and in the panel, and a
 * panel message mentions it by a token. Each kind of anchor answers those
 * questions in its own module, so naming, matching and mentioning a thread
 * never asks what it hangs on. Drawing one on the lines it hangs on still
 * does — only line anchors are drawn on a file — and bringing one into view
 * moves the page, which is the review's `ThreadNavigator`.
 */

import type { Anchor, AnchorKind } from '$lib/types';
import { lineAnchorView } from '$lib/anchors/line';

export interface AnchorView<Kind extends Anchor> {
	/** In the thread's own header: "Line 42". */
	label(anchor: Kind): string;
	/** In full, where there is room: "src/a.py · Line 42". */
	place(anchor: Kind): string;
	/** In a chip or a menu row: "a.py Line 42". */
	shortPlace(anchor: Kind): string;
	/** The word a panel message mentions the thread by. */
	token(anchor: Kind): string;
	/** Whether a message mentions the thread by its token. */
	mentionedIn(text: string, anchor: Kind): boolean;
	/** Whether two anchors of this kind hang on the same spot. */
	sameSpot(one: Kind, other: Kind): boolean;
	/** The file it hangs on, for a kind that hangs on one. */
	fileOf(anchor: Kind): string | null;
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

export function anchorMentionedIn(text: string, anchor: Anchor): boolean {
	return viewOf(anchor).mentionedIn(text, anchor);
}

/** Whether two anchors hang on the same spot; anchors of different kinds never do. */
export function sameSpot(one: Anchor, other: Anchor): boolean {
	return one.kind === other.kind && viewOf(one).sameSpot(one, other);
}

export function anchorFile(anchor: Anchor): string | null {
	return viewOf(anchor).fileOf(anchor);
}
