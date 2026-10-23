/**
 * When a review's story is written, read as Settings draws it: one choice of three, drawn as two boxes.
 *
 * "Write stories without asking" is ticked for both choices that write a
 * story unasked; "Write as soon as the review opens" hangs on it, ticked for
 * the one that writes it as the review opens. Each box ticked or unticked
 * leaves one of the three choices, so the two can never say what none of
 * them means: written as the review opens, but asked first.
 */

import type { StoryWriting } from '$lib/types';

/** The choice that writes every story without asking, at a press on Story: what the question's box keeps. */
export const WITHOUT_ASKING: StoryWriting = 'without_asking';

// Whether each choice writes a story without asking the reader first
const WRITES_WITHOUT_ASKING: Record<StoryWriting, boolean> = {
	ask_first: false,
	without_asking: true,
	as_the_review_opens: true
};

// Whether each choice writes each review's story as the review opens
const WRITES_AS_THE_REVIEW_OPENS: Record<StoryWriting, boolean> = {
	ask_first: false,
	without_asking: false,
	as_the_review_opens: true
};

/** Whether stories are written without the reader being asked first: at a press on Story, or as a review opens. */
export function writesWithoutAsking(writing: StoryWriting): boolean {
	return WRITES_WITHOUT_ASKING[writing];
}

/** Whether each review's story is written as the review opens. */
export function writesAsTheReviewOpens(writing: StoryWriting): boolean {
	return WRITES_AS_THE_REVIEW_OPENS[writing];
}

/** The choice the box "Write stories without asking" makes, ticked or unticked: unticked, every story is asked first. */
export function chosenByWithoutAsking(ticked: boolean): StoryWriting {
	return ticked ? WITHOUT_ASKING : 'ask_first';
}

/** The choice the box "Write as soon as the review opens" makes, ticked or unticked, stories being written unasked. */
export function chosenByAsTheReviewOpens(ticked: boolean): StoryWriting {
	return ticked ? 'as_the_review_opens' : WITHOUT_ASKING;
}
