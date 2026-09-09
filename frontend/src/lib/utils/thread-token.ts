import type { Comment } from "$lib/types";

/**
 * How a thread is written into a panel message.
 *
 * The token is the reference: one word in the text, deleted like any other
 * word, and read back at the moment of sending. Nothing is kept beside the
 * text, so a token typed by hand works exactly as one the picker inserted,
 * and editing the message cannot leave a reference behind that the words no
 * longer mention.
 */
export function threadToken(comment: Comment): string {
  return `@${comment.file}:${comment.start_line}-${comment.end_line}`;
}

/**
 * Whether a message mentions this thread.
 *
 * A plain search would let `@a.py:1-2` match inside `@a.py:1-20`, so what
 * follows the token has to be something other than the rest of a number.
 */
function mentions(text: string, token: string): boolean {
  let from = text.indexOf(token);
  while (from !== -1) {
    const after = text[from + token.length];
    if (after === undefined || !/[\d-]/.test(after)) return true;
    from = text.indexOf(token, from + 1);
  }
  return false;
}

/** The threads a message points at, as its text stands right now. */
export function threadsIn(text: string, comments: Comment[]): Comment[] {
  return comments.filter((comment) => mentions(text, threadToken(comment)));
}
