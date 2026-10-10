/** A review opened the way the page opens one, for a test to read and draw. */
import { flushSync } from 'svelte';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import { reviewContext } from '$lib/review/context';
import type { Review } from '$lib/review/review.svelte';
import type { DiffFile, DiffResponse, ReviewResponse } from '$lib/types';
import { DraftRepository } from '$lib/drafts/draft-repository';
import { openKeptReview, type KeptReview } from '$lib/page/kept-review';
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

// The page open in this tab: the review it holds, keeping its draft as the page does
let openPage: KeptReview | null = null;

/**
 * Let the page open in this tab go, as a reload or a closed tab does: what
 * it was about to keep is kept first.
 */
export function leavePage(): void {
	// What the page changed last is noticed before it goes, as in a browser
	flushSync();
	openPage?.keeper.flush();
	openPage?.stopKeeping();
	openPage = null;
}

/**
 * Open a review as the page does: from what the server says it is, its
 * first diff, and whatever unsent draft of the same review this browser
 * kept — and keep its draft from then on. Opening another is a reload: the
 * page before it goes first.
 */
export function openReview({ files = [], facts, diff, settings = new Settings() }: Opened = {}): Review {
	leavePage();
	openPage = openKeptReview(
		reviewResponse(facts),
		diffResponse({ files, ...diff }),
		{ settings, layout: new PageLayout(), sound: new ReplySound(settings) },
		new DraftRepository()
	);
	return openPage.review;
}

/** The options a component drawn on its own needs to be drawn inside this review. */
export function inReview(review: Review): { context: Map<symbol, Review> };
export function inReview<Props>(review: Review, props: Props): { props: Props; context: Map<symbol, Review> };
export function inReview<Props>(review: Review, props?: Props) {
	const context = reviewContext(review);
	return props === undefined ? { context } : { props, context };
}
