/**
 * How the parts of the page reach the review they draw, and the names of
 * the code of the reading area they are drawn in: handed down once, by the
 * screen or the view that draws them, rather than imported from anywhere.
 */

import { getContext, setContext } from 'svelte';

import { NamesInTheCode } from '$lib/review/names-in-the-code.svelte';
import type { Review } from '$lib/review/review.svelte';

const REVIEW = Symbol('review');
const NAMES_IN_THE_CODE = Symbol('names in the code');

/** Hand the review down to everything drawn inside this component. */
export function provideReview(review: Review): void {
	setContext(REVIEW, review);
}

/** The review this component is drawn in. */
export function useReview(): Review {
	const review = getContext<Review | undefined>(REVIEW);
	if (review === undefined) {
		throw new Error('Drawn outside a review: nothing above provided one');
	}
	return review;
}

/** The context a component drawn on its own needs, to draw this review. */
export function reviewContext(review: Review): Map<symbol, Review> {
	return new Map([[REVIEW, review]]);
}

/**
 * Make the names of the code of a view's reading area, where the review offers the gesture, and hand them down to
 * every line drawn inside it: they live as long as the view, and the marks they draw go with it.
 */
export function provideNamesInTheCode(review: Review): NamesInTheCode | null {
	const names = namesInTheCodeOf(review);
	setContext(NAMES_IN_THE_CODE, names);
	return names;
}

/** New names of the code of a reading area of a review, where the review offers the gesture. */
export function namesInTheCodeOf(review: Review): NamesInTheCode | null {
	return review.namePointing === null ? null : new NamesInTheCode(review.namePointing, review.sections);
}

/** The names of the code of the reading area this line is drawn in, as its view said: none where none are offered. */
export function useNamesInTheCode(): NamesInTheCode | null {
	const names = getContext<NamesInTheCode | null | undefined>(NAMES_IN_THE_CODE);
	if (names === undefined) throw new Error('Drawn outside a reading area: no view above said how names are looked up');
	return names;
}

/** The context a line drawn on its own needs: the names of the code of the area it is drawn in, if any. */
export function namesInTheCodeContext(names: NamesInTheCode | null): Map<symbol, NamesInTheCode | null> {
	return new Map([[NAMES_IN_THE_CODE, names]]);
}
