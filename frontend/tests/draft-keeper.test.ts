import { describe, it, expect, beforeEach, afterEach, vi, type MockInstance } from 'vitest';
import { flushSync } from 'svelte';
import { readDraft } from '$lib/drafts/draft-storage';
import type { Review } from '$lib/review/review.svelte';
import { REVIEW_IDENTITY, REVIEW_TITLE } from './diff';
import { newComment } from './new-comment';
import { openReview } from './review';
import { DRAFT_KEY } from './stored-draft';
// Longer than the keeper waits after the last change
const AFTER_A_PAUSE = 1000;

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
		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE)?.reviewBody).toBe('Overall');
	});

	it('keeps it at once when the page goes', () => {
		review.submission.setBody('Overall fine');
		flushSync();

		window.dispatchEvent(new Event('pagehide'));

		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE)?.reviewBody).toBe('Overall fine');
	});

	it('brings no draft back as the page goes with nothing waiting to be kept', () => {
		review.threads.add(newComment({ body: 'sent from another tab' }));
		flushSync();
		vi.advanceTimersByTime(AFTER_A_PAUSE);
		// The review was sent in another tab, which forgot the draft
		localStorage.removeItem(DRAFT_KEY);

		window.dispatchEvent(new Event('pagehide'));

		expect(localStorage.getItem(DRAFT_KEY)).toBeNull();
	});
});
