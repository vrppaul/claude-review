import type { Comment, DiffFile } from "$lib/types";

// Characters per token, roughly, for English prose and code alike. Close
// enough for the only question the number answers: is handing this over
// cheap, or is it most of what an agent can hold at once.
const CHARS_PER_TOKEN = 4;

/**
 * What handing this review over would cost, in tokens.
 *
 * This is the one number of the two in the panel that can be worked out
 * here: the review is the diff on screen and the threads written against
 * it, and both are in hand. The agent's own context cannot be measured from
 * this side at all, which is why it arrives as a report rather than a
 * measurement.
 */
export function reviewWeight(files: DiffFile[], comments: Comment[]): number {
  let characters = 0;

  for (const file of files) {
    characters += file.path.length;
    for (const hunk of file.hunks) {
      for (const line of hunk.lines) characters += line.content.length + 1;
    }
  }

  for (const comment of comments) {
    characters += comment.body.length;
    for (const turn of comment.turns) characters += turn.body.length;
    for (const line of comment.quote) characters += line.length;
  }

  return Math.round(characters / CHARS_PER_TOKEN);
}

/** The same number as the panel says it: "~18k", "~900". */
export function formatWeight(tokens: number): string {
  if (tokens < 1000) return `~${tokens}`;
  return `~${Math.round(tokens / 100) / 10}k`;
}
