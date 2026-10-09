import { beforeEach, describe, it, expect, vi } from 'vitest';
import { lineAnchor } from '$lib/anchors/line';
import type { LineSide } from '$lib/types';
import { indexByRow } from '$lib/utils/comment-index';
import { fakeServer, SERVER_ERROR } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** What the server says to a review that went, whatever it held. */
const ENDED = { markdown: '## Comments', comment_count: 1, round: 1, ended: true };

/** The threads drawn under one row of a file. */
function threadsOn(file: string, side: LineSide, line: number) {
	return indexByRow(review.threads.all, file).get(`${side}:${line}`) ?? [];
}

describe('the comments of a review', () => {
	it('start with nothing written', () => {
		expect(review.threads.count).toBe(0);
		expect(review.threads.all).toEqual([]);
	});

	it('keep a comment where it was written, under an id of its own', () => {
		const id = review.threads.add(newComment({ file: 'file.ts', startLine: 10, body: 'fix this' }));

		expect(id).toBeTruthy();
		expect(review.threads.count).toBe(1);
		expect(review.threads.all[0]).toMatchObject({
			id,
			anchor: { file: 'file.ts', start_line: 10, end_line: 10 },
			body: 'fix this'
		});
	});

	it('keep a comment on a range of lines', () => {
		review.threads.add(newComment({ startLine: 10, endLine: 15, body: 'refactor this block' }));

		expect(review.threads.all[0].anchor).toMatchObject({ start_line: 10, end_line: 15 });
	});

	it('keep comments on the two sides of the same line number apart', () => {
		review.threads.add(newComment({ side: 'old', startLine: 42, body: 'about the removed line' }));
		review.threads.add(newComment({ side: 'new', startLine: 42, body: 'about the replacement' }));

		const removed = threadsOn('file.ts', 'old', 42);
		const added = threadsOn('file.ts', 'new', 42);

		expect(removed.map((comment) => comment.body)).toEqual(['about the removed line']);
		expect(added.map((comment) => comment.body)).toEqual(['about the replacement']);
	});

	it('remember which side of the diff a comment is on, so line numbers stay unambiguous', () => {
		review.threads.add(newComment({ side: 'old', startLine: 7, endLine: 9, body: 'why was this dropped' }));

		expect(review.threads.all[0].anchor).toMatchObject({
			side: 'old',
			start_line: 7,
			end_line: 9
		});
	});

	it('take an edit to a comment', () => {
		const id = review.threads.add(newComment({ body: 'original' }));

		review.threads.update(id, 'updated', 'note', []);

		expect(review.threads.all[0].body).toBe('updated');
	});

	it('forget a deleted comment', () => {
		const id = review.threads.add(newComment({ body: 'to delete' }));

		review.threads.remove(id);

		expect(review.threads.count).toBe(0);
	});

	it('are found by the file they are on', () => {
		review.threads.add(newComment({ file: 'a.ts', startLine: 1, body: 'comment A' }));
		review.threads.add(newComment({ file: 'b.ts', startLine: 1, body: 'comment B' }));
		review.threads.add(newComment({ file: 'a.ts', startLine: 5, body: 'comment A2' }));

		expect(review.threads.onFile('a.ts').map((comment) => comment.body)).toEqual(['comment A', 'comment A2']);
		expect(review.threads.onFile('b.ts')).toHaveLength(1);
		expect(review.threads.onFile('c.ts')).toHaveLength(0);
	});

	it('draw a thread under the last line of its range only', () => {
		review.threads.add(newComment({ startLine: 10, endLine: 15, body: 'range comment' }));
		review.threads.add(newComment({ startLine: 20, body: 'single line' }));

		expect(threadsOn('file.ts', 'new', 10)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 12)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 15)).toHaveLength(1);
		expect(threadsOn('file.ts', 'new', 16)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 20)).toHaveLength(1);
	});
});

describe('the summary of a review', () => {
	it('starts empty', () => {
		expect(review.submission.body).toBe('');
	});

	it('is kept as it is written', () => {
		review.submission.setBody('Wrong approach');

		expect(review.submission.body).toBe('Wrong approach');
	});

	it('is something to send on its own', () => {
		expect(review.submission.hasContent).toBe(false);

		review.submission.setBody('Some feedback');

		expect(review.submission.hasContent).toBe(true);
	});

	it('is not needed when there are comments to send', () => {
		review.threads.add(newComment({ body: 'fix' }));

		expect(review.submission.hasContent).toBe(true);
	});

	it('is nothing to send when it is only blank', () => {
		review.submission.setBody('   \n  ');

		expect(review.submission.hasContent).toBe(false);
	});
});

describe('answered threads', () => {
	it('come newest answer first', () => {
		vi.useFakeTimers();
		const older = review.threads.add(newComment({ body: 'asked first' }));
		const newer = review.threads.add(newComment({ body: 'asked second' }));

		vi.setSystemTime(1_000);
		review.threads.receiveReply(older, 'answered first', null);
		vi.setSystemTime(2_000);
		review.threads.receiveReply(newer, 'answered last', null);
		vi.useRealTimers();

		expect(review.threads.answered.map((comment) => comment.body)).toEqual(['asked second', 'asked first']);
	});
});

describe('asking about a thread', () => {
	it('says how the thread is meant to be taken', async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', null);

		const id = review.threads.add(newComment({ body: 'This must go', severity: 'blocker' }));
		review.threads.setResolved(id, true);
		await review.threads.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { severity: 'blocker', resolved: true, raised_by: 'reader' } }
		]);
	});
});

describe('a thread the author raised', () => {
	it("is not counted as the reader's work", () => {
		review.threads.raise(
			'raised-1',
			lineAnchor('src/routes.py', 'new', 2, 2, ['y = 3']),
			'I did this differently',
			'note'
		);

		expect(review.threads.count).toBe(1);
		expect(review.threads.all[0].raised_by).toBe('author');
		// Already sent: the reader did not write it, so it is not theirs to send
		expect(review.threads.unsent.length).toBe(0);
		expect(review.submission.hasUnsent).toBe(false);
	});

	it('goes with the next round once the reader has answered in it', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { ...ENDED, ended: false });
		review.threads.raise('raised-1', lineAnchor('src/routes.py', 'new', 2, 2, []), 'I did this differently', 'note');

		review.threads.addTurn('raised-1', { author: 'reader', body: 'Fine, but rename it', images: [] });
		await review.submission.submit(false);

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([
			{ threads: [{ raised_by: 'author', turns: [{ body: 'Fine, but rename it' }] }] }
		]);
	});

	it("is handed over as the author's own words", async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', null);
		review.threads.raise('raised-1', lineAnchor('src/routes.py', 'new', 2, 2, []), 'I kept the old name', 'note');
		review.threads.addTurn('raised-1', { author: 'reader', body: 'Why?', images: [] });

		await review.threads.ask('raised-1');

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{
				thread: {
					raised_by: 'author',
					body: 'I kept the old name',
					turns: [{ author: 'reader', body: 'Why?' }]
				}
			}
		]);
	});
});

describe('stepping through comments', () => {
	it('keeps one position, so two controls cannot disagree', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));

		expect(review.threads.step(1)?.body).toBe('one');
		expect(review.threads.step(1)?.body).toBe('two');
		expect(review.threads.step(-1)?.body).toBe('one');
	});

	it('wraps around rather than stopping at the end', () => {
		review.threads.add(newComment({ body: 'one' }));

		expect(review.threads.step(1)?.body).toBe('one');
		expect(review.threads.step(1)?.body).toBe('one');
	});

	it('has nothing to step to when there are no comments', () => {
		expect(review.threads.step(1)).toBeUndefined();
	});
});

describe('ending the review', () => {
	it('sends every comment as it was written', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		review.threads.add(newComment({ file: 'file.ts', startLine: 10, body: 'fix this' }));
		const result = await review.submission.submit(true);

		expect(server.requests).toEqual([
			{
				method: 'POST',
				path: '/api/submit',
				query: {},
				body: {
					threads: [
						{
							thread_id: 'comment-1',
							anchor: {
								kind: 'line',
								file: 'file.ts',
								side: 'new',
								start_line: 10,
								end_line: 10,
								quote: [],
								outdated: false
							},
							severity: 'note',
							body: 'fix this',
							images: [],
							turns: [],
							raised_by: 'reader',
							resolved: false
						}
					],
					end: true
				}
			}
		]);
		expect(result.comment_count).toBe(1);
		expect(review.submission.finished).toBe(true);
	});

	it('sends the summary with the comments', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		review.submission.setBody('General feedback');
		await review.submission.submit(true);

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([{ body: 'General feedback' }]);
	});

	it('leaves the summary out when none was written', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		review.threads.add(newComment({ body: 'fix' }));
		await review.submission.submit(true);

		expect(server.bodiesSentTo('POST /api/submit')[0]).not.toHaveProperty('body');
	});

	it('stays open when the server refuses it', async () => {
		const server = fakeServer();
		server.fail('POST /api/submit', SERVER_ERROR);

		review.threads.add(newComment({ body: 'test' }));

		await expect(review.submission.submit(true)).rejects.toThrow(`Could not send the review: ${SERVER_ERROR}`);
		expect(review.submission.finished).toBe(false);
	});
});
