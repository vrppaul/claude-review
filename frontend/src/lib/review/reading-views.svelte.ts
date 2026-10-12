/**
 * The ways a review is read, and which of them is on screen.
 *
 * How the reader likes to read is theirs and outlives a review: it is kept
 * with the page's layout, and a review opens the way it says. What is on
 * screen is the review's own. The reader choosing a view changes both;
 * being taken to something only the files draw changes what is on screen,
 * and leaves the choice as the reader made it.
 */

import type { PageLayout, ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ViewsOnScreen } from '$lib/review/navigator';
import type { ReadingView } from '$lib/review/reading-view';

/** Each way a review is read, by its name. */
type Views = Record<ReadingViewName, ReadingView>;

/** How the reader chose to read last, as the page's layout keeps it. */
type KeptChoice = PageLayout['readingView'];

// The view every review can be read in, and the one that draws every thread and file it holds
const FILES: ReadingViewName = 'files';

export class ReadingViews implements ViewsOnScreen {
	readonly #views: Views;
	readonly #kept: KeptChoice;
	#nameOnScreen: ReadingViewName;

	/**
	 * @param views each way this review is read
	 * @param kept how the reader chose to read last, in whichever review
	 * @param storyCanBeTold whether this review can be read as a story at all: one that cannot opens
	 *   by its files, though the reader chose the story last
	 */
	constructor(views: Views, kept: KeptChoice, storyCanBeTold: boolean) {
		this.#views = views;
		this.#kept = kept;
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

	/** Bring on screen the view that draws every thread and file the review holds, and hand it over. */
	showEverything(): Promise<ReadingView> {
		this.showFiles();
		return Promise.resolve(this.#views[FILES]);
	}
}
