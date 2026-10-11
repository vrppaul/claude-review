import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, hunk } from '../diff';
import { fakeServer, SERVER_ERROR } from '../fake-server';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

const file = diffFile({ path: 'test.py', hunks: [hunk([contextLine(1, 1, 'hello')])] });
// A review of files compared against nothing: the header names it rather
// than offering bases
const READ_WHOLE = { phrase: null };

describe('sending the review', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview({ files: [file], diff: READ_WHOLE });
	});

	it('counts the comments written', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		review.threads.add(newComment({ file: 'test.py', startLine: 2, body: 'fix2' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('2');
		expect(count.textContent).toContain('comments');
	});

	it('says one comment, not one comments', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('1');
		expect(count.textContent).toMatch(/\bcomment\b/);
	});

	it('can be opened once something is written', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});

	it('opens even with nothing written, because a summary alone is a review', () => {
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});
});

describe('a review that is over', () => {
	it('says it was sent, wherever it was sent from', () => {
		const review = openReview({ files: [file] });

		review.link.end('finished');
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('submitted-banner').textContent).toContain('Review sent');
		expect(queryByTestId('top-bar')).toBeNull();
	});

	it('says one stopped under the reader keeps what was not sent', () => {
		const review = openReview({ files: [file] });

		review.link.end('stopped');
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('review-stopped').textContent).toContain('What you had not sent is kept');
	});

	it('says another review answers here now, and that what was not sent is kept', () => {
		const review = openReview({ files: [file] });

		review.link.end('replaced');
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('review-replaced').textContent).toContain('another review is running here now');
		expect(getByTestId('review-replaced').textContent).toContain('What you had not sent is kept');
	});
});

describe('the review header', () => {
	it('says what is under review', () => {
		const review = openReview({
			files: [file],
			facts: { title: 'claude-review: uncommitted changes' },
			diff: READ_WHOLE
		});

		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('review-title').textContent?.trim()).toBe('claude-review: uncommitted changes');
	});

	it('leaves the title out when the server sent none', () => {
		const review = openReview({ files: [file], facts: { title: '' }, diff: READ_WHOLE });

		const { queryByTestId } = render(ReviewHeader, inReview(review));

		expect(queryByTestId('review-title')).toBeNull();
	});

	it('offers comment navigation only once there is a comment', async () => {
		const review = openReview({ files: [file], diff: READ_WHOLE });

		const { queryByTestId, rerender } = render(ReviewHeader, inReview(review));
		expect(queryByTestId('next-comment')).toBeNull();

		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		await rerender({});

		expect(queryByTestId('next-comment')).toBeTruthy();
	});

	it('opens one door to everything that ends a round', async () => {
		const user = userEvent.setup({ delay: null });
		const review = openReview({ files: [file], diff: READ_WHOLE });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));
		await user.click(getByTestId('quick-submit'));

		// What was written, a summary, and the two ways out — all in one place
		expect(getByTestId('finish-review')).toBeTruthy();
		expect(getByTestId('finish-comment')).toBeTruthy();
		expect(getByTestId('review-body')).toBeTruthy();
		expect(getByTestId('modal-submit')).toBeTruthy();
	});
});

describe('the pane the review is sent from', () => {
	// What the server says to a round, and to a review sent for good
	const ROUND_SENT = { markdown: '## Round', comment_count: 1, round: 1, ended: false };
	const SENT_FOR_GOOD = { markdown: '## Review', comment_count: 1, round: 1, ended: true };

	/** The whole review on screen, as the page draws it. */
	function onScreen(review: Review) {
		return render(ReviewScreen, { props: { review } });
	}

	/** The number of a line, to press it by. */
	function lineNumber(number: number): HTMLElement {
		const gutter = screen
			.getAllByTestId('line-gutter')
			.find((candidate) => candidate.textContent?.trim() === String(number));
		if (!gutter) throw new Error(`Line ${number} is not drawn`);
		return gutter;
	}

	it('gives way to a press anywhere else, and the press does what it was for', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));

		await user.click(lineNumber(1));

		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(screen.getByTestId('comment-input')).toBeTruthy();
	});

	it('goes on Escape, and hands the keyboard back to the button that opened it', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));
		expect(document.activeElement).toBe(screen.getByTestId('review-body'));

		await user.keyboard('{Escape}');

		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('quick-submit'));
	});

	it('opens from the keys while a comment is being written, and sends with them once open', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('POST /api/submit', SENT_FOR_GOOD);
		const review = openReview({ files: [file] });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(lineNumber(1));

		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');
		expect(screen.getByTestId('finish-review')).toBeTruthy();
		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');

		expect(server.requestsTo('POST /api/submit')).toHaveLength(1);
	});

	it('says why a send did not go, and stays open with everything in it', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.fail('POST /api/submit', SERVER_ERROR);
		const review = openReview({ files: [file], facts: { answerer_attached: true } });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));
		await user.type(screen.getByTestId('review-body'), 'mostly fine');

		await user.click(screen.getByTestId('modal-submit'));

		expect(screen.getByTestId('submit-error').textContent).toContain(SERVER_ERROR);
		expect((screen.getByTestId('review-body') as HTMLTextAreaElement).value).toBe('mostly fine');
		server.answer('POST /api/submit', ROUND_SENT);
		await user.click(screen.getByTestId('modal-submit'));
		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(screen.queryByTestId('submit-error')).toBeNull();
	});
});
