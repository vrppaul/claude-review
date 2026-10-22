import { beforeEach, describe, it, expect, vi } from 'vitest';
import { flushSync } from 'svelte';
import { emptyDraft } from '$lib/drafts/draft-shapes';
import { forgetDraft, keepDraft, readDraft } from '$lib/drafts/draft-storage';
import { REVIEW_TITLE } from './diff';
import { REVIEW_IDENTITY } from './fake-socket';
import { fakeServer } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { leavePage, openReview } from './review';
import { DRAFT_KEY } from './stored-draft';
import { chatPush, handOverNext } from './pushes';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** What a browser throws where its storage is refused: private windows and blocked site data. */
function siteDataBlocked(): DOMException {
	return new DOMException('The operation is insecure.', 'SecurityError');
}

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

	it('comes back knowing what the agent has of each thread', () => {
		const id = review.threads.add(newComment({ body: 'handed over' }));
		handOverNext(review, { type: 'handed', thread_id: id, said: [id] });

		reload();

		expect(review.threads.handing.has(id, id)).toBe(true);
	});

	it('hands out ids past those said before the reload, so an answer or a note has an id of its own', () => {
		review.conversation.receive(chatPush('answered before the reload'));
		review.conversation.note('noted before the reload');

		reload();
		review.conversation.receive(chatPush('answered after the reload'));
		review.conversation.note('noted after the reload');

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

		review = openReview({ facts: { title: 'other-repo: changes since v1', identity: 'another-review' } });
		const count = review.restoredCount;

		expect(count).toBe(0);
		expect(review.threads.all).toEqual([]);
	});

	it('is kept apart from the draft of another review on the same port, though both have one title', () => {
		const namesake = { facts: { identity: 'a-namesake-in-another-directory' } };
		review = openReview();
		review.threads.add(newComment({ file: 'a.py', body: 'mine' }));
		review = openReview(namesake);
		review.threads.add(newComment({ file: 'a.py', body: "the namesake's" }));

		review = openReview();
		const mine = review.threads.all.map((thread) => thread.body);
		review = openReview(namesake);
		const theirs = review.threads.all.map((thread) => thread.body);

		expect(mine).toEqual(['mine']);
		expect(theirs).toEqual(["the namesake's"]);
	});

	it('comes back with the files read and folded as they were left', () => {
		review.reading.setViewed('read.py', true);
		review.reading.toggleFolded('folded.py');

		reload();

		expect(review.reading.isViewed('read.py')).toBe(true);
		expect(review.reading.isFolded('read.py')).toBe(true);
		expect(review.reading.isFolded('folded.py')).toBe(true);
		expect(review.reading.isViewed('folded.py')).toBe(false);
	});

	it('does not come back after it has been sent, though it was kept before', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { markdown: '## x', comment_count: 1, round: 1, ended: true });
		review = openReview();
		review.threads.add(newComment({ file: 'a.py', body: 'tighten this' }));
		flushSync();
		window.dispatchEvent(new Event('pagehide'));
		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft?.threads).toHaveLength(1);

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
			throw siteDataBlocked();
		});

		review = openReview();
		expect(() => review.threads.add(newComment({ body: 'still fine' }))).not.toThrow();
		expect(review.threads.count).toBe(1);
	});

	it('says a fault of its own in keeping or forgetting the draft, rather than taking it for storage refused', () => {
		// The review this file opens goes first: what it would keep as it goes is not what is asked here
		leavePage();
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new TypeError('a fault of the page');
		});
		vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
			throw new TypeError('a fault of the page');
		});

		expect(() => keepDraft(REVIEW_IDENTITY, emptyDraft(1))).toThrow(TypeError);
		expect(() => forgetDraft(REVIEW_IDENTITY)).toThrow(TypeError);
	});

	it('opens with nothing picked up when site data is blocked', () => {
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
			throw siteDataBlocked();
		});

		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft).toBeNull();
	});

	it('ignores a draft that is not what it should be', () => {
		localStorage.setItem(DRAFT_KEY, 'not json at all');

		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft).toBeNull();
	});

	it('is forgotten when asked', () => {
		keepDraft(REVIEW_IDENTITY, { ...emptyDraft(1), reviewBody: 'Overall fine' });

		forgetDraft(REVIEW_IDENTITY);

		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft).toBeNull();
	});
});
