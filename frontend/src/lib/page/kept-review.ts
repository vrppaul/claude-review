/**
 * A review opened and kept as a draft: the one way the page — and the tests
 * that stand in for it — open a review.
 */

import { DraftKeeper } from '$lib/drafts/draft-keeper.svelte';
import type { DraftRepository } from '$lib/drafts/draft-repository';
import { type ReaderParts, Review } from '$lib/review/review.svelte';
import type { DiffResponse, ReviewResponse } from '$lib/types';

/** A review on screen, and what keeps its draft. */
export interface KeptReview {
	review: Review;
	keeper: DraftKeeper;
	/** Stop keeping the draft. */
	stopKeeping: () => void;
}

/**
 * Open a review on what the server says it is, its first diff, and whatever
 * unsent draft of it this browser kept — and keep its draft from then on.
 */
export function openKeptReview(
	facts: ReviewResponse,
	firstDiff: DiffResponse,
	reader: ReaderParts,
	drafts: DraftRepository
): KeptReview {
	const review = new Review({ facts, firstDiff, draft: drafts.load(facts.title) }, reader);
	const keeper = new DraftKeeper(drafts, review);
	return { review, keeper, stopKeeping: keeper.start() };
}
