/** A review opened the way the page opens one, for a test to read and draw. */
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import { reviewContext } from '$lib/review/context';
import { Review } from '$lib/review/review.svelte';
import type { DiffFile, DiffResponse, ReviewResponse } from '$lib/types';
import { loadDraft } from '$lib/utils/drafts';
import { diffResponse, reviewResponse } from './diff';

/** What a test says about the review it opens; the rest is a diff in its first round. */
export interface Opened {
	files?: DiffFile[];
	/** What the server says the review is. */
	facts?: Partial<ReviewResponse>;
	/** The first diff, beyond its files. */
	diff?: Partial<DiffResponse>;
	/** The reader's settings, where a test reads them. */
	settings?: Settings;
}

/**
 * Open a review as the page does: from what the server says it is, its
 * first diff, and whatever unsent draft of the same review this browser
 * kept. Opening it again is a reload.
 */
export function openReview({ files = [], facts, diff, settings = new Settings() }: Opened = {}): Review {
	const said = reviewResponse(facts);
	return new Review(
		{ facts: said, firstDiff: diffResponse({ files, ...diff }), draft: loadDraft(said.title) },
		{ settings, layout: new PageLayout(), sound: new ReplySound(settings) }
	);
}

/** The options a component drawn on its own needs to be drawn inside this review. */
export function inReview(review: Review): { context: Map<symbol, Review> };
export function inReview<Props>(
	review: Review,
	props: Props
): { props: Props; context: Map<symbol, Review> };
export function inReview<Props>(review: Review, props?: Props) {
	const context = reviewContext(review);
	return props === undefined ? { context } : { props, context };
}
