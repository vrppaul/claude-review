/**
 * How a comment started on something the reader reads — lines of a file, a
 * block of the story's words — ends when its words go into the review: the
 * keyboard goes on to the thread they became, where the reader reads on.
 * Written once for every place a comment is started on.
 */

import type { CommentField } from '$lib/review/comment-field.svelte';
import type { Review } from '$lib/review/review.svelte';

/** Add a comment; the keyboard goes on to the thread it became. */
export function sayComment(review: Review, field: CommentField): void {
	review.sections.keyboardToThread(review.threads.say(field));
}

/** Add a comment and hand it straight to whoever is answering; the keyboard goes on to its thread. */
export async function askComment(review: Review, field: CommentField): Promise<void> {
	const said = review.threads.sayAndAsk(field);
	review.sections.keyboardToThread(said.thread);
	try {
		await said.asked;
	} catch {
		// The comment is written either way; the thread offers to ask again
	}
}
