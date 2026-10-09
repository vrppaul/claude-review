/**
 * Keeping the draft as the review changes, without the review saying so.
 *
 * Whatever changes the threads, the summary or the panel changes the
 * review's snapshot of its draft; this keeps it a moment after the last
 * change rather than on every keystroke, and at once when the page goes.
 * A review that is over has no draft, and its old one is forgotten, so the
 * next review is not greeted with this one's unsent work.
 *
 * Two tabs on one review keep one draft: what another tab keeps, this one
 * takes in, so neither writes the other's threads away.
 */

import type { DraftRepository } from '$lib/drafts/draft-repository';
import type { Draft } from '$lib/drafts/draft-shapes';

// How long the draft waits after a change before it is kept: long enough
// for a sentence to be typed in one go, short enough that a crash loses
// almost nothing
const KEPT_AFTER = 300;

/** What a draft is kept for: a review's snapshot of it, and taking in another tab's. */
export interface Drafted {
	readonly title: string;
	/** The draft as the review now stands, or null once it is over. */
	readonly draft: Draft | null;
	adopt(draft: Draft): void;
}

export class DraftKeeper {
	readonly #repository: DraftRepository;
	readonly #review: Drafted;
	#waiting: ReturnType<typeof setTimeout> | null = null;

	constructor(repository: DraftRepository, review: Drafted) {
		this.#repository = repository;
		this.#review = review;
	}

	/** Keep the draft from now on, and take in another tab's; returns how to stop. */
	start(): () => void {
		const stopFollowing = $effect.root(() => {
			$effect(() => this.#changed(this.#review.draft));
		});
		const stopHearing = this.#repository.onChange(this.#review.title, (kept) => this.#review.adopt(kept));
		const leaving = () => this.flush();
		window.addEventListener('pagehide', leaving);
		return () => {
			stopFollowing();
			stopHearing();
			window.removeEventListener('pagehide', leaving);
			this.#stopWaiting();
		};
	}

	/** Keep the draft as it stands now, without waiting. */
	flush(): void {
		this.#stopWaiting();
		this.#keep(this.#review.draft);
	}

	#changed(draft: Draft | null): void {
		this.#stopWaiting();
		if (draft === null) {
			this.#repository.clear();
			return;
		}
		this.#waiting = setTimeout(() => this.flush(), KEPT_AFTER);
	}

	#keep(draft: Draft | null): void {
		if (draft === null) this.#repository.clear();
		else this.#repository.save(draft);
	}

	#stopWaiting(): void {
		if (this.#waiting !== null) clearTimeout(this.#waiting);
		this.#waiting = null;
	}
}
