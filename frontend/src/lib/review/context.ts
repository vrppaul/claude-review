/**
 * How the parts of the page reach the review they draw: handed down once,
 * by the screen that draws it, rather than imported from anywhere.
 */

import { getContext, setContext } from "svelte";

import type { Review } from "$lib/review/review.svelte";

const REVIEW = Symbol("review");

/** Hand the review down to everything drawn inside this component. */
export function provideReview(review: Review): void {
  setContext(REVIEW, review);
}

/** The review this component is drawn in. */
export function useReview(): Review {
  const review = getContext<Review | undefined>(REVIEW);
  if (review === undefined) {
    throw new Error("Drawn outside a review: nothing above provided one");
  }
  return review;
}

/** The context a component drawn on its own needs, to draw this review. */
export function reviewContext(review: Review): Map<symbol, Review> {
  return new Map([[REVIEW, review]]);
}
