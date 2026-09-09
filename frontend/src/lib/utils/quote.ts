import type { DiffHunk, DiffLine, LineSide } from "$lib/types";

/** A removed line only exists in the old file; everything else is the new one. */
function sideOf(line: DiffLine): LineSide {
  return line.type === "delete" ? "old" : "new";
}

function numberOf(line: DiffLine): number {
  return line.new_no ?? line.old_no ?? 0;
}

/**
 * The text of the lines a comment covers.
 *
 * Sent with a question so the Claude answering can see what is meant without
 * having the file to hand, and used to start a suggested replacement.
 */
export function linesInRange(
  hunks: DiffHunk[],
  side: LineSide,
  startLine: number,
  endLine: number,
): string[] {
  return hunks
    .flatMap((hunk) => hunk.lines)
    .filter(
      (line) =>
        sideOf(line) === side &&
        numberOf(line) >= startLine &&
        numberOf(line) <= endLine,
    )
    .map((line) => line.content);
}
