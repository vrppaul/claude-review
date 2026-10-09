/**
 * Keeping the draft as the review changes, without the review saying so.
 *
 * Whatever changes the threads, the summary or the panel changes the
 * review's snapshot of its draft; this keeps it a moment after the last
 * change rather than on every keystroke, and at once when the page goes.
 * A review that is over has no draft, and its old one is forgotten, so the
 * next review is not greeted with this one's unsent work.
 *
 * Two tabs on one review keep one draft. Keeping is a turn taken with the
 * kept draft: it is read, merged with what this tab changed since the two
 * last agreed, written back, and taken in here — so neither tab writes the
 * other's work away, and both end up holding the same. The tabs take these
 * turns one at a time, so whatever is kept was built on what was kept
 * before it, and what a tab last read or wrote is always where the kept
 * draft and this tab's both started from.
 */

import type { DraftRepository } from '$lib/drafts/draft-repository';
import { emptyDraftLike, mergeDrafts, sameDraft } from '$lib/drafts/draft-merge';
import type { Draft } from '$lib/drafts/draft-shapes';
import { stopsTogether } from '$lib/utils/stops';

// How long the draft waits after a change before it is kept: long enough
// for a sentence to be typed in one go, short enough that a crash loses
// almost nothing
const KEPT_AFTER = 300;

/** What a draft is kept for: a review's snapshot of it, and taking in the merged one. */
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
	// The draft as this tab last read it from storage or wrote it there: what
	// this tab's draft and whatever is kept now both started from
	#base: Draft | null;

	/** @param opened the draft the review opened from, if it opened from one */
	constructor(repository: DraftRepository, review: Drafted, opened: Draft | null) {
		this.#repository = repository;
		this.#review = review;
		this.#base = opened;
	}

	/** Keep the draft from now on, and take in another tab's; returns how to stop. */
	start(): () => void {
		window.addEventListener('pagehide', this.#leaving);
		return stopsTogether(
			$effect.root(() => {
				$effect(() => this.#changed(this.#review.draft));
			}),
			this.#repository.onChange(this.#review.title, () => this.#keepInTurn()),
			() => window.removeEventListener('pagehide', this.#leaving),
			() => this.#stopWaiting()
		);
	}

	/**
	 * Keep the draft as it stands now, without waiting — not even for a turn:
	 * a page going away cannot wait for one.
	 */
	flush(): void {
		this.#stopWaiting();
		this.#bringTogether();
	}

	#changed(draft: Draft | null): void {
		this.#stopWaiting();
		if (draft === null) {
			this.#base = null;
			this.#repository.clear();
			return;
		}
		// Just as it was last read or written: nothing to keep
		if (this.#base !== null && sameDraft(draft, this.#base)) return;
		this.#waiting = setTimeout(() => this.#keepInTurn(), KEPT_AFTER);
	}

	#keepInTurn(): void {
		this.#stopWaiting();
		void this.#repository.inTurn(() => this.#bringTogether());
	}

	/** Read the kept draft, merge this tab's into it, keep the merge, and take it in here. */
	#bringTogether(): void {
		const mine = this.#review.draft;
		if (mine === null) return;
		const kept = this.#repository.load(this.#review.title);
		const together = kept === null ? mine : mergeDrafts(this.#base ?? emptyDraftLike(mine), mine, kept);
		this.#repository.save(together);
		this.#base = together;
		if (!sameDraft(together, mine)) this.#review.adopt(together);
	}

	#stopWaiting(): void {
		if (this.#waiting !== null) clearTimeout(this.#waiting);
		this.#waiting = null;
	}

	// The page going: what is waiting to be kept is kept now
	readonly #leaving = (): void => this.flush();
}
