import type { Thread, ThreadInput, Turn, TurnInput } from '$lib/types';

/**
 * A thread as the other side is told about it.
 *
 * One shape for every errand: a round, a question, a message pointing at a
 * thread, and the review telling the server what it holds. Each is the same
 * fact — what this thread is and what has been said in it — and an agent
 * should not have to learn it twice.
 */
export function threadOnTheWire(comment: Thread): ThreadInput {
	return {
		thread_id: comment.id,
		anchor: comment.anchor,
		severity: comment.severity,
		body: comment.body,
		images: comment.images,
		// The clock belongs to reading the thread, not to what it says
		turns: comment.turns.map(turnOnTheWire),
		raised_by: comment.raised_by,
		resolved: comment.resolved
	};
}

/** A turn as the other side is told about it: what was said and by whom, not when. */
function turnOnTheWire({ id, author, body, round, images }: Turn): TurnInput {
	return { turn_id: id, author, body, round, images };
}
