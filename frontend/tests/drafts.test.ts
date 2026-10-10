import { beforeEach, describe, it, expect, vi } from 'vitest';
import { DraftRepository } from '$lib/drafts/draft-repository';
import { DRAFT_SHAPE } from '$lib/drafts/draft-shapes';
import { fakeServer } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';

let review: Review;
// Where the page keeps drafts, read the way the page reads them
const drafts = new DraftRepository();

beforeEach(() => {
	review = openReview();
});

const TITLE = 'repo: uncommitted changes';
/** Where the page keeps the draft between reloads. */
const DRAFT_KEY = 'claude-review:draft';

/** The reload of a page: whatever it held is gone, and the draft is read again. */
function reload() {
	review = openReview();
}

describe('an unsent review', () => {
	it('comes back folded, unread and waited on as it was left', async () => {
		fakeServer().answer('POST /api/ask', null);
		const folded = review.threads.add(newComment({ startLine: 1, body: 'folded' }));
		const unread = review.threads.add(newComment({ startLine: 2, body: 'unread' }));
		const asked = review.threads.add(newComment({ startLine: 3, body: 'asked' }));
		review.threads.reading.setFolded(folded, true);
		review.threads.reading.markUnread(unread);
		await review.threads.ask(asked);

		reload();

		expect(review.threads.reading.isFolded(folded)).toBe(true);
		expect(review.threads.reading.isUnread(unread)).toBe(true);
		expect(review.threads.reading.awaiting(asked).map((question) => question.id)).toEqual([asked]);
	});

	it('hands out ids past those said before the reload, so an answer has an id of its own', () => {
		review.conversation.receive(null, 'before the reload', []);

		reload();
		review.conversation.receive(null, 'after the reload', []);

		const ids = review.conversation.turns.map((turn) => turn.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('survives a reload of the same review', () => {
		review = openReview();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));
		review.submission.setBody('Overall fine');

		review = openReview();
		const count = review.restoredCount;

		expect(count).toBe(1);
		expect(review.threads.all[0].body).toBe('tighten this');
		expect(review.submission.body).toBe('Overall fine');
	});

	it('is not handed to a different review', () => {
		review = openReview();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		review = openReview({ facts: { title: 'other-repo: changes since v1' } });
		const count = review.restoredCount;

		expect(count).toBe(0);
		expect(review.threads.all).toEqual([]);
	});

	it('does not come back after it has been sent', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { markdown: '## x', comment_count: 1, round: 1, ended: true });
		review = openReview();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));

		await review.submission.submit(true);

		review = openReview();
		expect(review.restoredCount).toBe(0);
	});

	it('never hands out a comment id a restored comment already has, even after a deletion', () => {
		review = openReview();
		const first = review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.remove(first);

		reload();
		review.threads.add(newComment({ startLine: 3, body: 'three' }));

		const ids = review.threads.all.map((comment) => comment.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('never hands out again the ids of a thread deleted just before the reload', () => {
		review = openReview();
		review.threads.add(newComment({ startLine: 1, body: 'kept' }));
		const deleted = review.threads.add(newComment({ startLine: 2, body: 'deleted' }));
		review.threads.addTurn(deleted, { author: 'reader', body: 'Asked', images: [] });
		const deletedTurn = review.threads.all[1].turns[0].id;
		review.threads.remove(deleted);

		reload();
		const added = review.threads.add(newComment({ startLine: 3, body: 'new' }));
		review.threads.addTurn(added, { author: 'reader', body: 'Asked anew', images: [] });

		// The agent may still know the deleted ones, and would answer the new under them
		expect(added).not.toBe(deleted);
		expect(review.threads.all[1].turns[0].id).not.toBe(deletedTurn);
	});

	it('never hands out a turn id a restored turn already has', () => {
		review = openReview();
		const id = review.threads.add(newComment({ body: 'Why?' }));
		review.threads.addTurn(id, { author: 'reader', body: 'Still asking', images: [] });
		review.threads.receiveReply(id, 'Because', null);

		reload();
		review.threads.addTurn(id, { author: 'reader', body: 'Thanks', images: [] });

		const ids = review.threads.all[0].turns.map((turn) => turn.id);
		expect(ids).toHaveLength(3);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('leaves the review working when site data is blocked', () => {
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});

		review = openReview();
		expect(() => review.threads.add(newComment({ body: 'still fine' }))).not.toThrow();
		expect(review.threads.count).toBe(1);
	});

	it('ignores a draft that is not what it should be', () => {
		localStorage.setItem(DRAFT_KEY, 'not json at all');

		expect(drafts.load(TITLE)).toBeNull();
	});

	it('is forgotten when asked', () => {
		drafts.save({
			version: DRAFT_SHAPE,
			title: 'repo',
			threads: [],
			read: { folded: [], unread: [], awaiting: {} },
			reviewBody: 'x',
			sent: {},
			panel: [],
			composer: { text: '', images: [] },
			issued: { comments: 0, turns: 0 },
			told: null
		});
		drafts.clear();

		expect(drafts.load('repo')).toBeNull();
	});
});
