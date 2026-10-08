import { describe, it, expect, vi } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { lineAnchor } from '$lib/anchors/line';
import type { LineSide } from '$lib/types';
import { indexByRow } from '$lib/utils/comment-index';
import { fakeServer, SERVER_ERROR } from './fake-server';
import { newComment } from './new-comment';

/** What the server says to a review that went, whatever it held. */
const ENDED = { markdown: '## Comments', comment_count: 1, round: 1, ended: true };

/** The threads drawn under one row of a file. */
function threadsOn(file: string, side: LineSide, line: number) {
	return indexByRow(commentStore.comments, file).get(`${side}:${line}`) ?? [];
}

describe('the comments of a review', () => {
	it('start with nothing written', () => {
		expect(commentStore.count).toBe(0);
		expect(commentStore.comments).toEqual([]);
	});

	it('keep a comment where it was written, under an id of its own', () => {
		const id = commentStore.add(newComment({ file: 'file.ts', startLine: 10, body: 'fix this' }));

		expect(id).toBeTruthy();
		expect(commentStore.count).toBe(1);
		expect(commentStore.comments[0]).toMatchObject({
			id,
			anchor: { file: 'file.ts', start_line: 10, end_line: 10 },
			body: 'fix this'
		});
	});

	it('keep a comment on a range of lines', () => {
		commentStore.add(newComment({ startLine: 10, endLine: 15, body: 'refactor this block' }));

		expect(commentStore.comments[0].anchor).toMatchObject({ start_line: 10, end_line: 15 });
	});

	it('keep comments on the two sides of the same line number apart', () => {
		commentStore.add(newComment({ side: 'old', startLine: 42, body: 'about the removed line' }));
		commentStore.add(newComment({ side: 'new', startLine: 42, body: 'about the replacement' }));

		const removed = threadsOn('file.ts', 'old', 42);
		const added = threadsOn('file.ts', 'new', 42);

		expect(removed.map((comment) => comment.body)).toEqual(['about the removed line']);
		expect(added.map((comment) => comment.body)).toEqual(['about the replacement']);
	});

	it('remember which side of the diff a comment is on, so line numbers stay unambiguous', () => {
		commentStore.add(
			newComment({ side: 'old', startLine: 7, endLine: 9, body: 'why was this dropped' })
		);

		expect(commentStore.comments[0].anchor).toMatchObject({
			side: 'old',
			start_line: 7,
			end_line: 9
		});
	});

	it('take an edit to a comment', () => {
		const id = commentStore.add(newComment({ body: 'original' }));

		commentStore.update(id, 'updated', 'note', []);

		expect(commentStore.comments[0].body).toBe('updated');
	});

	it('forget a deleted comment', () => {
		const id = commentStore.add(newComment({ body: 'to delete' }));

		commentStore.remove(id);

		expect(commentStore.count).toBe(0);
	});

	it('are found by the file they are on', () => {
		commentStore.add(newComment({ file: 'a.ts', startLine: 1, body: 'comment A' }));
		commentStore.add(newComment({ file: 'b.ts', startLine: 1, body: 'comment B' }));
		commentStore.add(newComment({ file: 'a.ts', startLine: 5, body: 'comment A2' }));

		expect(commentStore.getForFile('a.ts').map((comment) => comment.body)).toEqual([
			'comment A',
			'comment A2'
		]);
		expect(commentStore.getForFile('b.ts')).toHaveLength(1);
		expect(commentStore.getForFile('c.ts')).toHaveLength(0);
	});

	it('draw a thread under the last line of its range only', () => {
		commentStore.add(newComment({ startLine: 10, endLine: 15, body: 'range comment' }));
		commentStore.add(newComment({ startLine: 20, body: 'single line' }));

		expect(threadsOn('file.ts', 'new', 10)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 12)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 15)).toHaveLength(1);
		expect(threadsOn('file.ts', 'new', 16)).toHaveLength(0);
		expect(threadsOn('file.ts', 'new', 20)).toHaveLength(1);
	});
});

describe('the summary of a review', () => {
	it('starts empty', () => {
		expect(commentStore.reviewBody).toBe('');
	});

	it('is kept as it is written', () => {
		commentStore.setReviewBody('Wrong approach');

		expect(commentStore.reviewBody).toBe('Wrong approach');
	});

	it('is something to send on its own', () => {
		expect(commentStore.hasContent).toBe(false);

		commentStore.setReviewBody('Some feedback');

		expect(commentStore.hasContent).toBe(true);
	});

	it('is not needed when there are comments to send', () => {
		commentStore.add(newComment({ body: 'fix' }));

		expect(commentStore.hasContent).toBe(true);
	});

	it('is nothing to send when it is only blank', () => {
		commentStore.setReviewBody('   \n  ');

		expect(commentStore.hasContent).toBe(false);
	});
});

describe('answered threads', () => {
	it('come newest answer first', () => {
		vi.useFakeTimers();
		const older = commentStore.add(newComment({ body: 'asked first' }));
		const newer = commentStore.add(newComment({ body: 'asked second' }));

		vi.setSystemTime(1_000);
		commentStore.receiveReply(older, 'answered first');
		vi.setSystemTime(2_000);
		commentStore.receiveReply(newer, 'answered last');
		vi.useRealTimers();

		expect(commentStore.answered.map((comment) => comment.body)).toEqual([
			'asked second',
			'asked first'
		]);
	});
});

describe('asking about a thread', () => {
	it('says how the thread is meant to be taken', async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', { status: 'asked' });

		const id = commentStore.add(newComment({ body: 'This must go', severity: 'blocker' }));
		commentStore.setResolved(id, true);
		await commentStore.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ severity: 'blocker', resolved: true, raised_by: 'reader' }
		]);
	});
});

describe('a thread the author raised', () => {
	it('is not counted as the reader\'s work', () => {
		commentStore.raise(
			'raised-1',
			lineAnchor('src/routes.py', 'new', 2, 2, ['y = 3']),
			'I did this differently',
			'note'
		);

		expect(commentStore.count).toBe(1);
		expect(commentStore.comments[0].raised_by).toBe('author');
		// Already sent: the reader did not write it, so it is not theirs to send
		expect(commentStore.unsentCount).toBe(0);
		expect(commentStore.hasUnsent).toBe(false);
	});

	it('goes with the next round once the reader has answered in it', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { ...ENDED, ended: false });
		commentStore.raise(
			'raised-1',
			lineAnchor('src/routes.py', 'new', 2, 2, []),
			'I did this differently',
			'note'
		);

		commentStore.addTurn('raised-1', { author: 'reader', body: 'Fine, but rename it', images: [] });
		await commentStore.submit(false);

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([
			{ comments: [{ raised_by: 'author', turns: [{ body: 'Fine, but rename it' }] }] }
		]);
	});

	it('is handed over as the author\'s own words', async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', { status: 'asked' });
		commentStore.raise(
			'raised-1',
			lineAnchor('src/routes.py', 'new', 2, 2, []),
			'I kept the old name',
			'note'
		);
		commentStore.addTurn('raised-1', { author: 'reader', body: 'Why?', images: [] });

		await commentStore.ask('raised-1');

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ body: 'Why?', history: [{ author: 'author', body: 'I kept the old name' }] }
		]);
	});
});

describe('stepping through comments', () => {
	it('keeps one position, so two controls cannot disagree', () => {
		commentStore.add(newComment({ startLine: 1, body: 'one' }));
		commentStore.add(newComment({ startLine: 2, body: 'two' }));

		expect(commentStore.step(1)?.body).toBe('one');
		expect(commentStore.step(1)?.body).toBe('two');
		expect(commentStore.step(-1)?.body).toBe('one');
	});

	it('wraps around rather than stopping at the end', () => {
		commentStore.add(newComment({ body: 'one' }));

		expect(commentStore.step(1)?.body).toBe('one');
		expect(commentStore.step(1)?.body).toBe('one');
	});

	it('has nothing to step to when there are no comments', () => {
		expect(commentStore.step(1)).toBeUndefined();
	});
});

describe('ending the review', () => {
	it('sends every comment as it was written', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		commentStore.add(newComment({ file: 'file.ts', startLine: 10, body: 'fix this' }));
		const result = await commentStore.submit();

		expect(server.requests).toEqual([
			{
				method: 'POST',
				path: '/api/submit',
				query: {},
				body: {
					comments: [
						{
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
		expect(commentStore.submitted).toBe(true);
	});

	it('sends the summary with the comments', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		commentStore.setReviewBody('General feedback');
		await commentStore.submit();

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([{ body: 'General feedback' }]);
	});

	it('leaves the summary out when none was written', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', ENDED);

		commentStore.add(newComment({ body: 'fix' }));
		await commentStore.submit();

		expect(server.bodiesSentTo('POST /api/submit')[0]).not.toHaveProperty('body');
	});

	it('stays open when the server refuses it', async () => {
		const server = fakeServer();
		server.refuse('POST /api/submit', SERVER_ERROR);

		commentStore.add(newComment({ body: 'test' }));

		await expect(commentStore.submit()).rejects.toThrow(`Submit failed: ${SERVER_ERROR}`);
		expect(commentStore.submitted).toBe(false);
	});
});
