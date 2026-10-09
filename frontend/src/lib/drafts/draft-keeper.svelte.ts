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
 * takes in, so neither writes the other's threads away — merged with what
 * this one has not kept yet, so neither wipes the other's either.
 */

import type { DraftRepository } from '$lib/drafts/draft-repository';
import { emptyDraftLike, mergeDrafts, sameDraft } from '$lib/drafts/draft-merge';
import type { Draft } from '$lib/drafts/draft-shapes';
import { stopsTogether } from '$lib/utils/stops';

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
	// The draft as this tab last kept it or took it in: what a draft from
	// another tab is merged against
	#base: Draft | null = null;

	constructor(repository: DraftRepository, review: Drafted) {
		this.#repository = repository;
		this.#review = review;
	}

	/** Keep the draft from now on, and take in another tab's; returns how to stop. */
	start(): () => void {
		window.addEventListener('pagehide', this.#leaving);
		return stopsTogether(
			$effect.root(() => {
				$effect(() => this.#changed(this.#review.draft));
			}),
			this.#repository.onChange(this.#review.title, (kept) => this.#takeIn(kept)),
			() => window.removeEventListener('pagehide', this.#leaving),
			() => this.#stopWaiting()
		);
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
		this.#base = draft;
		if (draft === null) this.#repository.clear();
		else this.#repository.save(draft);
	}

	/**
	 * Take in the draft another tab kept. Taken as it is when this tab has
	 * nothing it has not kept; merged with this tab's when it has, and the
	 * merge kept at once, so the other tab takes in this one's too.
	 */
	#takeIn(theirs: Draft): void {
		const mine = this.#review.draft;
		if (mine === null) return;
		const untouched = this.#waiting === null && this.#base !== null && sameDraft(mine, this.#base);
		const taken = untouched ? theirs : mergeDrafts(this.#base ?? emptyDraftLike(theirs), mine, theirs);
		this.#review.adopt(taken);
		this.#base = taken;
		if (!untouched) this.flush();
	}

	#stopWaiting(): void {
		if (this.#waiting !== null) clearTimeout(this.#waiting);
		this.#waiting = null;
	}

	// The page going: what is waiting to be kept is kept now
	readonly #leaving = (): void => this.flush();
}
