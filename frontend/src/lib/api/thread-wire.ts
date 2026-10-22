import type { HeldThread, Thread, ThreadAsHanded, ThreadDraft, Turn, TurnDraft } from '$lib/types';

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
		turns: held.turns.map(turnOffTheWire),
		raised_by: held.raised_by,
		resolved: held.resolved,
		round: Math.min(currentRound, ...held.turns.map((turn) => turn.round))
	};
}

/** A turn as the other side says it, as this page holds one: when it was said, and what it answers, never told. */
function turnOffTheWire({ turn_id, author, body, round, images }: TurnDraft): Turn {
	return { id: turn_id, author, body, round, images };
}

/**
 * A thread as the agent has it, where the review says what that is, by
 * thread; as the page holds it, where the review says nothing of it. The
 * agent may have been handed a copy older than this page's, and what it has
 * is what stands: its opening, how it is meant and each turn it was handed
 * say what the agent has; one this page no longer holds stands again where
 * it stood; what was said since stays as the page holds it.
 */
export function asTheAgentHasIt(thread: Thread, handed: Record<string, ThreadAsHanded>): Thread {
	const has = handed[thread.id];
	if (!has) return thread;
	return {
		...thread,
		severity: has.severity,
		raised_by: has.opening.author,
		body: has.opening.body,
		images: has.opening.images,
		turns: turnsTheAgentHas(thread.turns, has.turns)
	};
}

/**
 * The page's turns, each the agent has saying what it has; one the page no
 * longer holds stands again after the turn handed before it.
 */
function turnsTheAgentHas(turns: readonly Turn[], handed: readonly TurnDraft[]): Turn[] {
	const words = new Map(handed.map((turn) => [turn.turn_id, turnOffTheWire(turn)]));
	const onThePage = new Set(turns.map((turn) => turn.id));
	const kept = turns.map((turn) => ({ ...turn, ...words.get(turn.id) }));
	return handed.reduce(
		(placed, turnHanded, position) =>
			onThePage.has(turnHanded.turn_id)
				? placed
				: placedAfter(placed, handed[position - 1]?.turn_id, turnOffTheWire(turnHanded)),
		kept
	);
}

/** Turns with one more, after the turn of that id, or first where no turn comes before it. */
function placedAfter(turns: readonly Turn[], previousId: string | undefined, turn: Turn): Turn[] {
	const at = turns.findIndex((placed) => placed.id === previousId) + 1;
	return [...turns.slice(0, at), turn, ...turns.slice(at)];
}
