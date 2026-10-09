import { describe, it, expect, beforeEach, afterEach, vi, type MockInstance } from 'vitest';
import { flushSync } from 'svelte';
import { DraftRepository } from '$lib/drafts/draft-repository';
import type { Draft } from '$lib/drafts/draft-shapes';
import { storageKey } from '$lib/utils/preferences';
import type { Review } from '$lib/review/review.svelte';
import { newComment } from './new-comment';
import { leavePage, openReview } from './review';

const DRAFT_KEY = storageKey('draft');
const TITLE = 'repo: uncommitted changes';
// Longer than the keeper waits after the last change
const AFTER_A_PAUSE = 1000;
// How far apart two tabs take in the same push, in milliseconds
const TAKEN_APART = 5;
// A thread the agent raised, told to every tab on the review at once
const RAISED_ID = 'raised-1';

/** Write one thread, as the reader does. */
function writeThread(review: Review): void {
	review.threads.add(newComment({ body: 'written in the other tab' }));
}

/** Take in the thread the agent raised, as every tab on the review does. */
function takeInRaised(review: Review): void {
	review.threads.raise(RAISED_ID, newComment({ body: 'Look here' }).anchor, 'Look here', 'note');
}

/**
 * What another tab on the same review keeps, once it has done something —
 * by default, written one thread. Only the storage event brings it here:
 * what it wrote is cleared away, as if it had been written in a tab of its
 * own.
 */
function anotherTabsDraft({
	title = TITLE,
	does = writeThread
}: { title?: string; does?: (review: Review) => void } = {}): Draft {
	const other = openReview({ facts: { title } });
	does(other);
	const kept = other.draft;
	if (kept === null) throw new Error('A review not yet sent has a draft');
	leavePage();
	localStorage.clear();
	return kept;
}

/** The storage event a tab hears when another tab on this port has kept its draft. */
function heardElsewhere(draft: Draft): void {
	window.dispatchEvent(new StorageEvent('storage', { key: DRAFT_KEY, newValue: JSON.stringify(draft) }));
}

/** Another tab on this port keeps its draft, and this tab hears of it. */
function keptElsewhere(draft: Draft): void {
	localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
	heardElsewhere(draft);
}

/** How many times the draft was written, of everything written to storage. */
function draftWrites(written: MockInstance<Storage['setItem']>): number {
	return written.mock.calls.filter(([key]) => key === DRAFT_KEY).length;
}

describe('keeping the draft', () => {
	let review: Review;

	beforeEach(() => {
		vi.useFakeTimers();
		review = openReview();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('keeps it a moment after the last change, not on every keystroke', () => {
		const written = vi.spyOn(Storage.prototype, 'setItem');

		for (const typed of ['O', 'Ov', 'Ove', 'Over', 'Overall']) {
			review.submission.setBody(typed);
			flushSync();
		}
		expect(draftWrites(written)).toBe(0);

		vi.advanceTimersByTime(AFTER_A_PAUSE);

		expect(draftWrites(written)).toBe(1);
		expect(new DraftRepository().load(TITLE)?.reviewBody).toBe('Overall');
	});

	it('keeps it at once when the page goes', () => {
		review.submission.setBody('Overall fine');
		flushSync();

		window.dispatchEvent(new Event('pagehide'));

		expect(new DraftRepository().load(TITLE)?.reviewBody).toBe('Overall fine');
	});

	it('takes in what another tab on the same review keeps', () => {
		const theirs = anotherTabsDraft();
		review = openReview();

		keptElsewhere(theirs);

		expect(review.threads.all.map((thread) => thread.body)).toEqual(['written in the other tab']);
	});

	it('keeps what it has not kept yet when another tab keeps its draft', () => {
		const theirs = anotherTabsDraft();
		review = openReview();
		review.threads.add(newComment({ body: 'written here, not kept yet' }));
		review.submission.setBody('summary typed here');
		review.conversation.composer.setText('message typed here');
		flushSync();

		keptElsewhere(theirs);

		expect(review.threads.all.map((thread) => thread.body)).toEqual([
			'written in the other tab',
			'written here, not kept yet'
		]);
		expect(review.submission.body).toBe('summary typed here');
		expect(review.conversation.composer.text).toBe('message typed here');
	});

	it('gives a thread written here under an id the other tab also gave out an id of its own', () => {
		const theirs = anotherTabsDraft();
		review = openReview();
		review.threads.add(newComment({ body: 'written here, not kept yet' }));
		flushSync();

		keptElsewhere(theirs);

		const ids = review.threads.all.map((thread) => thread.id);
		expect(ids).toHaveLength(2);
		expect(new Set(ids).size).toBe(ids.length);
		expect(review.threads.add(newComment({ body: 'next' }))).not.toBeOneOf(ids);
	});

	it('does not write back what it took in, which would wake the other tab', () => {
		const theirs = anotherTabsDraft();
		review = openReview();
		localStorage.setItem(DRAFT_KEY, JSON.stringify(theirs));
		const written = vi.spyOn(Storage.prototype, 'setItem');

		heardElsewhere(theirs);
		flushSync();
		vi.advanceTimersByTime(AFTER_A_PAUSE);

		expect(draftWrites(written)).toBe(0);
	});

	it('holds once a thread the agent raised, though both tabs took it in', () => {
		const theirs = anotherTabsDraft({ does: takeInRaised });
		review = openReview();
		vi.advanceTimersByTime(TAKEN_APART);
		takeInRaised(review);
		flushSync();

		keptElsewhere(theirs);

		expect(review.threads.all.map((thread) => thread.id)).toEqual([RAISED_ID]);
	});

	it("leaves another review's draft alone", () => {
		const theirs = anotherTabsDraft({ title: 'other-repo: changes since v1' });
		review = openReview();

		keptElsewhere(theirs);

		expect(review.threads.count).toBe(0);
	});
});
