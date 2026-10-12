import { beforeEach, describe, it, expect } from 'vitest';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, contextLine, diffFile, hunk, removedLine } from './diff';
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

	it('puts the keyboard on the thread without moving the screen again, which is already on its way there', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const [thread] = review.threads.all;
		const drawn = document.createElement('div');
		drawn.scrollIntoView = () => undefined;
		const focusedWith: (FocusOptions | undefined)[] = [];
		drawn.focus = (options) => focusedWith.push(options);
		review.sections.registerThread(thread.id, drawn);

		review.navigator.step(1);

		expect(focusedWith).toEqual([{ preventScroll: true }]);
	});

	it('has nothing to step to when there are no threads', () => {
		const brought = drawThreads();

		review.navigator.step(1);

		expect(brought).toEqual([]);
	});

	it('goes back from nowhere to the last thread', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();

		review.navigator.step(-1);

		expect(brought).toEqual(['three']);
	});

	it('goes on from the thread it is on when one before it is removed', () => {
		const first = review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(first);
		review.navigator.step(1);

		expect(brought).toEqual(['one', 'two', 'three']);
	});

	it('goes on from the thread the reader was last taken to, by whatever control', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		const [, second] = review.threads.all;

		if (second) review.navigator.reveal(second);
		review.navigator.step(1);

		expect(brought).toEqual(['two', 'three']);
	});

	it('goes on to the next thread from one the reader removed, and back to the one before it', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const second = review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(second);
		review.navigator.step(1);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'three', 'one']);
	});

	it('goes back from a removed thread to the one before it', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const second = review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(second);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'one']);
	});
});

describe('the order the threads are stepped through', () => {
	// Two files, in the order the diff holds them: a.py with a change at its
	// top and one further down, where two lines were replaced by two
	const files = [
		diffFile({
			path: 'a.py',
			hunks: [
				hunk([contextLine(1, 1, 'import os'), addedLine(2, 'import sys')]),
				hunk(
					[
						contextLine(38, 39, 'def run():'),
						removedLine(39, '    old_first()'),
						removedLine(40, '    old_second()'),
						addedLine(40, '    new_first()'),
						addedLine(41, '    new_second()')
					],
					{ header: '@@ -38,3 +39,3 @@', old_start: 38, new_start: 39 }
				)
			]
		}),
		diffFile({ path: 'b.py', hunks: [hunk([addedLine(1, 'x = 1')])] })
	];

	it('goes down the diff, file by file and line by line, whatever order they were written in', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'b.py', startLine: 1, body: 'b.py:1' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 41, body: 'a.py:41' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'a.py:2' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['a.py:2', 'a.py:41', 'b.py:1']);
	});

	it('takes a removed line before the line that replaced it, as they are drawn, whatever their numbers', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 40, body: 'new 40' }));
		review.threads.add(newComment({ file: 'a.py', side: 'old', startLine: 40, body: 'old 40' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['old 40', 'new 40']);
	});

	it('takes a thread on a line read in between two changes where that line stands', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 41, body: 'below' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 20, body: 'read in between' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'above' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['above', 'read in between', 'below']);
	});

	it('takes first the threads on a file the diff no longer holds, which are drawn above it', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'on a.py' }));
		review.threads.add(newComment({ file: 'gone.py', startLine: 7, body: 'on gone.py' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['on gone.py', 'on a.py']);
	});
});
