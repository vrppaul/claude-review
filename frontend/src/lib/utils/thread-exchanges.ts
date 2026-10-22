/**
 * A thread read as the questions in it and the answers to each.
 *
 * An answer says which question it belongs to, so two questions asked
 * before either is answered still read straight: each answer lands under
 * its own. An answer from an older version, which named nothing, falls to
 * the last question — where it used to go anyway.
 */

import type { Thread, Turn, TurnAuthor } from '$lib/types';
import { AGENT, READER } from '$lib/utils/speakers';

/** One question — the comment that opened the thread, or a reply of the reader's — and the answers to it. */
export interface Exchange {
	/** What an answer names it by: the comment's id, or the reply's. */
	id: string;
	/** Who asked it: whoever opened the thread, the agent where it raised it, and the reader every reply. */
	by: TurnAuthor;
	asked: string;
	round: number;
	/** Whether it was asked in another round than the question before it: where a new round begins in the thread. */
	startsRound: boolean;
	/** When it was asked; a reply kept from an older version may not say. */
	at: number | undefined;
	images: string[];
	answers: Turn[];
}

export function exchangesOf(thread: Thread): Exchange[] {
	const opening: Exchange = {
		id: thread.id,
		by: thread.raised_by,
		asked: thread.body,
		round: thread.round,
		startsRound: false,
		at: thread.at,
		images: thread.images,
		answers: []
	};
	const exchanges = [opening];
	// The question asked last, which an answer that names none falls to
	let latest = opening;
	for (const turn of thread.turns) {
		if (turn.author === READER) {
			latest = exchangeAfter(latest, turn);
			exchanges.push(latest);
		} else {
			const answered = exchanges.find((exchange) => exchange.id === turn.answers) ?? latest;
			answered.answers.push(turn);
		}
	}
	return exchanges;
}

/**
 * Which question asking in a thread puts: the reader's reply when theirs is
 * the last word, and otherwise the thread itself, by its opening comment.
 * Decided here alone: the server finds what the id names, and asks nothing
 * else of it.
 */
export function questionIdOf(thread: Thread): string {
	const last = thread.turns.at(-1);
	return last?.author === READER ? last.id : thread.id;
}

/** When the agent last answered in a thread; 0 for a thread it never answered. */
export function lastAnsweredAt(thread: Thread): number {
	return thread.turns.findLast((turn) => turn.author === AGENT)?.at ?? 0;
}

/** The question a reply of the reader's asks, after the question before it. */
function exchangeAfter(previous: Exchange, reply: Turn): Exchange {
	return {
		id: reply.id,
		by: reply.author,
		asked: reply.body,
		round: reply.round,
		startsRound: reply.round !== previous.round,
		at: reply.at,
		images: reply.images,
		answers: []
	};
}
