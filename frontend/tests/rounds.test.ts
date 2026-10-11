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
