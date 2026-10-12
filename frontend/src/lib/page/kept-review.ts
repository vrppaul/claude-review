/**
 * A review opened and kept as a draft: the one way the page — and the tests
 * that stand in for it — open a review.
 */

import { DraftKeeper } from '$lib/drafts/draft-keeper.svelte';
import { type KeptDraft, readDraft, setDraftAside } from '$lib/drafts/draft-storage';
import { type Opening, type ReaderParts, Review } from '$lib/review/review.svelte';

/** What a review opens on, whatever draft it opens from. */
type OpeningWithoutDraft = Omit<Opening, 'draft' | 'draftSetAside'>;

/** A review on screen, and how to stop keeping its draft. */
export interface KeptReview {
	review: Review;
	/** Stop keeping the draft, keeping first what was waiting to be kept. */
	stopKeeping: () => void;
}

/**
 * Open a review on what the server says it is, its first diff, what was said
 * in its panel, and whatever unsent draft of it this browser kept — or, with
 * none kept, the threads the review holds — and keep its draft from then on.
 */
export function openKeptReview(opening: OpeningWithoutDraft, reader: ReaderParts): KeptReview {
	const { identity, title } = opening.facts;
	const review = openOnKeptDraft(opening, readDraft(identity, title), reader);
	return { review, stopKeeping: new DraftKeeper(review).start() };
}

/**
 * The review opened on the draft this browser kept of it. A draft that
 * reads but that the review cannot be opened on is set aside as one that
 * cannot be read is, and the review opens without it: a broken draft never
 * keeps the review shut, reload after reload.
 */
function openOnKeptDraft(opening: OpeningWithoutDraft, kept: KeptDraft, reader: ReaderParts): Review {
	try {
		return new Review({ ...opening, draft: kept.draft, draftSetAside: kept.setAside }, reader);
	} catch (error) {
		if (kept.draft === null) throw error;
		const setAside = setDraftAside(opening.facts.identity, error);
		return new Review({ ...opening, draft: null, draftSetAside: setAside }, reader);
	}
}
