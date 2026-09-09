import type { DiffFile, DiffHunk, DiffLine } from "$lib/types";

/** How many lines one click reveals. */
export const EXPAND_STEP = 20;

/** A gap this small is not worth revealing a piece at a time. */
export const EXPAND_ALL_BELOW = 60;

/**
 * How many lines are still hidden above a hunk.
 *
 * A hunk starts where the one before it ended plus whatever the diff left
 * out. Lines already revealed count against that, so the gap closes as it is
 * expanded.
 */
export function hiddenAbove(
  hunks: DiffHunk[],
  index: number,
  revealed: number,
): number {
  const previous = hunks[index - 1];
  const previousEnd = previous ? lastNewLine(previous) : 0;
  const gap = hunks[index].new_start - previousEnd - 1;
  return Math.max(0, gap - revealed);
}

/** The line range one click should ask for, or null when nothing is hidden. */
export function nextWindow(
  hunks: DiffHunk[],
  index: number,
  revealed: number,
  step: number = EXPAND_STEP,
): { start: number; end: number } | null {
  const hidden = hiddenAbove(hunks, index, revealed);
  if (hidden <= 0) return null;

  const end = hunks[index].new_start - revealed - 1;
  const wanted = hidden <= EXPAND_ALL_BELOW ? hidden : step;
  return { start: Math.max(1, end - wanted + 1), end };
}

/**
 * The file as it should be drawn, with revealed lines folded into the hunks.
 *
 * Revealed lines are unchanged context, so putting them inside the hunk they
 * sit above means line numbering, highlighting and comment anchoring all
 * treat them like any other context line, with nothing to special-case.
 */
export function withRevealed(
  file: DiffFile,
  revealed: Map<number, DiffLine[]>,
): DiffFile {
  if (revealed.size === 0) return file;

  return {
    ...file,
    hunks: file.hunks.map((hunk, index) => {
      const extra = revealed.get(index);
      if (!extra || extra.length === 0) return hunk;
      return { ...hunk, lines: [...extra, ...hunk.lines] };
    }),
  };
}

/** Turn fetched text into context lines numbered from `start`. */
export function toContextLines(start: number, lines: string[]): DiffLine[] {
  return lines.map((content, offset) => ({
    type: "context" as const,
    old_no: null,
    new_no: start + offset,
    content,
  }));
}

function lastNewLine(hunk: DiffHunk): number {
  for (let i = hunk.lines.length - 1; i >= 0; i -= 1) {
    const line = hunk.lines[i];
    if (line.new_no !== null) return line.new_no;
  }
  return hunk.new_start - 1;
}
