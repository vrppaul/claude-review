import { beforeEach, describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { threadsNotDrawnIn } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, diffResponse, hunk, removedLine, REVIEW_BASE, sinceRound } from './diff';
import { fakeServer, SERVER_ERROR } from './fake-server';
import { newComment } from './new-comment';
import { openReview } from './review';
import { settled } from './settled';

// The review's own diff: a.py lost a line and gained one, b.py gained a line
const A_PY = diffFile({ path: 'a.py', hunks: [hunk([removedLine(1, 'was'), addedLine(1, 'is')])] });
const B_PY = diffFile({ path: 'b.py', hunks: [hunk([addedLine(5, 'in b.py')])] });
const files = [A_PY, B_PY];

let review: Review;

/** Draw every thread of the review where the page would, and keep the body of each one brought into view. */
function drawThreads(): string[] {
	const brought: string[] = [];
	for (const thread of review.threads.all) {
		const drawn = document.createElement('div');
		drawn.scrollIntoView = () => brought.push(thread.body);
		review.sections.registerThread(thread.id, drawn);
	}
	return brought;
}

describe("the files read against the review's own base", () => {
	beforeEach(() => {
		review = openReview({ files });
	});

	it('draw every thread: one on a file the diff does not hold too, above the files', () => {
		review.threads.add(newComment({ file: 'gone.py', startLine: 1 }));
		review.threads.add(newComment({ file: 'a.py', side: 'old', startLine: 1 }));

		expect(threadsNotDrawnIn(review.views.onScreen, review.threads)).toEqual([]);
	});
});

describe('the files read against a narrower base', () => {
	beforeEach(async () => {
		review = openReview({ files });
		// Since round one, a.py alone; whatever diff is asked for after that is the review's own
		fakeServer().answer('GET /api/diff', diffResponse({ files: [A_PY], base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		fakeServer().answer('GET /api/diff', diffResponse({ files, base: REVIEW_BASE }));
	});

	it('draw a thread on a line the base shows', () => {
		const onTheLineAdded = newComment({ file: 'a.py', startLine: 1 }).anchor;

		expect(review.views.onScreen.sectionOf(onTheLineAdded)).toBe('a.py');
	});

	it('draw no thread on a file the base leaves out', () => {
		const inTheFileLeftOut = newComment({ file: 'b.py', startLine: 5 }).anchor;

		expect(review.views.onScreen.sectionOf(inTheFileLeftOut)).toBeNull();
	});

	it("draw no thread on a removed line, whose number is the base's own there", () => {
		const onTheLineRemoved = newComment({ file: 'a.py', side: 'old', startLine: 1 }).anchor;

		expect(review.views.onScreen.sectionOf(onTheLineRemoved)).toBeNull();
	});

	it('walk only the threads they draw', () => {
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in the file left out' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'on a line shown' }));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual(['on a line shown']);
	});

	it('say which threads they do not draw', () => {
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in the file left out' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'on a line shown' }));

		const notDrawn = threadsNotDrawnIn(review.views.onScreen, review.threads);

		expect(notDrawn.map((thread) => thread.body)).toEqual(['in the file left out']);
	});

	it('are put back whole for a thread the base cannot draw, which the reader is then taken to', async () => {
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in the file left out' }));
		const [thread] = review.threads.all;
		const brought = drawThreads();

		review.navigator.reveal(thread);
		await settled();

		expect(review.diff.narrowed).toBe(false);
		expect(brought).toEqual(['in the file left out']);
	});

	it('stay as they are for a thread the base draws', async () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'on a line shown' }));
		const [thread] = review.threads.all;
		drawThreads();

		review.navigator.reveal(thread);
		await settled();

		expect(review.diff.narrowed).toBe(true);
	});

	it('are put back whole for a file the base leaves out, which the reader is shown once it is drawn', async () => {
		render(ReviewScreen, { props: { review } });

		review.navigator.showFile('b.py');
		await settled();

		expect(review.diff.narrowed).toBe(false);
		expect(review.sections.fileInView).toBe('b.py');
	});

	it('say why the whole review could not be put back, and take the reader nowhere', async () => {
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in the file left out' }));
		const [thread] = review.threads.all;
		const brought = drawThreads();
		fakeServer().refuse('GET /api/diff', SERVER_ERROR, 'The diff could not be read');

		review.navigator.reveal(thread);
		await settled();

		expect(review.diff.wholeReviewFailed).toContain('The diff could not be read');
		expect(brought).toEqual([]);
	});

	it('no longer say so while the whole review is asked for again', async () => {
		const server = fakeServer();
		server.refuse('GET /api/diff', SERVER_ERROR, 'The diff could not be read');
		await review.diff.showWholeReview();
		server.hold('GET /api/diff');

		void review.diff.showWholeReview();

		expect(review.diff.wholeReviewFailed).toBeNull();
	});

	it('no longer say so once another diff is on screen', async () => {
		const server = fakeServer();
		server.refuse('GET /api/diff', SERVER_ERROR, 'The diff could not be read');
		await review.diff.showWholeReview();

		server.answer('GET /api/diff', diffResponse({ files: [A_PY], base: sinceRound(1) }));
		await review.diff.take();

		expect(review.diff.wholeReviewFailed).toBeNull();
	});
});
