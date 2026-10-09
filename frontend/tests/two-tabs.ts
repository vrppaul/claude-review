/**
 * Two tabs on one review, side by side in one test: each with a review and
 * a keeper of its own, sharing the browser's storage, and hearing of the
 * other's keeping only when the test says.
 */
import { DraftRepository } from '$lib/drafts/draft-repository';
import { openKeptReview, type KeptReview } from '$lib/page/kept-review';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { ReviewResponse } from '$lib/types';
import { diffResponse, reviewResponse } from './diff';

/** One tab's way to the kept draft: the browser's storage, and word of the other tab keeping. */
class TabDrafts extends DraftRepository {
	#heardOf: (() => void) | null = null;

	override onChange(_title: string, listener: () => void): () => void {
		this.#heardOf = listener;
		return () => (this.#heardOf = null);
	}

	/** The other tab kept its draft, and this tab hears of it now. */
	hearOtherTab(): void {
		this.#heardOf?.();
	}
}

/** A tab open on the review. */
export class Tab {
	readonly #drafts = new TabDrafts();
	readonly #opened: KeptReview;

	/** @param facts what the server tells this tab the review is */
	constructor(facts: Partial<ReviewResponse> = {}) {
		const settings = new Settings();
		this.#opened = openKeptReview(
			reviewResponse(facts),
			diffResponse(),
			{ settings, layout: new PageLayout(), sound: new ReplySound(settings) },
			this.#drafts
		);
	}

	get review(): Review {
		return this.#opened.review;
	}

	/** Keep this tab's draft now, rather than a moment after its last change. */
	keep(): void {
		this.#opened.keeper.flush();
	}

	/** Hear that the other tab kept its draft. */
	hearOtherTab(): void {
		this.#drafts.hearOtherTab();
	}

	/** Close the tab without keeping anything more. */
	close(): void {
		this.#opened.stopKeeping();
	}
}
