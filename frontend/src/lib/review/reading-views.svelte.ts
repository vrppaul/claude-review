/**
 * The ways a review is read, and which of them is on screen.
 *
 * How the reader likes to read is theirs and outlives a review: it is kept
 * with the page's layout, and a review opens the way it says. What is on
 * screen is the review's own. The reader choosing a view changes both;
 * being taken to something only the files draw changes what is on screen,
 * and leaves the choice as the reader made it.
 *
 * Only the files read against the review's own base draw every thread and
 * file the review holds: a story draws what it tells and what it leaves
 * out, and a narrower base the lines it shows. Whatever takes the reader to
 * something neither draws asks for everything here, in one place.
 */

import type { PageLayout, ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ViewsOnScreen } from '$lib/review/navigator';
import type { ReadingView } from '$lib/review/reading-view';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';

/** Each way a review is read, by its name. */
type Views = Record<ReadingViewName, ReadingView>;

/** How the reader chose to read last, as the page's layout keeps it. */
type KeptChoice = PageLayout['readingView'];

// The view every review can be read in, and the one that can draw every thread and file it holds
const FILES: ReadingViewName = 'files';

export class ReadingViews implements ViewsOnScreen {
	readonly #views: Views;
	readonly #kept: KeptChoice;
	readonly #diff: ReviewDiff;
	#nameOnScreen: ReadingViewName;

	/**
	 * @param views each way this review is read
	 * @param kept how the reader chose to read last, in whichever review
	 * @param storyCanBeTold whether this review can be read as a story at all: one that cannot opens
	 *   by its files, though the reader chose the story last
	 * @param diff the diff the files are read from, which a narrower base may be in force on
	 */
	constructor(views: Views, kept: KeptChoice, storyCanBeTold: boolean, diff: ReviewDiff) {
		this.#views = views;
		this.#kept = kept;
		this.#diff = diff;
		this.#nameOnScreen = $state(storyCanBeTold ? kept.name : FILES);
	}

	/** The view the review is read in now. */
	get onScreen(): ReadingView {
		return this.#views[this.#nameOnScreen];
	}

	/** Read the review the way the reader chooses, and the next review they open too. */
	choose(name: ReadingViewName): void {
		this.#nameOnScreen = name;
		this.#kept.set(name);
	}

	/** Bring the files on screen for something only they show: how the reader chose to read stays as they chose it. */
	showFiles(): void {
		this.#nameOnScreen = FILES;
	}

	/**
	 * Bring on screen what draws every thread and file the review holds — the
	 * files, read against the review's own base — and hand their view over,
	 * as it is if the whole review could not be put back: the diff keeps why,
	 * and the files' bar says it.
	 */
	async showEverything(): Promise<ReadingView> {
		this.showFiles();
		if (this.#diff.narrowed) await this.#diff.showWholeReview();
		return this.#views[FILES];
	}
}
