/**
 * Keeping the draft as the review changes, without the review saying so.
 *
 * Whatever changes the threads, the summary or the panel changes the
 * review's snapshot of its draft; this keeps it a moment after the last
 * change rather than on every keystroke, and at once when the page goes.
 * A review that is over has no draft, and its old one is forgotten, so the
 * next review is not greeted with this one's unsent work.
 *
 * The review is open in one tab at a time, so one tab keeps its draft.
 */

import type { DraftRepository } from '$lib/drafts/draft-repository';
import type { Draft } from '$lib/drafts/draft-shapes';
import { stopsTogether } from '$lib/utils/stops';

// How long the draft waits after a change before it is kept: long enough
// for a sentence to be typed in one go, short enough that a crash loses
// almost nothing
const KEPT_AFTER = 300;

/** What a draft is kept for: a review's snapshot of it. */
export interface Drafted {
	/** The draft as the review now stands, or null once it is over. */
	readonly draft: Draft | null;
}

export class DraftKeeper {
	readonly #repository: DraftRepository;
	readonly #review: Drafted;
	#waiting: ReturnType<typeof setTimeout> | null = null;

	constructor(repository: DraftRepository, review: Drafted) {
		this.#repository = repository;
		this.#review = review;
	}

	/** Keep the draft from now on; returns how to stop. */
	start(): () => void {
		window.addEventListener('pagehide', this.#leaving);
		return stopsTogether(
			$effect.root(() => {
				$effect(() => this.#changed(this.#review.draft));
			}),
			() => window.removeEventListener('pagehide', this.#leaving),
			() => this.#stopWaiting()
		);
	}

	/**
	 * Keep now what is waiting to be kept. Nothing waiting, nothing written:
	 * a page closing over a review sent from another tab does not bring its
	 * draft back.
	 */
	flush(): void {
		if (this.#waiting === null) return;
		this.#stopWaiting();
		this.#keep();
	}

	#changed(draft: Draft | null): void {
		this.#stopWaiting();
		if (draft === null) {
			this.#repository.clear();
			return;
		}
		this.#waiting = setTimeout(() => this.flush(), KEPT_AFTER);
	}

	#keep(): void {
		const draft = this.#review.draft;
		if (draft !== null) this.#repository.save(draft);
	}

	#stopWaiting(): void {
		if (this.#waiting !== null) clearTimeout(this.#waiting);
		this.#waiting = null;
	}

	// The page going: what is waiting to be kept is kept now
	readonly #leaving = (): void => this.flush();
}
