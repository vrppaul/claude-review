import type { Comment } from "$lib/types";

/**
 * A thread as the other side is told about it.
 *
 * One shape for both errands: a message pointing at a thread, and the
 * review telling the server what it holds. Both are the same fact — what
 * this thread is and what has been said in it — and an agent should not
 * have to learn it twice.
 */
export function threadOnTheWire(comment: Comment) {
  return {
    thread_id: comment.id,
    file: comment.file,
    side: comment.side,
    start_line: comment.start_line,
    end_line: comment.end_line,
    quote: comment.quote,
    body: comment.body,
    history: comment.turns.map(({ author, body, round }) => ({
      author,
      body,
      round,
    })),
    severity: comment.severity,
    resolved: comment.resolved,
    outdated: comment.outdated,
    raised_by: comment.raised_by,
  };
}
