import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FinishReview from '$lib/components/FinishReview.svelte';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

/** What an element says, without the template's line breaks. */
function said(element: HTMLElement): string {
	return element.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

// What the server says once a review is sent for good
const SENT_FOR_GOOD = { markdown: '## Comments', comment_count: 1, round: 1, ended: true };

describe('finishing a review', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview();
	});

	it('counts the comments about to go', () => {
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix this' }));
		review.threads.add(newComment({ file: 'file.ts', startLine: 5, body: 'and this' }));

		const { getByTestId } = render(FinishReview, inReview(review));

		expect(said(getByTestId('finish-count'))).toBe('2 comments');
	});

	it('says one comment, not one comments', () => {
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix' }));

		const { getByTestId } = render(FinishReview, inReview(review));

		expect(said(getByTestId('finish-count'))).toBe('1 comment');
	});

	it('says a summary alone is a review when nothing is written', () => {
		const { queryByTestId, getByText } = render(FinishReview, inReview(review));

		expect(queryByTestId('finish-comment')).toBeNull();
		expect(getByText(/A summary on its own is a review too/)).toBeTruthy();
	});

	it('counts what is still unsent once rounds are being sent', () => {
		review.answerer.setAttached(true);
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix' }));

		const { getByTestId } = render(FinishReview, inReview(review));

		expect(said(getByTestId('finish-count'))).toBe('1 unsent of 1');
		expect(getByTestId('modal-submit').textContent).toContain('Send round');
		expect(getByTestId('end-review')).toBeTruthy();
	});

	it('sends a round only with something new in it', async () => {
		review.answerer.setAttached(true);
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix' }));
		review.threads.markSent(review.threads.all, 1);

		const { getByTestId } = render(FinishReview, inReview(review));
		const send = getByTestId('modal-submit') as HTMLButtonElement;
		expect(send.disabled).toBe(true);

		await userEvent.type(getByTestId('review-body'), 'And one more thing');
		expect(send.disabled).toBe(false);
	});

	it('offers only the final send once the agent has gone', () => {
		review.answerer.setAttached(true);
		review.answerer.setAttached(false);
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix' }));

		const { getByTestId, queryByTestId } = render(FinishReview, inReview(review));

		expect(getByTestId('modal-submit').textContent).not.toContain('Send round');
		expect(queryByTestId('end-review')).toBeNull();
	});

	it('shows each comment in full before it is sent', () => {
		const long =
			'This reads the clock twice per call, so a sweep can see two different ' +
			'instants and drop a session that was alive when it started.';
		review.threads.add(newComment({ file: 'src/app.ts', startLine: 42, body: long }));

		const { getByText, getByTestId } = render(FinishReview, inReview(review));

		// The last screen before sending is the wrong place to truncate
		expect(getByText(long)).toBeTruthy();
		expect(getByTestId('modal-comment-ref').textContent).toContain('src/app.ts');
	});

	it('cannot be sent with nothing written', () => {
		const { getByTestId } = render(FinishReview, inReview(review));

		expect((getByTestId('modal-submit') as HTMLButtonElement).disabled).toBe(true);
	});

	it('can be sent with only a summary', async () => {
		const { getByTestId } = render(FinishReview, inReview(review));

		await userEvent.type(getByTestId('review-body'), 'General feedback');

		expect((getByTestId('modal-submit') as HTMLButtonElement).disabled).toBe(false);
	});

	it('sends the review when asked', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', SENT_FOR_GOOD);
		review.threads.add(newComment({ file: 'file.ts', startLine: 1, body: 'fix' }));

		const { getByTestId } = render(FinishReview, inReview(review));
		await userEvent.click(getByTestId('modal-submit'));

		expect(server.requestsTo('POST /api/submit')).toHaveLength(1);
		expect(review.submission.finished).toBe(true);
	});
});

describe('the line a comment sits on, before it is sent', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview();
	});

	it('marks a comment that sits on a removed line', () => {
		review.threads.add(newComment({ file: 'src/app.ts', side: 'old', startLine: 42, body: 'why was this dropped' }));

		const { getByTestId } = render(FinishReview, inReview(review));

		expect(said(getByTestId('modal-comment-ref'))).toBe('src/app.ts · Removed line 42');
	});

	it('leaves a comment on the current version unmarked', () => {
		review.threads.add(newComment({ file: 'src/app.ts', startLine: 42, endLine: 47, body: 'tighten this' }));

		const { getByTestId } = render(FinishReview, inReview(review));

		expect(said(getByTestId('modal-comment-ref'))).toBe('src/app.ts · Lines 42-47');
	});
});
