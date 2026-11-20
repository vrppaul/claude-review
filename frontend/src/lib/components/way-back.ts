/** The way back, as the column beside what is read offers it: decided here once, drawn by the column. */

import type { Review } from '$lib/review/review.svelte';
import type { WayBackTo } from '$lib/ui/column';

/** The way back to the last place the reader left, while there is one; none where they left no place to go back to. */
export function wayBackOf(review: Review): WayBackTo | undefined {
	const top = review.wayBack.top;
	if (top === null) return undefined;
	return { called: top.called, calledInFull: top.calledInFull, go: () => void review.navigator.goBack() };
}
