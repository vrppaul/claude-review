import type { Comment, DiffFile } from "$lib/types";

/**
 * Whether a thread has a row to hang on in the diff as it is drawn.
 *
 * A narrower base leaves out the files it has nothing to say about, and the
 * hunks of the files it keeps. A thread whose lines are not among them is
 * not lost — it is anchored to the review's own diff, which has not moved —
 * but there is nowhere to draw it here, so it is counted and said out loud
 * instead.
 *
 * Removed lines are the second way out. Their numbers belong to whatever is
 * on the left, and a narrower base puts something else there: a thread on
 * old line 17 would be drawn against whichever line now sits at 17. So with
 * `removedLines` off, the old side is not drawn at all.
 */
export function isDrawn(
  comment: Comment,
  files: DiffFile[],
  { removedLines = true }: { removedLines?: boolean } = {},
): boolean {
  if (comment.side === "old" && !removedLines) return false;

  const file = files.find((f) => f.path === comment.file);
  if (!file) return false;

  return file.hunks.some((hunk) =>
    hunk.lines.some(
      (line) =>
        (comment.side === "old" ? line.old_no : line.new_no) ===
        comment.end_line,
    ),
  );
}
