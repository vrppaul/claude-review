/**
 * A thread read as the questions in it and the answers to each.
 *
 * An answer says which question it belongs to, so two questions asked
 * before either is answered still read straight: each answer lands under
 * its own. An answer from an older version, which named nothing, falls to
 * the last question — where it used to go anyway.
 */

import type { Thread, Turn } from '$lib/types';
import { READER } from '$lib/utils/speakers';

/** One question — the comment that opened the thread, or a reply of the reader's — and the answers to it. */
export interface Exchange {
	/** What an answer names it by: the comment's id, or the reply's. */
	id: string;
	asked: string;
	round: number;
	/** When it was asked; a reply kept from an older version may not say. */
	at: number | undefined;
	images: string[];
	answers: Turn[];
}

export function exchangesOf(thread: Thread): Exchange[] {
	const exchanges: Exchange[] = [
		{ id: thread.id, asked: thread.body, round: thread.round, at: thread.at, images: thread.images, answers: [] }
	];
	for (const turn of thread.turns) {
		if (turn.author === READER) {
			exchanges.push({
				id: turn.id,
				asked: turn.body,
				round: turn.round,
				at: turn.at,
				images: turn.images,
				answers: []
			});
		} else {
			const answered = exchanges.find((exchange) => exchange.id === turn.answers) ?? exchanges[exchanges.length - 1];
			answered.answers.push(turn);
		}
	}
	return exchanges;
}
