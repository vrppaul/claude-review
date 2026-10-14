/**
 * The way into Story: every way a reader comes to read the review as its story.
 *
 * They ask for it — Story in the header, or Try Story wherever Story is
 * introduced — and are asked first where reading it means having one
 * written. Or the page brings it on screen: for a thread only the story
 * draws, or as the review opens the way they read last. However they come
 * there, a reader with the story on screen is trying Story, and one who
 * asked for it has tried it: it is introduced to them from then on, which
 * the guide keeps.
 *
 * So every way the story comes on screen passes through here, the
 * navigator's too, and nothing watches what is on screen to catch it after.
 */

import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ViewsOnScreen } from '$lib/review/navigator';
import type { ReadingView } from '$lib/review/reading-view';
import type { ReadingViews } from '$lib/review/reading-views.svelte';

// The view that draws the story told of the change
const STORY: ReadingViewName = 'story';

/** Whoever keeps that Story was introduced to the reader. */
export interface StoryIntroductions {
	noteStoryIntroduced: () => void;
}

/** What reading the review as its story depends on, beyond the views it is read in. */
export interface StoryReadings {
	/** Whether the story view opens now: the reader wants stories, or one is held or on its way. */
	viewOpens: () => boolean;
	/** Turn stories on, and ask for this review's where none is on its way. */
	turnStoriesOn: () => Promise<void>;
}

export class WayIntoStory implements ViewsOnScreen {
	readonly #views: ReadingViews;
	readonly #introductions: StoryIntroductions;
	readonly #readings: StoryReadings;
	// Whether the reader is being asked before stories are turned on: asked from the switch or from wherever Story
	// is introduced, drawn by the switch
	#askingToTurnStoriesOn = $state(false);

	constructor(views: ReadingViews, introductions: StoryIntroductions, readings: StoryReadings) {
		this.#views = views;
		this.#introductions = introductions;
		this.#readings = readings;
		// A review that opens as its story, the way the reader read last
		if (views.onScreen.name === STORY) this.#tried();
	}

	get onScreen(): ReadingView {
		return this.#views.onScreen;
	}

	showEverything(): Promise<ReadingView> {
		return this.#views.showEverything();
	}

	/** Bring the story on screen for a thread only it draws, and hand its view over. */
	showStory(): ReadingView {
		this.#tried();
		return this.#views.showStory();
	}

	/** Whether the reader is being asked before stories are turned on, having asked to read the story. */
	get askingToTurnStoriesOn(): boolean {
		return this.#askingToTurnStoriesOn;
	}

	/**
	 * The reader asks to read the review as its story: Story in the header,
	 * or Try Story where Story is introduced. Where reading it means having
	 * one written, they are asked first.
	 */
	readAsStory(): void {
		this.#tried();
		if (this.#readings.viewOpens()) this.#views.choose(STORY);
		else this.#askingToTurnStoriesOn = true;
	}

	/** The reader said yes: stories are on from now, this review's is asked for, and where it will be comes on screen. */
	turnStoriesOnAndRead(): void {
		void this.#readings.turnStoriesOn();
		this.#views.choose(STORY);
	}

	/** The question before stories are turned on is closed, whatever the reader said. */
	stopAskingToTurnStoriesOn(): void {
		this.#askingToTurnStoriesOn = false;
	}

	/** The reader is trying Story: it is introduced to them, here and in every review. */
	#tried(): void {
		this.#introductions.noteStoryIntroduced();
	}
}
