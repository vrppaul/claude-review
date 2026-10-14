/**
 * The ways a review is read, as the header's switch offers them, and what
 * a segment of the switch says of its view beyond the view's name.
 *
 * The switch is all a reader of the files sees of the story: so its Story
 * segment says what the story view would, were it on screen — that the
 * agent is writing the story, or that one arrived and waits to be read.
 */

import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ReviewStory, StoryArrival } from '$lib/review/review-story.svelte';
import type { IconName } from './icons';

/** One way to read the review, as the switch offers it. */
export interface Offered {
	name: ReadingViewName;
	label: string;
	icon: IconName;
	testId: string;
}

/**
 * What a segment says of its view beyond its name: nothing; that the agent
 * is writing what the view will show; or that the view holds what the
 * agent brought and the reader has not read.
 */
export type Said = 'nothing' | 'writing' | 'unread';

/** The story first, as the canvas has it: an open book, then a stack of files. */
export const OFFERED: readonly Offered[] = [
	{ name: 'story', label: 'Story', icon: 'story', testId: 'read-as-story' },
	{ name: 'files', label: 'Files', icon: 'files', testId: 'read-as-files' }
];

// What the Story segment says of each way the arrival of a story stands with the reader: unread from its
// arrival until they have read it, whether or not they put its note away
const SAID_OF_ARRIVAL: Record<StoryArrival, Said> = {
	none: 'nothing',
	offered: 'unread',
	'put-away': 'unread'
};

/** What the Story segment says of a story the reader is not looking at: that it is being written, or that it arrived. */
export function saidOfStory(story: ReviewStory): Said {
	return story.wait?.kind === 'writing' ? 'writing' : SAID_OF_ARRIVAL[story.arrival];
}
