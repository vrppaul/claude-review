import { describe, it, expect } from 'vitest';
import type { Thread, Turn } from '$lib/types';
import { lineAnchor } from '$lib/anchors/line';
import { exchangesOf, turnsToFold } from '$lib/utils/thread-exchanges';

function thread(turns: Turn[]): Thread {
	return {
		id: 'c1',
		anchor: lineAnchor('a.py', 'new', 1, 1, []),
		severity: 'question',
		body: 'Why here?',
		images: [],
		turns,
		raised_by: 'reader',
		resolved: false,
		round: 1,
		at: 0
	};
}

function reply(id: string, body: string, round = 1): Turn {
	return { id, author: 'reader', body, round, at: 0, images: [] };
}

function answer(id: string, body: string, answers?: string): Turn {
	return { id, author: 'author', body, round: 1, at: 0, images: [], ...(answers ? { answers } : {}) };
}

/** What each exchange asked, and what was answered to it. */
function read(exchanges: ReturnType<typeof exchangesOf>) {
	return exchanges.map((exchange) => [exchange.asked, exchange.answers.map((turn) => turn.body)]);
}

describe('a thread read as questions and answers', () => {
	it('is one question while nobody has said anything since the comment', () => {
		expect(read(exchangesOf(thread([])))).toEqual([['Why here?', []]]);
	});

	it('starts a question at each reply of the reader', () => {
		const exchanges = exchangesOf(thread([answer('t1', 'Because.'), reply('t2', 'And there?'), answer('t3', 'Same.')]));

		expect(read(exchanges)).toEqual([
			['Why here?', ['Because.']],
			['And there?', ['Same.']]
		]);
	});

	it('puts an answer under the question it names, even with a later one asked', () => {
		const exchanges = exchangesOf(thread([reply('t1', 'And there?'), answer('t2', 'To the first.', 'c1')]));

		expect(read(exchanges)).toEqual([
			['Why here?', ['To the first.']],
			['And there?', []]
		]);
	});

	it('puts an answer that names nothing under the last question', () => {
		const exchanges = exchangesOf(thread([reply('t1', 'And there?'), answer('t2', 'An old answer.')]));

		expect(read(exchanges)).toEqual([
			['Why here?', []],
			['And there?', ['An old answer.']]
		]);
	});

	it('says where a new round begins: at a question asked in a later round than the one before it', () => {
		const exchanges = exchangesOf(thread([reply('t1', 'And this?'), reply('t2', 'Still?', 2), reply('t3', 'Now?', 2)]));

		expect(exchanges.map((exchange) => exchange.startsRound)).toEqual([false, false, true, false]);
	});
});

/** What must stay in sight: these turns, and no other. */
function keeping(...turnIds: string[]): (turnId: string) => boolean {
	return (turnId) => turnIds.includes(turnId);
}

describe('which turns of a long thread fold', () => {
	it('folds what lies between the opening and the last three turns, two turns or more, up to one that must stay', () => {
		const six = ['c1', 't1', 't2', 't3', 't4', 't5'];
		const eight = ['c1', 't1', 't2', 't3', 't4', 't5', 't6', 't7'];

		// Six turns, nothing to keep: the two between the opening and the last three
		expect(turnsToFold(six, keeping())).toEqual(['t1', 't2']);
		// Five: one turn behind a row saves nothing
		expect(turnsToFold(six.slice(0, -1), keeping())).toEqual([]);
		// An answer not read yet among the early turns: the run before it folds, the rest stays
		expect(turnsToFold(eight, keeping('t3'))).toEqual(['t1', 't2']);
		// A question still with the agent, second: one turn before it, too few to fold
		expect(turnsToFold(eight, keeping('t2'))).toEqual([]);
		// A turn being rewritten, first after the opening: nothing before it
		expect(turnsToFold(eight, keeping('t1'))).toEqual([]);
	});
});
