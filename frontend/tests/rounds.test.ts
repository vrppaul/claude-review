import { beforeEach, describe, it, expect } from 'vitest';
import { lineAnchor } from '$lib/anchors/line';
import type { SubmitResponse } from '$lib/types';
import { fakeServer, type FakeServer } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** What the server says to a round it took, numbered as it numbers them. */
function roundTaken(round: number): SubmitResponse {
	return { markdown: '## x', comment_count: 1, round, ended: false };
}

/** A server that takes every round and numbers it `round`. */
function takingRounds(round = 1): FakeServer {
	const server = fakeServer();
	server.answer('POST /api/submit', roundTaken(round));
	return server;
}

/** The page reloaded against a server that restarted, and knows only round one. */
function reloadAfterRestart() {
	review = openReview();
}

describe('sending a round rather than ending the review', () => {
	it('keeps the threads on screen', async () => {
		takingRounds();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		await review.submission.submit(false);

		expect(review.threads.count).toBe(1);
		expect(review.link.ending).toBeNull();
	});

	it('carries what is new since the last round, not the review again', async () => {
		const server = takingRounds();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));
		await review.submission.submit(false);

		review.threads.add(newComment({ file: 'b.py', startLine: 2, body: 'and this' }));
		await review.submission.submit(false);

		expect(server.bodiesSentTo('POST /api/submit')[1]).toMatchObject({
			threads: [{ anchor: { file: 'b.py' } }]
		});
	});

	it('sends a thread again once something has been said in it', async () => {
		const server = takingRounds();
		const id = review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));
		await review.submission.submit(false);

		review.threads.receiveReply(id, 'Tightened', null);
		review.threads.addTurn(id, { author: 'reader', body: 'Still reads oddly', images: [] });
		await review.submission.submit(false);

		expect(server.bodiesSentTo('POST /api/submit')[1]).toMatchObject({
			threads: [
				{
					anchor: { file: 'a.py' },
					turns: [{ body: 'Tightened' }, { body: 'Still reads oddly' }]
				}
			]
		});
	});

	it('does not resend a thread just because it was answered', async () => {
		const server = takingRounds();
		const id = review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));
		await review.submission.submit(false);

		review.threads.receiveReply(id, 'Tightened', null);
		review.threads.add(newComment({ file: 'b.py', startLine: 2, body: 'and this' }));
		await review.submission.submit(false);

		expect(server.bodiesSentTo('POST /api/submit')[1]).toMatchObject({
			threads: [{ anchor: { file: 'b.py' } }]
		});
	});

	it('counts up so the next round says which one it is', async () => {
		takingRounds(2);
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		await review.submission.submit(false);

		expect(review.rounds.current).toBe(3);
	});
});

describe('the round a restarted server has forgotten', () => {
	it('is read back from the round the threads were written in', () => {
		review = openReview();
		review.rounds.reach(3);
		review.threads.add(newComment({ body: 'written in the third round' }));

		reloadAfterRestart();

		expect(review.rounds.current).toBe(3);
	});

	it('is the one after the last round a thread went out in', async () => {
		takingRounds(3);
		review = openReview();
		review.threads.add(newComment({ body: 'sent in the third round' }));
		await review.submission.submit(false);

		reloadAfterRestart();

		expect(review.rounds.current).toBe(4);
	});

	it('does not take back a later round the server already knows', () => {
		review = openReview();
		review.threads.add(newComment({ body: 'written in the first round' }));

		review = openReview({ facts: { round: 5 } });

		expect(review.rounds.current).toBe(5);
	});
});

describe('a thread meeting a diff that has been taken again', () => {
	it('asks the server where every thread now hangs', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', {
			anchors: [lineAnchor('a.py', 'new', 2, 2, ['def run():'])]
		});
		review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		await review.threads.follow();

		expect(server.requests).toMatchObject([
			{
				method: 'POST',
				path: '/api/anchors/follow',
				body: { anchors: [lineAnchor('a.py', 'new', 2, 2, ['def run():'])] }
			}
		]);
	});

	it('moves a thread to where its lines went, and counts it', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', {
			anchors: [lineAnchor('a.py', 'new', 3, 3, ['def run():'])]
		});
		review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		const moved = await review.threads.follow();

		expect(review.threads.all[0].anchor.start_line).toBe(3);
		expect(moved).toEqual({ followed: 1, outdated: 0 });
	});

	it('counts a thread whose lines are gone as outdated, not as followed', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', {
			anchors: [{ ...lineAnchor('a.py', 'new', 2, 2, ['def walk():']), outdated: true }]
		});
		review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def walk():'] }));

		const moved = await review.threads.follow();

		expect(review.threads.all[0].anchor.outdated).toBe(true);
		expect(moved).toEqual({ followed: 0, outdated: 1 });
	});

	it('refuses an answer that does not say where every thread went, and leaves them where they were', async () => {
		fakeServer().answer('POST /api/anchors/follow', { anchors: [] });
		review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		await expect(review.threads.follow()).rejects.toThrow();

		expect(review.threads.all.map((comment) => comment.anchor.start_line)).toEqual([2]);
	});

	it('counts only the threads still there when the answer lands', async () => {
		const followed = fakeServer().hold('POST /api/anchors/follow');
		const removed = review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));
		review.threads.add(newComment({ file: 'a.py', startLine: 5, quote: ['def walk():'] }));

		const following = review.threads.follow();
		review.threads.remove(removed);
		followed.answer(0, {
			anchors: [lineAnchor('a.py', 'new', 3, 3, ['def run():']), lineAnchor('a.py', 'new', 6, 6, ['def walk():'])]
		});

		expect(await following).toEqual({ followed: 1, outdated: 0 });
		expect(review.threads.all.map((comment) => comment.anchor.start_line)).toEqual([6]);
	});

	it('leaves a thread written while the answer was on its way where it is', async () => {
		const followed = fakeServer().hold('POST /api/anchors/follow');
		review.threads.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		const following = review.threads.follow();
		review.threads.add(newComment({ file: 'a.py', startLine: 9, quote: ['late'] }));
		followed.answer(0, { anchors: [lineAnchor('a.py', 'new', 3, 3, ['def run():'])] });
		await following;

		expect(review.threads.all.map((comment) => comment.anchor.start_line)).toEqual([3, 9]);
	});
});

describe('sending while the review cannot be reached', () => {
	it('sends nothing, a round or the end, until the review is back', async () => {
		const server = takingRounds();
		server.answer('POST /api/end', null);
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		review.link.lost();
		const couldSend = review.submission.canSend;
		const couldEnd = review.submission.canEnd;
		await review.submission.send();
		await review.submission.end();

		expect([couldSend, couldEnd]).toEqual([false, false]);
		expect(server.requests).toEqual([]);
		review.link.reached();
		expect([review.submission.canSend, review.submission.canEnd]).toEqual([true, true]);
	});
});

describe('ending a review worked through in rounds', () => {
	const ENDED: SubmitResponse = { markdown: '## Final', comment_count: 1, round: 2, ended: true };

	/** A review an agent works through, with its first round sent. */
	async function afterARound(): Promise<FakeServer> {
		review = openReview({ facts: { answerer_attached: true } });
		const server = takingRounds();
		review.threads.add(newComment({ file: 'a.py', body: 'sent in round one' }));
		await review.submission.submit(false);
		server.answer('POST /api/submit', ENDED);
		server.answer('POST /api/end', null);
		return server;
	}

	it('sends what was not sent yet as the final review rather than dropping it', async () => {
		const server = await afterARound();
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'written since' }));
		review.submission.setBody('Ship it after this');

		await review.submission.end();

		expect(server.requestsTo('POST /api/end')).toEqual([]);
		expect(server.bodiesSentTo('POST /api/submit').at(-1)).toMatchObject({
			threads: [{ body: 'written since' }],
			body: 'Ship it after this',
			end: true
		});
		expect(review.link.ending).toBe('finished');
	});

	it('only ends it when everything has gone already', async () => {
		const server = await afterARound();

		await review.submission.end();

		expect(server.requestsTo('POST /api/end')).toHaveLength(1);
		expect(server.requestsTo('POST /api/submit')).toHaveLength(1);
		expect(review.link.ending).toBe('finished');
	});
});

describe('writing while a round is on its way', () => {
	it('sends again with the next round a thread that changed after this one took it', async () => {
		const rounds = fakeServer().hold('POST /api/submit');
		const id = review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		const sending = review.submission.submit(false);
		review.threads.addTurn(id, { author: 'reader', body: 'and this too', images: [] });
		rounds.answer(0, roundTaken(1));
		await sending;

		expect(review.threads.unsent.map((thread) => thread.id)).toEqual([id]);
	});

	it('marks sent a thread that did not change while the round was on its way', async () => {
		const rounds = fakeServer().hold('POST /api/submit');
		const id = review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		const sending = review.submission.submit(false);
		rounds.answer(0, roundTaken(1));
		await sending;

		expect(review.threads.sentInRound(id)).toBe(1);
	});

	it('keeps what was added to the summary while the round was on its way, and only that', async () => {
		const rounds = fakeServer().hold('POST /api/submit');
		review.submission.setBody('Mostly fine.');

		const sending = review.submission.submit(false);
		review.submission.setBody('Mostly fine. One more thing:');
		rounds.answer(0, roundTaken(1));
		await sending;

		expect(review.submission.body).toBe('One more thing:');
	});

	it('keeps a summary rewritten while the round was on its way whole', async () => {
		const rounds = fakeServer().hold('POST /api/submit');
		review.submission.setBody('Mostly fine.');

		const sending = review.submission.submit(false);
		review.submission.setBody('Actually, not fine.');
		rounds.answer(0, roundTaken(1));
		await sending;

		expect(review.submission.body).toBe('Actually, not fine.');
	});
});
