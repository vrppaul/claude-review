/** Pushes from the server, taken in by a review as its socket would hand them over. */
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { ServerPush, TellingPosition } from '$lib/types';
import { THIS_RUN } from './fake-socket';

/** A push that changes nothing a test reads. */
export const NO_WORK: ServerPush = { type: 'progress', work: null };

/** Where the n-th push of this run of the review stands in its telling. */
export function pushedAt(sequence: number): TellingPosition {
	return { instance: THIS_RUN, sequence };
}

/** Hand the review the next push the server tells, as its socket would. */
export function told(review: Review, push: ServerPush): void {
	const { heard } = review.telling;
	takePush(review, push, { ...heard, sequence: heard.sequence + 1 });
}
