import type { Comment, DiffHunk, DiffLine, LineSide } from "$lib/types";

/** A removed line only exists in the old file; everything else is the new one. */
function sideOf(line: DiffLine): LineSide {
  return line.type === "delete" ? "old" : "new";
}

function numberOf(line: DiffLine): number {
  return line.new_no ?? line.old_no ?? 0;
}

/** Every line of one side of a file, in order, with the number it has there. */
function linesOfSide(
  hunks: DiffHunk[],
  side: LineSide,
): { no: number; content: string }[] {
  return hunks
    .flatMap((hunk) => hunk.lines)
    .filter((line) => sideOf(line) === side)
    .map((line) => ({ no: numberOf(line), content: line.content }));
}

function matchesAt(
  lines: { content: string }[],
  at: number,
  quote: string[],
): boolean {
  return quote.every((text, offset) => lines[at + offset]?.content === text);
}

/**
 * The lines a thread hangs on, as the diff on screen has them.
 *
 * A thread the reader opens keeps what they selected. One raised from
 * outside the browser has only numbers, so the lines are read off the diff
 * here — without them the thread cannot follow its code when it moves, or
 * say what it was written against when the code is gone.
 */
export function quoteFrom(
  hunks: DiffHunk[] | null,
  side: LineSide,
  startLine: number,
  endLine: number,
): string[] {
  if (!hunks) return [];
  return linesOfSide(hunks, side)
    .filter((line) => line.no >= startLine && line.no <= endLine)
    .map((line) => line.content);
}

export interface Anchor {
  start_line: number;
  end_line: number;
  outdated: boolean;
}

/**
 * Where a thread hangs once the diff has been taken again.
 *
 * A comment is written about lines, not about numbers: work moves them, and
 * a thread left on its old numbers ends up describing whatever slid into
 * their place. So the lines it was written against are looked for, and the
 * anchor follows them — or, when they are gone, the thread says so instead
 * of pointing somewhere it no longer belongs.
 */
export function reanchor(comment: Comment, hunks: DiffHunk[] | null): Anchor {
  const unchanged = {
    start_line: comment.start_line,
    end_line: comment.end_line,
  };

  // Nothing to search for: a thread from before quotes were kept, or one on
  // lines that were never in the diff. Leaving it be beats guessing.
  if (comment.quote.length === 0) return { ...unchanged, outdated: false };
  if (!hunks) return { ...unchanged, outdated: true };

  const lines = linesOfSide(hunks, comment.side);
  const at = lines.findIndex((_, index) =>
    matchesAt(lines, index, comment.quote),
  );
  if (at === -1) return { ...unchanged, outdated: true };

  return {
    start_line: lines[at].no,
    end_line: lines[at + comment.quote.length - 1].no,
    outdated: false,
  };
}
