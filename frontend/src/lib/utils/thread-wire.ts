import type { Comment, Turn, TurnPayload } from "$lib/types";

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
    anchor: comment.anchor,
    body: comment.body,
    images: comment.images,
    history: comment.turns.map(turnOnTheWire),
    severity: comment.severity,
    resolved: comment.resolved,
    raised_by: comment.raised_by,
  };
}

/** A turn as the other side is told about it: what was said, not when. */
export function turnOnTheWire({
  author,
  body,
  round,
  images,
}: Turn): TurnPayload {
  return { author, body, round, images };
}
