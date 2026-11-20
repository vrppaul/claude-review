/**
 * The way into Story: the reader asking to read the review as its story.
 *
 * They ask for it — Story in the header, or Try Story wherever Story is
 * introduced — and where reading it means having one written, it is
 * written: asked first, unless they chose stories written without asking.
 * One who asked for it has tried it, whether or not it comes on screen yet,
 * as one the page brings it on screen for is trying it (`ReadingViews`): it
 * is introduced to them from then on, which the guide keeps.
 */

import type { ReadingChoice } from '$lib/reader/page-layout.svelte';
import type { ReadingViews, StoryIntroductions } from '$lib/review/reading-views.svelte';

// The view that draws the story told of the change, which the reader chooses by its name
const STORY: ReadingChoice = 'story';

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

export class WayIntoStory {
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
		this.#introductions.noteStoryIntroduced();
		if (this.#readings.viewOpens()) this.#views.choose(STORY);
		else if (this.#readings.askedFirst()) this.#askingBeforeWriting = true;
		else this.#writeAndShow();
	}

	/** The reader said yes to the question: the story is written; and every later one without asking, where they ticked so. */
	writeAndRead(withoutAskingFromNowOn: boolean): void {
		if (withoutAskingFromNowOn) void this.#readings.writeStoriesWithoutAsking();
		this.#writeAndShow();
	}

	/** The question before a story is written is closed, whatever the reader said. */
	stopAskingBeforeWriting(): void {
		this.#askingBeforeWriting = false;
	}

	/** Have the story written, and bring where it will be on screen. */
	#writeAndShow(): void {
		void this.#readings.writeStory();
		this.#views.choose(STORY);
	}
}
