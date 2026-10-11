import { describe, it, expect } from 'vitest';
import type { Thread, Turn } from '$lib/types';
import { lineAnchor } from '$lib/anchors/line';
import { exchangesOf } from '$lib/utils/thread-exchanges';

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

function reply(id: string, body: string): Turn {
	return { id, author: 'reader', body, round: 1, at: 0, images: [] };
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
});
