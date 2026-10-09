import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import SubmitBar from '$lib/components/SubmitBar.svelte';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, hunk } from '../diff';
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

		const { getByTestId } = render(SubmitBar, inReview(review));
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('2');
		expect(count.textContent).toContain('comments');
	});

	it('says one comment, not one comments', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar, inReview(review));
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('1');
		expect(count.textContent).toMatch(/\bcomment\b/);
	});

	it('can be opened once something is written', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});

	it('opens even with nothing written, because a summary alone is a review', () => {
		const { getByTestId } = render(SubmitBar, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});
});

describe('the review header', () => {
	it('says what is under review', () => {
		const review = openReview({
			files: [file],
			facts: { title: 'claude-review: uncommitted changes' },
			diff: READ_WHOLE
		});

		const { getByTestId } = render(SubmitBar, inReview(review));

		expect(getByTestId('review-title').textContent?.trim()).toBe(
			'claude-review: uncommitted changes'
		);
	});

	it('leaves the title out when the server sent none', () => {
		const review = openReview({ files: [file], facts: { title: '' }, diff: READ_WHOLE });

		const { queryByTestId } = render(SubmitBar, inReview(review));

		expect(queryByTestId('review-title')).toBeNull();
	});

	it('offers comment navigation only once there is a comment', async () => {
		const review = openReview({ files: [file], diff: READ_WHOLE });

		const { queryByTestId, rerender } = render(SubmitBar, inReview(review));
		expect(queryByTestId('next-comment')).toBeNull();

		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		await rerender({});

		expect(queryByTestId('next-comment')).toBeTruthy();
	});

	it('opens one door to everything that ends a round', async () => {
		const user = userEvent.setup({ delay: null });
		const review = openReview({ files: [file], diff: READ_WHOLE });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar, inReview(review));
		await user.click(getByTestId('quick-submit'));

		// What was written, a summary, and the two ways out — all in one place
		expect(getByTestId('finish-review')).toBeTruthy();
		expect(getByTestId('finish-comment')).toBeTruthy();
		expect(getByTestId('review-body')).toBeTruthy();
		expect(getByTestId('modal-submit')).toBeTruthy();
	});
});
