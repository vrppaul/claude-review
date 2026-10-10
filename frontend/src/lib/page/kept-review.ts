/**
 * A review opened and kept as a draft: the one way the page — and the tests
 * that stand in for it — open a review.
 */

import { DraftKeeper } from '$lib/drafts/draft-keeper.svelte';
import { readDraft } from '$lib/drafts/draft-storage';
import { type ReaderParts, Review } from '$lib/review/review.svelte';
import type { DiffResponse, ReviewResponse } from '$lib/types';

/** A review on screen, and how to stop keeping its draft. */
export interface KeptReview {
	review: Review;
	/** Stop keeping the draft, keeping first what was waiting to be kept. */
	stopKeeping: () => void;
}

/**
 * Open a review on what the server says it is, its first diff, and whatever
 * unsent draft of it this browser kept — and keep its draft from then on.
 */
export function openKeptReview(facts: ReviewResponse, firstDiff: DiffResponse, reader: ReaderParts): KeptReview {
	const review = new Review({ facts, firstDiff, draft: readDraft(facts.title) }, reader);
	return { review, stopKeeping: new DraftKeeper(review).start() };
}
