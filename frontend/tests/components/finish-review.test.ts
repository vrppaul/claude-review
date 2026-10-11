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
		expect(review.link.ending).toBe('finished');
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

describe('a comment still open in its field as the review is finished', () => {
	// Where the reader started a comment and left it open
	const PICKED = { side: 'new' as const, startLine: 3, endLine: 4, opensBelow: { side: 'new' as const, number: 4 } };
	let review: Review;

	beforeEach(() => {
		review = openReview();
	});

	/** Start a comment on lines of a file and type into it, without adding it. */
	function leftOpen(text: string): void {
		review.threads.writing.pickLines('file.ts', PICKED, ['a', 'b']);
		const [field] = review.threads.writing.onLinesOf('file.ts');
		if (!field) throw new Error('No field was opened');
		field.text = text;
	}

	it('is listed in the pane as going with the review, where it is and what it says', () => {
		leftOpen('half a thought');

		const { getByTestId, queryByText } = render(FinishReview, inReview(review));

		expect(said(getByTestId('open-fields'))).toContain('1 comment still open goes with the review');
		expect(said(getByTestId('open-field'))).toContain('file.ts · Lines 3-4');
		expect(said(getByTestId('open-field'))).toContain('half a thought');
		expect(queryByText(/Nothing written yet/)).toBeNull();
	});

	it('goes with a round, rather than being left behind', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { markdown: '## Round', comment_count: 1, round: 1, ended: false });
		review.answerer.setAttached(true);
		leftOpen('half a thought');

		await review.submission.send();

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([{ threads: [{ body: 'half a thought' }] }]);
		expect(review.threads.writing.onLinesOf('file.ts')).toEqual([]);
	});

	it('goes with the final review, rather than being forgotten with the draft', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', SENT_FOR_GOOD);
		leftOpen('half a thought');

		await review.submission.send();

		expect(server.bodiesSentTo('POST /api/submit')).toMatchObject([
			{ threads: [{ body: 'half a thought' }], end: true }
		]);
	});

	it('is not a field opened and left empty', () => {
		leftOpen('   ');

		const { queryByTestId, getByText } = render(FinishReview, inReview(review));

		expect(queryByTestId('open-fields')).toBeNull();
		expect(getByText(/Nothing written yet/)).toBeTruthy();
		expect(review.submission.canSend).toBe(false);
	});

	it('is not an edit left open as it was, which would send the thread again', () => {
		const id = review.threads.add(newComment({ body: 'as it was' }));
		const [thread] = review.threads.all;
		if (!thread) throw new Error('No thread');
		review.threads.markSent([thread], 1);
		review.answerer.setAttached(true);
		review.threads.writing.openEdit(thread);

		const { queryByTestId } = render(FinishReview, inReview(review));

		expect(queryByTestId('open-fields')).toBeNull();
		expect(review.submission.canSend).toBe(false);
		expect(review.threads.sentInRound(id)).toBe(1);
	});
});
