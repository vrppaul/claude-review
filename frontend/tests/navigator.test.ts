import { beforeEach, describe, it, expect } from 'vitest';
import type { Review } from '$lib/review/review.svelte';
import { newComment } from './new-comment';
import { openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/**
 * Draw every thread of the review where the page would, and keep the body
 * of each one brought into view, in the order they were.
 */
function drawThreads(): string[] {
	const brought: string[] = [];
	for (const thread of review.threads.all) {
		const drawn = document.createElement('div');
		drawn.scrollIntoView = () => brought.push(thread.body);
		review.sections.registerThread(thread.id, drawn);
	}
	return brought;
}

describe('stepping through the threads', () => {
	it('keeps one position, so two controls cannot disagree', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'one']);
	});

	it('wraps around rather than stopping at the end', () => {
		review.threads.add(newComment({ body: 'one' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['one', 'one']);
	});

	it('has nothing to step to when there are no threads', () => {
		const brought = drawThreads();

		review.navigator.step(1);

		expect(brought).toEqual([]);
	});
});
