import type { HeldThread, Thread, ThreadDraft, Turn, TurnDraft } from '$lib/types';

/**
 * A thread as the other side is told about it.
 *
 * One shape for every errand: a round, a question, a message pointing at a
 * thread, and the review telling the server what it holds. Each is the same
 * fact — what this thread is and what has been said in it — and an agent
 * should not have to learn it twice.
 */
export function threadOnTheWire(comment: Thread): ThreadDraft {
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
function turnOnTheWire({ id, author, body, round, images }: Turn): TurnDraft {
	return { turn_id: id, author, body, round, images };
}

/**
 * A thread the review holds, as this page holds one: what a page opening
 * with no draft takes in. When it was written was never told, nor which
 * question an answer belongs to; the round it was written in is no later
 * than the first thing said in it, nor than now.
 */
export function threadOfHeld(held: HeldThread, currentRound: number): Thread {
	return {
		id: held.thread_id,
		anchor: held.anchor,
		severity: held.severity,
		body: held.body,
		images: held.images,
		turns: held.turns.map(({ turn_id, author, body, round, images }) => ({ id: turn_id, author, body, round, images })),
		raised_by: held.raised_by,
		resolved: held.resolved,
		round: Math.min(currentRound, ...held.turns.map((turn) => turn.round))
	};
}
