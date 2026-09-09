import type { DiffLine, LineSide } from "$lib/types";

export interface LineRange {
  side: LineSide;
  line: number;
  endLine: number;
  /** Index of the last line in the flat hunk lines array where the comment box should render */
  anchorIndex: number;
}

/** A removed line only exists in the old file; everything else is the new one. */
export function lineSide(line: DiffLine): LineSide {
  return line.type === "delete" ? "old" : "new";
}

/** The number a line carries on its own side — old for removed, new otherwise. */
export function getLineNumber(line: DiffLine): number {
  return line.new_no ?? line.old_no ?? 0;
}

export function createLineSelection() {
  let commentingAt = $state<LineRange | null>(null);
  let dragSide = $state<LineSide | null>(null);
  let dragStart = $state<number | null>(null);
  let dragEnd = $state<number | null>(null);
  let dragAnchorIndex = $state<number | null>(null);
  let dragging = $state(false);

  return {
    get commentingAt() {
      return commentingAt;
    },
    get dragging() {
      return dragging;
    },

    reset() {
      commentingAt = null;
      dragSide = null;
      dragStart = null;
      dragEnd = null;
      dragAnchorIndex = null;
      dragging = false;
    },

    handleMouseDown(line: DiffLine, index: number) {
      const lineNo = getLineNumber(line);
      if (lineNo === 0) return;
      dragSide = lineSide(line);
      dragStart = lineNo;
      dragEnd = lineNo;
      dragAnchorIndex = index;
      dragging = true;
    },

    handleMouseEnter(line: DiffLine, index: number) {
      if (!dragging) return;
      // A range spans one side only: old line 42 and new line 42 are different
      // places, so dragging across the other side must not extend the range.
      if (lineSide(line) !== dragSide) return;
      const lineNo = getLineNumber(line);
      if (lineNo === 0) return;
      dragEnd = lineNo;
      dragAnchorIndex = Math.max(dragAnchorIndex ?? index, index);
    },

    handleMouseUp() {
      if (
        !dragging ||
        dragStart === null ||
        dragEnd === null ||
        dragSide === null
      )
        return;
      dragging = false;
      commentingAt = {
        side: dragSide,
        line: Math.min(dragStart, dragEnd),
        endLine: Math.max(dragStart, dragEnd),
        anchorIndex: dragAnchorIndex ?? 0,
      };
      dragSide = null;
      dragStart = null;
      dragEnd = null;
      dragAnchorIndex = null;
    },

    clearCommenting() {
      commentingAt = null;
    },

    isHighlighted(side: LineSide, lineNo: number): boolean {
      if (
        dragging &&
        dragSide === side &&
        dragStart !== null &&
        dragEnd !== null
      ) {
        if (
          lineNo >= Math.min(dragStart, dragEnd) &&
          lineNo <= Math.max(dragStart, dragEnd)
        ) {
          return true;
        }
      }
      if (commentingAt !== null && commentingAt.side === side) {
        return lineNo >= commentingAt.line && lineNo <= commentingAt.endLine;
      }
      return false;
    },

    getLineNumber,
    lineSide,
  };
}
