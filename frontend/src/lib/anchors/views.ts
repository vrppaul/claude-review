/**
 * What the browser needs to know about each kind of anchor.
 *
 * A thread is named in its own header, in menus and in the panel. Each
 * kind of anchor answers that in its own module, so nothing that lists
 * threads has to ask what a thread hangs on. Bringing one into view moves
 * the page, and is the review's `ThreadNavigator`.
 */

import type { Anchor, AnchorKind, LineSide } from "$lib/types";
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
