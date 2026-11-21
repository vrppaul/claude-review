/**
 * How the parts of the page reach the review they draw, and the lookup of
 * names of the reading area they are drawn in: handed down once, by the
 * screen or the view that draws them, rather than imported from anywhere.
 */

import { getContext, setContext } from 'svelte';

import { NameLookup } from '$lib/review/name-lookup.svelte';
import type { Review } from '$lib/review/review.svelte';

const REVIEW = Symbol('review');
const NAME_LOOKUP = Symbol('name lookup');

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
 * Make the lookup of names of a view's reading area, where the review offers one, and hand it down to every line
 * drawn inside it: it lives as long as the view, and the marks it draws go with it.
 */
export function provideNameLookup(review: Review): NameLookup | null {
	const lookup = nameLookupIn(review);
	setContext(NAME_LOOKUP, lookup);
	return lookup;
}

/** A new lookup of names pressed in a reading area of a review, where the review offers one. */
export function nameLookupIn(review: Review): NameLookup | null {
	return review.namePointing === null ? null : new NameLookup(review.namePointing, review.sections);
}

/** The lookup of the reading area this line is drawn in, as the view it is drawn in said: none where none is offered. */
export function useNameLookup(): NameLookup | null {
	const lookup = getContext<NameLookup | null | undefined>(NAME_LOOKUP);
	if (lookup === undefined) throw new Error('Drawn outside a reading area: no view above said how names are looked up');
	return lookup;
}

/** The context a line drawn on its own needs: the lookup of the area it is drawn in, if any. */
export function nameLookupContext(lookup: NameLookup | null): Map<symbol, NameLookup | null> {
	return new Map([[NAME_LOOKUP, lookup]]);
}
