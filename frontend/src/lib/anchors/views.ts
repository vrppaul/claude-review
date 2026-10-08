/**
 * What the browser needs to know about each kind of anchor.
 *
 * A thread is named in its own header, in menus and in the panel, and is
 * brought into view from all of them. Each kind of anchor answers those
 * questions in its own module, so nothing that lists or jumps to threads
 * has to ask what a thread hangs on.
 */

import type { Anchor, AnchorKind, Comment, LineSide } from "$lib/types";
import { lineAnchorView } from "$lib/anchors/line";

export interface AnchorView<Kind extends Anchor> {
  /** In the thread's own header: "Line 42". */
  label(anchor: Kind): string;
  /** In full, where there is room: "src/a.py · Line 42". */
  place(anchor: Kind): string;
  /** In a chip or a menu row: "a.py Line 42". */
  shortPlace(anchor: Kind): string;
  /** The word a panel message mentions the thread by. */
  token(anchor: Kind): string;
  /** Which side of the diff it hangs on, when it hangs on the diff at all. */
  side(anchor: Kind): LineSide | null;
  /** Bring the thread into view. */
  reveal(threadId: string, anchor: Kind): void;
}

const VIEWS: {
  [Kind in AnchorKind]: AnchorView<Extract<Anchor, { kind: Kind }>>;
} = {
  line: lineAnchorView,
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

export function anchorSide(anchor: Anchor): LineSide | null {
  return viewOf(anchor).side(anchor);
}

export function revealThread(comment: Comment): void {
  viewOf(comment.anchor).reveal(comment.id, comment.anchor);
}
