/**
 * Who says what in a review, in the words the wire has for them.
 *
 * The wire calls the agent "the author" — the one who wrote the change under
 * review — so the page names it once, here, and says "agent" everywhere else.
 */

import type { PanelSpeaker, Thread, TurnAuthor } from '$lib/types';

/** The person reading the review. */
export const READER = 'reader' satisfies TurnAuthor;
/** The agent that wrote the change and answers for it. */
export const AGENT = 'author' satisfies TurnAuthor;
/** The review itself, noting in the panel what happened rather than what was said. */
export const THE_REVIEW = 'event' satisfies PanelSpeaker;

/** Whether the agent opened the thread, rather than the reader. */
export function raisedByAgent(thread: Thread): boolean {
	return thread.raised_by === AGENT;
}
