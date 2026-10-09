import { describe, it, expect, beforeEach, afterEach, vi, type MockInstance } from 'vitest';
import { flushSync } from 'svelte';
import { DraftRepository } from '$lib/drafts/draft-repository';
import type { Draft } from '$lib/drafts/draft-shapes';
import { storageKey } from '$lib/utils/preferences';
import type { Review } from '$lib/review/review.svelte';
import { newComment } from './new-comment';
import { openReview } from './review';

const DRAFT_KEY = storageKey('draft');
const TITLE = 'repo: uncommitted changes';
// Longer than the keeper waits after the last change
const AFTER_A_PAUSE = 1000;

/** What another tab on the same review keeps, holding one thread. */
function anotherTabsDraft(title = TITLE): Draft {
	const other = openReview({ facts: { title } });
	other.threads.add(newComment({ body: 'written in the other tab' }));
	const kept = other.draft;
	if (kept === null) throw new Error('A review not yet sent has a draft');
	return kept;
}

/** The storage event a tab hears when another tab on this port keeps something. */
function keptElsewhere(draft: Draft): void {
	window.dispatchEvent(new StorageEvent('storage', { key: DRAFT_KEY, newValue: JSON.stringify(draft) }));
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

	it('does not write back what it took in, which would wake the other tab', () => {
		const theirs = anotherTabsDraft();
		review = openReview();
		localStorage.setItem(DRAFT_KEY, JSON.stringify(theirs));
		const written = vi.spyOn(Storage.prototype, 'setItem');

		keptElsewhere(theirs);
		flushSync();
		vi.advanceTimersByTime(AFTER_A_PAUSE);

		expect(draftWrites(written)).toBe(0);
	});

	it("leaves another review's draft alone", () => {
		const theirs = anotherTabsDraft('other-repo: changes since v1');
		review = openReview();

		keptElsewhere(theirs);

		expect(review.threads.count).toBe(0);
	});
});
