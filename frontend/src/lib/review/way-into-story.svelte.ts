/**
 * The way into Story: every way a reader comes to read the review as its story.
 *
 * They ask for it — Story in the header, or Try Story wherever Story is
 * introduced — and where reading it means having one written, it is
 * written: asked first, unless they chose stories written without asking.
 * Or the page brings it on screen: for a thread only the story
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
	/** Whether the story view opens as it is: a story is held, or one was asked for, on its way or stopped. */
	viewOpens: () => boolean;
	/** Whether the reader is asked before a story is written. */
	askedFirst: () => boolean;
	/** Have this review's story written. */
	writeStory: () => Promise<void>;
	/** Have every later story written without asking, in every review: the settings as kept once it is, unread here. */
	writeStoriesWithoutAsking: () => Promise<unknown>;
}

export class WayIntoStory implements ViewsOnScreen {
	readonly #views: ReadingViews;
	readonly #introductions: StoryIntroductions;
	readonly #readings: StoryReadings;
	// Whether the reader is being asked before a story is written: asked from the switch or from wherever Story is
	// introduced, drawn by the switch
	#askingBeforeWriting = $state(false);

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

	/** Whether the reader is being asked before a story is written, having asked to read the story. */
	get askingBeforeWriting(): boolean {
		return this.#askingBeforeWriting;
	}

	/**
	 * The reader asks to read the review as its story: Story in the header,
	 * or Try Story where Story is introduced. Where reading it means having
	 * one written, they are asked first, unless they chose stories written
	 * without asking: then it is written at once.
	 */
	readAsStory(): void {
		this.#tried();
		if (this.#readings.viewOpens()) this.#views.choose(STORY);
		else if (this.#readings.askedFirst()) this.#askingBeforeWriting = true;
		else this.#writeAndShow();
	}

	/** The reader said yes to the question: the story is written; and every later one without asking, where they ticked so. */
	writeAndRead(withoutAskingFromNowOn: boolean): void {
		if (withoutAskingFromNowOn) void this.#readings.writeStoriesWithoutAsking();
		this.#writeAndShow();
	}

	/** Have the story written, and bring where it will be on screen. */
	#writeAndShow(): void {
		void this.#readings.writeStory();
		this.#views.choose(STORY);
	}

	/** The question before a story is written is closed, whatever the reader said. */
	stopAskingBeforeWriting(): void {
		this.#askingBeforeWriting = false;
	}

	/** The reader is trying Story: it is introduced to them, here and in every review. */
	#tried(): void {
		this.#introductions.noteStoryIntroduced();
	}
}
