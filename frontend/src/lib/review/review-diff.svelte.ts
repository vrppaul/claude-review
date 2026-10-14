/**
 * The diff on screen: which files, taken against which base, and what else
 * it could be taken against.
 *
 * The threads are anchored to the review's own diff. A narrower base — a
 * round, a branch — is another way of reading the same working tree, and
 * nothing about the review is written down by choosing one.
 */

import type { Numbering } from '$lib/anchors/numbering';
import { offeredVersions, retakeDiff, takeDiff } from '$lib/api/review-api';
import { RevealedContext } from '$lib/review/revealed-context.svelte';
import { TreeMoved } from '$lib/review/tree-moved.svelte';
import type { DiffFile, DiffResponse, ReviewVersion } from '$lib/types';
import { messageOf } from '$lib/utils/errors';

export class ReviewDiff {
	/** Files changed on disk since this diff was taken. */
	readonly treeMoved = new TreeMoved();

	readonly #whitespaceIgnored: () => boolean;
	// The diff on screen, as it arrived: its files, and which base it was
	// taken against as the server named it — its key, what the header says,
	// and whether it is narrower than the review's own. The base comes with
	// the diff rather than out of the version list, so the header can speak
	// before it knows everything the diff could be compared against; it is
	// null in a review compared against nothing.
	#onScreen: DiffResponse;
	// Lines revealed above the hunks of the diff on screen; every diff starts with none
	#revealed = $state.raw(new RevealedContext());
	// The files of the review's own diff, as it was last taken: a narrower
	// base shows fewer of them, and the review holds them all the same
	#ownFiles = $state.raw<DiffFile[]>([]);
	// Which base the reader last asked for, null for the review's own. Set the
	// moment they ask, so a diff taken again while theirs is on its way — a
	// round landing — is taken against what they picked, not against what is
	// still on screen.
	#requestedBase: string | null = null;
	// Why the review's own diff could not be put back when it was last asked for
	#wholeReviewFailed = $state<string | null>(null);
	#versions = $state.raw<ReviewVersion[]>([]);
	// Which request is the latest. Two can be in flight — a round landing
	// while the reader picks a base — and only the latest is drawn, whatever
	// order the answers come back in.
	#asking = 0;

	/**
	 * @param first the diff the review opened on, against its own base
	 * @param whitespaceIgnored whether the reader has whitespace-only changes left out
	 */
	constructor(first: DiffResponse, whitespaceIgnored: () => boolean) {
		this.#whitespaceIgnored = whitespaceIgnored;
		this.#onScreen = $state.raw(first);
		this.#noteWhatCameWithIt();
	}

	get files(): DiffFile[] {
		return this.#onScreen.files;
	}

	/** Whether the review's own diff holds a file, whatever base is on screen. */
	holds(path: string): boolean {
		return this.#ownFiles.some((file) => file.path === path);
	}

	/** Lines revealed above the hunks of the diff on screen. */
	get revealed(): RevealedContext {
		return this.#revealed;
	}

	/** Which base the diff on screen was taken against, by its key. */
	get base(): string | null {
		return this.#onScreen.base?.key ?? null;
	}

	/** What the header says the diff on screen is. */
	get phrase(): string {
		return this.#onScreen.base?.phrase ?? '';
	}

	/** Everything the diff could be taken against, once asked for. */
	get versions(): ReviewVersion[] {
		return this.#versions;
	}

	/**
	 * Whether a narrower base than the review's own is in force.
	 *
	 * False is the state everything else is written for: the threads are
	 * anchored to the review's own diff, and only that one draws them all.
	 */
	get narrowed(): boolean {
		return this.#onScreen.base?.narrowed ?? false;
	}

	/** Whose numbers the lines of the diff on screen carry: the review's own, unless a narrower base is in force. */
	get numbering(): Numbering {
		return this.narrowed ? 'a-narrower-bases' : 'the-reviews';
	}

	/**
	 * Which take of the review the page reads: the one the diff on screen was
	 * read at, whatever base it is read against, and the one the threads'
	 * lines are numbered by. While a retake lands — the threads followed, the
	 * diff not read yet — it is still the take before.
	 */
	get takeOnScreen(): number {
		return this.#onScreen.take;
	}

	/** Take the diff again against the base the reader asked for. */
	async take(): Promise<void> {
		const hold = await this.read();
		hold();
	}

	/**
	 * Read the diff again against the base the reader asked for, and return
	 * how to put it on screen: whoever reads it with something else holds
	 * both once both are read.
	 */
	async read(): Promise<() => void> {
		const mine = ++this.#asking;
		const data = await takeDiff({
			ignoreWhitespace: this.#whitespaceIgnored(),
			base: this.#requestedBase
		});
		return () => this.#showIfLatest(mine, data);
	}

	/**
	 * Read the same working tree against something else.
	 *
	 * The threads stay anchored to the review's own diff; one this base
	 * cannot draw is hidden and said out loud, never moved and never marked
	 * outdated.
	 *
	 * The diff arrives before the base changes. The other way round, the
	 * screen spends a moment saying it is showing one thing while it is still
	 * drawing another — and a base that cannot be taken leaves it saying so
	 * for good.
	 */
	async setBase(key: string | null): Promise<void> {
		this.#requestedBase = key;
		try {
			await this.take();
		} catch (error) {
			// A base that cannot be taken is not asked for again by the next retake
			if (this.#requestedBase === key) this.#requestedBase = this.base;
			throw error;
		}
	}

	/**
	 * Put the review's own diff back, with every thread it holds: the one the
	 * server shows when asked for no other. A failure is kept to be said,
	 * never thrown: whoever asked goes on with the diff as it is.
	 */
	async showWholeReview(): Promise<void> {
		if (this.#onScreen.base === null) return;
		this.#wholeReviewFailed = null;
		try {
			await this.setBase(null);
		} catch (error) {
			this.#wholeReviewFailed = messageOf(error);
		}
	}

	/**
	 * Why the review's own diff could not be put back when it was last asked
	 * for; null once it was, and once any other diff is on screen: the
	 * failure is news of the diff it left there.
	 */
	get wholeReviewFailed(): string | null {
		return this.#wholeReviewFailed;
	}

	/** Ask what the diff could be taken against. */
	async loadVersions(): Promise<void> {
		this.#versions = (await offeredVersions()).versions;
	}

	/**
	 * Take the diff again, at the reader's word.
	 *
	 * The same act the agent performs with `claude-review retake`, and it goes
	 * the same way: the server retakes it and every open review is told to
	 * fetch, so a browser keeps its own view of what is folded.
	 */
	async retake(): Promise<void> {
		await retakeDiff();
	}

	/** Put a diff read on screen, unless a later read was asked for since: only the latest is drawn. */
	#showIfLatest(asked: number, data: DiffResponse): void {
		if (asked === this.#asking) this.#show(data);
	}

	/** Put a diff that has arrived on screen, with everything that came with it. */
	#show(data: DiffResponse): void {
		this.#onScreen = data;
		this.#noteWhatCameWithIt();
	}

	/**
	 * Take in what the diff now on screen brings beside itself: nothing read
	 * in around its hunks yet, no failure to put the whole review back left
	 * to say, the review's own files where it is of the review's own base,
	 * and how far the tree has moved since it was taken.
	 */
	#noteWhatCameWithIt(): void {
		this.#revealed = new RevealedContext();
		this.#wholeReviewFailed = null;
		if (!this.narrowed) this.#ownFiles = this.files;
		// Said with the diff as well as pushed: a review reloaded while the tree
		// was moving heard the push and lost it, and one opened later never
		// heard it at all
		this.treeMoved.note(this.#onScreen.moved);
	}
}
