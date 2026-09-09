import type { Comment } from "$lib/types";

/**
 * A file's comments keyed by the row they hang under, as "side:line".
 *
 * Asking row by row turned one comment into a scan of the whole list per
 * line, which a long file pays for on every keystroke that changes it.
 */
export function indexByRow(
  comments: Comment[],
  file: string,
): Map<string, Comment[]> {
  const index = new Map<string, Comment[]>();
  for (const comment of comments) {
    if (comment.file !== file) continue;
    const key = `${comment.side}:${comment.end_line}`;
    const existing = index.get(key);
    if (existing) existing.push(comment);
    else index.set(key, [comment]);
  }
  return index;
}
