/**
 * A thread read as the questions in it and the answers to each.
 *
 * An answer says which question it belongs to, so two questions asked
 * before either is answered still read straight: each answer lands under
 * its own. An answer from an older version, which named nothing, falls to
 * the last question — where it used to go anyway.
 *
 * Read in that order, a long thread folds what lies between its opening and
 * its last turns: which turns fold is how the page shows what it holds, so
 * it is decided here, on the page.
 */

import type { Thread, Turn, TurnAuthor } from '$lib/types';
import { AGENT, READER } from '$lib/utils/speakers';

// How many of a thread's last turns stay in sight however long it grows
const LAST_IN_SIGHT = 3;
// The fewest turns worth folding behind a row: one turn behind a row saves nothing
const FEWEST_FOLDED = 2;

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

/** A turn as a thread draws it, in its order: a question, or an answer under the question it answers. */
export type DrawnTurn = { id: string; exchange: Exchange; endsExchange: boolean } & (
	{ kind: 'question' } | { kind: 'answer'; answer: Turn }
);

/** A thread's turns in the order it draws them: each question, then the answers to it; the last of each says so. */
export function drawnTurnsOf(exchanges: readonly Exchange[]): DrawnTurn[] {
	return exchanges.flatMap((exchange): DrawnTurn[] => [
		{ kind: 'question', id: exchange.id, exchange, endsExchange: exchange.answers.length === 0 },
		...exchange.answers.map((answer): DrawnTurn => ({
			kind: 'answer',
			id: answer.id,
			exchange,
			answer,
			endsExchange: answer === exchange.answers.at(-1)
		}))
	]);
}

/**
 * Which turns of a long thread fold behind one row, given every turn in the
 * order it draws them and which must stay in sight: those between the
 * comment that opened it and its last turns, up to the first that must stay.
 */
export function turnsToFold(drawn: readonly string[], staysInSight: (turnId: string) => boolean): string[] {
	const beforeTheLast = drawn.slice(1, -LAST_IN_SIGHT);
	const firstStaying = beforeTheLast.findIndex(staysInSight);
	const folding = firstStaying === -1 ? beforeTheLast : beforeTheLast.slice(0, firstStaying);
	return folding.length >= FEWEST_FOLDED ? folding : [];
}

/** The turns of a thread folded behind its rows of earlier replies, and those of them the reader opened, by id. */
export interface TurnsFolded {
	turns: readonly string[];
	opened: readonly string[];
}

/** Turns a thread draws one after another: never folded, or folded behind one row. */
export interface TurnsRun {
	turns: DrawnTurn[];
	folded: boolean;
	/** Whether its turns stand in sight: the reader opened its row, or it has none. */
	open: boolean;
}

/**
 * A thread's drawn turns as runs, in sight or folded. A turn that arrived
 * among the folded ones since they were folded is in none of them: it splits
 * their run in two, each behind a row of its own, and stands between in sight.
 */
export function runsOf(drawn: readonly DrawnTurn[], folded: TurnsFolded): TurnsRun[] {
	const runs: TurnsRun[] = [];
	for (const turn of drawn) {
		const isFolded = folded.turns.includes(turn.id);
		const open = !isFolded || folded.opened.includes(turn.id);
		const last = runs.at(-1);
		if (last?.folded === isFolded && last.open === open) last.turns.push(turn);
		else runs.push({ turns: [turn], folded: isFolded, open });
	}
	return runs;
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
